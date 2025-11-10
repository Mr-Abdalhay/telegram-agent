#!/usr/bin/env python3
"""
Web Admin Panel for Telegram Bot
Provides a web interface for managing users, departments, and admins
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.database_enhanced import DatabaseEnhanced
from bot.permissions import AccessControl
from config import config

app = Flask(__name__)
app.secret_key = os.getenv('WEB_SECRET_KEY', 'your-secret-key-change-this-in-production')

# Initialize database
db = DatabaseEnhanced(config.DB_PATH)
access_control = AccessControl(db)


# ============================================================
# AUTHENTICATION DECORATOR
# ============================================================

def login_required(f):
    """Require user to be logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Require user to be admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))

        user_id = session['user_id']
        if not access_control.is_admin(user_id):
            flash('Admin access required', 'error')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """Require user to be at least a manager"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'error')
            return redirect(url_for('login'))

        user_id = session['user_id']
        user_role = db.get_user_primary_role(user_id)

        if not user_role or user_role['role_name'] not in ['manager', 'upper_manager', 'admin']:
            flash('Manager access required', 'error')
            return redirect(url_for('dashboard'))

        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# AUTHENTICATION ROUTES
# ============================================================

@app.route('/')
def index():
    """Home page - redirect to login or dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        user_id = request.form.get('user_id', '').strip()
        password = request.form.get('password', '').strip()

        # Simple authentication - check if user exists and is admin/manager
        try:
            user_id = int(user_id)

            # Get user from database
            user = db.get_user(user_id)

            if not user:
                flash('User not found. Please use /start in Telegram bot first.', 'error')
                return render_template('login.html')

            # Get user role
            user_role = db.get_user_primary_role(user_id)

            if not user_role:
                flash('No role assigned. Please register in Telegram bot first.', 'error')
                return render_template('login.html')

            # Check if user is at least a manager
            role_name = user_role.get('role_name', '')

            if role_name not in ['manager', 'upper_manager', 'admin']:
                flash('Access denied. Manager role or above required.', 'error')
                return render_template('login.html')

            # For now, simple password check (user_id as password)
            # In production, implement proper password hashing
            if password == str(user_id) or password == 'admin':
                session['user_id'] = user_id
                session['username'] = user.get('username', 'User')
                session['role'] = role_name
                flash(f'Welcome, {user.get("first_name", "User")}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid password. Use your user_id or "admin" as password.', 'error')

        except ValueError:
            flash('Invalid user ID format. Must be a number.', 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('login'))


# ============================================================
# DASHBOARD
# ============================================================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    user_id = session['user_id']
    user_role = db.get_user_primary_role(user_id)

    # Get statistics
    stats = {
        'total_users': len(db.get_all_users()),
        'total_departments': len(db.get_all_departments()),
        'total_reports': db.get_total_reports_count(),
        'pending_reports': db.get_pending_reports_count(),
    }

    # Get recent activity
    recent_activity = db.get_recent_audit_logs(limit=10)

    return render_template('dashboard.html',
                         user_role=user_role,
                         stats=stats,
                         recent_activity=recent_activity)


# ============================================================
# USER MANAGEMENT
# ============================================================

@app.route('/users')
@login_required
def users_list():
    """List all users"""
    users = db.get_all_users()

    # Enrich with roles
    for user in users:
        user['roles'] = db.get_user_roles(user['user_id'])
        user['primary_role'] = db.get_user_primary_role(user['user_id'])

    return render_template('users_list.html', users=users)


@app.route('/users/<int:user_id>')
@login_required
def user_detail(user_id):
    """View user details"""
    user = db.get_user(user_id)

    if not user:
        flash('User not found', 'error')
        return redirect(url_for('users_list'))

    user['roles'] = db.get_user_roles(user_id)
    user['reports'] = db.get_user_reports(user_id)

    return render_template('user_detail.html', user=user)


@app.route('/users/create-admin', methods=['POST'])
@admin_required
def create_admin():
    """Create new admin"""
    target_user_id = request.form.get('user_id', '').strip()

    try:
        target_user_id = int(target_user_id)

        # Check if user exists
        user = db.get_user(target_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        # Assign admin role
        success = db.assign_role(target_user_id, 'admin', None, assigned_by=session['user_id'], is_primary=True)

        if success:
            # Log action
            db.log_action(
                user_id=session['user_id'],
                action='create_admin',
                entity_type='user',
                entity_id=target_user_id,
                new_value=json.dumps({'target_user_id': target_user_id})
            )
            return jsonify({'success': True, 'message': f'User {user["username"]} is now an admin'})
        else:
            return jsonify({'success': False, 'message': 'Failed to assign admin role'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid user ID'})


@app.route('/users/promote', methods=['POST'])
@admin_required
def promote_user():
    """Promote user to manager/upper_manager"""
    target_user_id = request.form.get('user_id', '').strip()
    role_name = request.form.get('role', '').strip()

    try:
        target_user_id = int(target_user_id)

        if role_name not in ['manager', 'upper_manager']:
            return jsonify({'success': False, 'message': 'Invalid role'})

        user = db.get_user(target_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        role = db.get_role_by_name(role_name)
        if not role:
            return jsonify({'success': False, 'message': 'Role not found'})

        # Get role ID from the role dict
        role_id = role.get('id')
        if not role_id:
            return jsonify({'success': False, 'message': 'Invalid role data'})

        user_roles = db.get_user_roles(target_user_id)

        if user_roles:
            dept_id = user_roles[0].get('department_id')
        else:
            dept_id = None

        success = db.assign_role(target_user_id, role_name, dept_id, assigned_by=session['user_id'], is_primary=True)

        if success:
            db.log_action(
                user_id=session['user_id'],
                action='promote_user',
                entity_type='user',
                entity_id=target_user_id,
                new_value=json.dumps({'target_user_id': target_user_id, 'role': role_name})
            )
            return jsonify({'success': True, 'message': f'User promoted to {role_name}'})
        else:
            return jsonify({'success': False, 'message': 'Failed to promote user'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid user ID'})


@app.route('/users/remove', methods=['POST'])
@admin_required
def remove_user():
    """Deactivate user"""
    target_user_id = request.form.get('user_id', '').strip()

    try:
        target_user_id = int(target_user_id)

        # Can't remove yourself
        if target_user_id == session['user_id']:
            return jsonify({'success': False, 'message': 'Cannot remove yourself'})

        # Can't remove other admins
        if access_control.is_admin(target_user_id):
            return jsonify({'success': False, 'message': 'Remove admin role first'})

        success = db.deactivate_user(target_user_id)

        if success:
            db.log_action(
                user_id=session['user_id'],
                action='deactivate_user',
                entity_type='user',
                entity_id=target_user_id,
                new_value=json.dumps({'target_user_id': target_user_id})
            )
            return jsonify({'success': True, 'message': 'User deactivated'})
        else:
            return jsonify({'success': False, 'message': 'Failed to deactivate user'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid user ID'})


@app.route('/users/activate', methods=['POST'])
@admin_required
def activate_user():
    """Activate user"""
    target_user_id = request.form.get('user_id', '').strip()

    try:
        target_user_id = int(target_user_id)

        # Check if user exists
        user = db.get_user(target_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        # Check if already active
        if user.get('is_active', 1):
            return jsonify({'success': False, 'message': 'User is already active'})

        # Activate user
        import sqlite3
        with db.lock:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_active = 1 WHERE user_id = ?', (target_user_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()

        if affected > 0:
            db.log_action(
                user_id=session['user_id'],
                action='activate_user',
                entity_type='user',
                entity_id=target_user_id,
                new_value=json.dumps({'target_user_id': target_user_id})
            )
            return jsonify({'success': True, 'message': 'User activated'})
        else:
            return jsonify({'success': False, 'message': 'Failed to activate user'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid user ID'})


@app.route('/users/assign-department', methods=['POST'])
@admin_required
def assign_user_department():
    """Assign user to department with role (Admin only)"""
    target_user_id = request.form.get('user_id', '').strip()
    dept_id = request.form.get('dept_id', '').strip()
    role_name = request.form.get('role', '').strip()

    try:
        target_user_id = int(target_user_id)
        dept_id = int(dept_id)

        # Validate inputs
        if role_name not in ['employee', 'manager', 'upper_manager']:
            return jsonify({'success': False, 'message': 'Invalid role'})

        # Check if user exists
        user = db.get_user(target_user_id)
        if not user:
            return jsonify({'success': False, 'message': 'User not found'})

        # Check if department exists
        dept = db.get_department(dept_id)
        if not dept:
            return jsonify({'success': False, 'message': 'Department not found'})

        # Assign role to user in department
        success = db.assign_role(
            user_id=target_user_id,
            role_name=role_name,
            department_id=dept_id,
            assigned_by=session['user_id'],
            is_primary=True
        )

        if success:
            db.log_action(
                user_id=session['user_id'],
                action='assign_department',
                entity_type='user',
                entity_id=target_user_id,
                new_value=json.dumps({
                    'target_user_id': target_user_id,
                    'department_id': dept_id,
                    'role': role_name
                })
            )
            return jsonify({
                'success': True,
                'message': f'User assigned to {dept["name"]} as {role_name}'
            })
        else:
            return jsonify({'success': False, 'message': 'Failed to assign user to department'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid input data'})


# ============================================================
# DEPARTMENT MANAGEMENT
# ============================================================

@app.route('/departments')
@manager_required
def departments_list():
    """List all departments"""
    departments = db.get_all_departments(active_only=False)

    # Build hierarchy
    for dept in departments:
        dept['user_count'] = db.get_department_user_count(dept['id'])
        dept['report_count'] = db.get_department_report_count(dept['id'])

    return render_template('departments_list.html', departments=departments)


@app.route('/departments/create', methods=['POST'])
@manager_required
def create_department():
    """Create new department"""
    name_ar = request.form.get('name_ar', '').strip()
    name_en = request.form.get('name_en', '').strip()
    parent_id = request.form.get('parent_id', '').strip()
    description = request.form.get('description', '').strip()

    if not name_ar or not name_en:
        return jsonify({'success': False, 'message': 'Name required in both languages'})

    parent_id = int(parent_id) if parent_id else None

    try:
        dept_id = db.create_department(
            name=name_ar,
            name_en=name_en,
            description=description,
            parent_id=parent_id
        )

        if dept_id:
            db.log_action(
                user_id=session['user_id'],
                action='create_department',
                entity_type='department',
                entity_id=dept_id,
                new_value=json.dumps({'department_id': dept_id, 'name': name_ar})
            )
            return jsonify({'success': True, 'message': 'Department created', 'dept_id': dept_id})
        else:
            return jsonify({'success': False, 'message': 'Failed to create department'})
    except Exception as e:
        error_msg = str(e)
        if 'UNIQUE constraint failed' in error_msg:
            return jsonify({'success': False, 'message': 'Department name already exists'})
        else:
            return jsonify({'success': False, 'message': f'Error: {error_msg}'})


@app.route('/departments/remove', methods=['POST'])
@admin_required
def remove_department():
    """Remove/deactivate department"""
    dept_id = request.form.get('dept_id', '').strip()

    try:
        dept_id = int(dept_id)

        # Get department info
        dept = db.get_department(dept_id)
        if not dept:
            return jsonify({'success': False, 'message': 'Department not found'})

        # Deactivate the department (soft delete)
        import sqlite3
        with db.lock:
            conn = sqlite3.connect(db.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE departments SET is_active = 0 WHERE id = ?', (dept_id,))
            affected = cursor.rowcount
            conn.commit()
            conn.close()

        if affected > 0:
            db.log_action(
                user_id=session['user_id'],
                action='remove_department',
                entity_type='department',
                entity_id=dept_id,
                old_value=json.dumps({'name': dept['name']})
            )
            return jsonify({'success': True, 'message': f'Department "{dept["name"]}" deactivated'})
        else:
            return jsonify({'success': False, 'message': 'Failed to deactivate department'})

    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid department ID'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


# ============================================================
# REPORTS
# ============================================================

@app.route('/reports')
@login_required
def reports_list():
    """List reports"""
    user_id = session['user_id']
    user_role = db.get_user_primary_role(user_id)

    # Get reports based on role
    if user_role['role_name'] == 'admin':
        reports = db.get_all_reports(limit=100)
    else:
        user_dept = user_role.get('department_id')
        if user_role['role_name'] in ['upper_manager']:
            # Get hierarchical reports
            reports = db.get_hierarchical_reports(user_dept, limit=100)
        elif user_role['role_name'] == 'manager':
            reports = db.get_department_reports(user_dept, limit=100)
        else:
            reports = db.get_user_reports(user_id)

    return render_template('reports_list.html', reports=reports, user_role=user_role)


# ============================================================
# API ENDPOINTS
# ============================================================

@app.route('/api/report/<int:report_id>')
@login_required
def api_get_report(report_id):
    """Get single report details"""
    try:
        report = db.get_report(report_id)
        if not report:
            return jsonify({'success': False, 'message': 'Report not found'})

        # Check permissions
        user_id = session['user_id']
        user_role = db.get_user_primary_role(user_id)

        # Admin can view all
        if user_role['role_name'] != 'admin':
            # Check if user can access this report
            if report['submitted_by'] != user_id:
                user_dept = user_role.get('department_id')
                if user_dept != report['department_id']:
                    return jsonify({'success': False, 'message': 'Access denied'})

        return jsonify({'success': True, 'report': report})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/users')
@login_required
def api_get_users():
    """Get all users with their roles"""
    try:
        users = db.get_all_users()

        # Enrich with roles
        for user in users:
            user_role = db.get_user_primary_role(user['user_id'])
            user['role'] = user_role['role_name'] if user_role else 'employee'

        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/departments')
@login_required
def api_get_departments():
    """Get all departments"""
    try:
        departments = db.get_all_departments(active_only=False)
        return jsonify({'success': True, 'departments': departments})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/stats')
@login_required
def api_stats():
    """Get dashboard statistics"""
    stats = {
        'total_users': len(db.get_all_users()),
        'active_users': len(db.get_all_users(active_only=True)),
        'total_departments': len(db.get_all_departments()),
        'total_reports': db.get_total_reports_count(),
        'pending_reports': db.get_pending_reports_count(),
        'approved_reports': db.get_approved_reports_count(),
    }
    return jsonify(stats)


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500


# ============================================================
# MAIN
# ============================================================

if __name__ == '__main__':
    port = int(os.getenv('WEB_PORT', 5000))
    debug = os.getenv('WEB_DEBUG', 'False').lower() == 'true'

    print(f"\n{'='*60}")
    print(f"  WEB ADMIN PANEL STARTING")
    print(f"{'='*60}")
    print(f"  URL: http://localhost:{port}")
    print(f"  Debug: {debug}")
    print(f"{'='*60}\n")

    app.run(host='0.0.0.0', port=port, debug=debug)
