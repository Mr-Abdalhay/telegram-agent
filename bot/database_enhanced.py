"""
Enhanced Database Module for Reporting System
Includes methods for departments, roles, reports, and cumulative reporting
"""

import sqlite3
from typing import List, Dict, Optional, Tuple, Any
import threading
import os
import json
from datetime import datetime, timedelta
from config import config


class DatabaseEnhanced:
    """Enhanced database with reporting system support"""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self.init_db()

    def init_db(self):
        """Initialize database with new schema"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)

        # Check if database exists and has old schema
        if os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='departments'")
            if not cursor.fetchone():
                print("⚠️  Old database schema detected. Please run migration script:")
                print("   python scripts/migrate_database.py")
            conn.close()

    # ============================================================
    # USER MANAGEMENT
    # ============================================================

    def add_user(self, user_id: int, username: str, first_name: str,
                 last_name: str = None, email: str = None, phone: str = None):
        """Add or update user"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT OR REPLACE INTO users
                (user_id, username, first_name, last_name, email, phone, is_active)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ''',
                (user_id, username, first_name, last_name, email, phone),
            )
            conn.commit()
            conn.close()

    def get_user(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'user_id': row[0], 'username': row[1], 'first_name': row[2],
                'last_name': row[3], 'email': row[4], 'phone': row[5],
                'is_active': row[6], 'created_at': row[7]
            }
        return None

    # ============================================================
    # DEPARTMENT MANAGEMENT
    # ============================================================

    def create_department(self, name: str, name_en: str = None,
                         description: str = None, parent_id: int = None,
                         manager_id: int = None) -> int:
        """Create new department"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Calculate level
            level = 0
            if parent_id:
                cursor.execute('SELECT level FROM departments WHERE id = ?', (parent_id,))
                parent_level = cursor.fetchone()
                level = (parent_level[0] + 1) if parent_level else 0

            cursor.execute(
                '''
                INSERT INTO departments
                (name, name_en, description, parent_department_id, level, manager_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (name, name_en, description, parent_id, level, manager_id)
            )
            dept_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return dept_id

    def get_department(self, dept_id: int) -> Optional[Dict]:
        """Get department by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM departments WHERE id = ?', (dept_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0], 'name': row[1], 'name_en': row[2],
                'description': row[3], 'parent_department_id': row[4],
                'level': row[5], 'manager_id': row[6], 'is_active': row[7]
            }
        return None

    def get_all_departments(self, active_only: bool = True) -> List[Dict]:
        """Get all departments"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT * FROM departments'
        if active_only:
            query += ' WHERE is_active = 1'
        query += ' ORDER BY level, name'

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'name': r[1], 'name_en': r[2],
            'description': r[3], 'parent_department_id': r[4],
            'level': r[5], 'manager_id': r[6], 'is_active': r[7]
        } for r in rows]

    def get_department_hierarchy(self, dept_id: int) -> List[int]:
        """Get department and all its sub-departments (recursive)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Recursive CTE to get all child departments
        cursor.execute('''
            WITH RECURSIVE dept_tree AS (
                SELECT id FROM departments WHERE id = ?
                UNION ALL
                SELECT d.id FROM departments d
                JOIN dept_tree dt ON d.parent_department_id = dt.id
            )
            SELECT id FROM dept_tree
        ''', (dept_id,))

        dept_ids = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dept_ids

    def get_subdepartments(self, dept_id: int) -> List[Dict]:
        """Get immediate subdepartments"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT * FROM departments WHERE parent_department_id = ? AND is_active = 1',
            (dept_id,)
        )
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'name': r[1], 'name_en': r[2],
            'description': r[3], 'parent_department_id': r[4],
            'level': r[5], 'manager_id': r[6]
        } for r in rows]

    # ============================================================
    # ROLE MANAGEMENT
    # ============================================================

    def get_role_by_name(self, role_name: str) -> Optional[Dict]:
        """Get role by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM roles WHERE name = ?', (role_name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0], 'name': row[1], 'name_ar': row[2],
                'description': row[3], 'level': row[4],
                'permissions': json.loads(row[5]) if row[5]  else {}
            }
        return None

    def assign_role(self, user_id: int, role_name: str,
                   department_id: int = None, assigned_by: int = None, is_primary: bool = True) -> bool:
        """Assign role to user"""
        role = self.get_role_by_name(role_name)
        if not role:
            return False

        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            try:
                # If this should be primary role, unset other primary roles first
                if is_primary:
                    cursor.execute(
                        'UPDATE user_roles SET is_primary = 0 WHERE user_id = ?',
                        (user_id,)
                    )

                # Try to insert new role
                cursor.execute(
                    '''
                    INSERT INTO user_roles (user_id, role_id, department_id, assigned_by, is_primary)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (user_id, role['id'], department_id, assigned_by, 1 if is_primary else 0)
                )
                conn.commit()
                conn.close()
                return True
            except sqlite3.IntegrityError:
                # Role already exists for this user/dept combination - UPDATE instead
                try:
                    cursor.execute(
                        '''
                        UPDATE user_roles
                        SET is_active = 1, is_primary = ?, assigned_by = ?, assigned_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND role_id = ? AND department_id IS ?
                        ''',
                        (1 if is_primary else 0, assigned_by, user_id, role['id'], department_id)
                    )
                    if cursor.rowcount == 0:
                        # No existing role found, might be different role/dept combo
                        # Delete old assignments and insert new one
                        cursor.execute(
                            'DELETE FROM user_roles WHERE user_id = ? AND is_primary = 1',
                            (user_id,)
                        )
                        cursor.execute(
                            '''
                            INSERT INTO user_roles (user_id, role_id, department_id, assigned_by, is_primary)
                            VALUES (?, ?, ?, ?, ?)
                            ''',
                            (user_id, role['id'], department_id, assigned_by, 1 if is_primary else 0)
                        )
                    conn.commit()
                    conn.close()
                    return True
                except Exception as e:
                    conn.rollback()
                    conn.close()
                    return False

    def get_user_roles(self, user_id: int) -> List[Dict]:
        """Get all roles for a user"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, ur.department_id, d.name as dept_name
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            LEFT JOIN departments d ON ur.department_id = d.id
            WHERE ur.user_id = ? AND ur.is_active = 1
        ''', (user_id,))
        rows = cursor.fetchall()
        conn.close()

        result = []
        for r in rows:
            # r[0]=id, r[1]=name, r[2]=name_ar, r[3]=description,
            # r[4]=level, r[5]=permissions, r[6]=created_at,
            # r[7]=ur.department_id, r[8]=d.name
            permissions = {}
            if r[5] and r[5].strip():
                try:
                    permissions = json.loads(r[5])
                except (json.JSONDecodeError, ValueError):
                    permissions = {}

            result.append({
                'role_id': r[0],
                'role_name': r[1],
                'role_name_ar': r[2],
                'level': r[4],
                'permissions': permissions,
                'department_id': r[7],  # Fixed: was r[6]
                'department_name': r[8]  # Fixed: was r[7]
            })
        return result

    def get_user_primary_role(self, user_id: int) -> Optional[Dict]:
        """Get user's highest level role"""
        roles = self.get_user_roles(user_id)
        if not roles:
            return None
        return max(roles, key=lambda x: x['level'])

    def get_user_department(self, user_id: int) -> Optional[int]:
        """Get user's primary department"""
        roles = self.get_user_roles(user_id)
        if not roles:
            return None
        # Return department of highest role
        primary_role = max(roles, key=lambda x: x['level'])
        return primary_role.get('department_id')

    # ============================================================
    # PERMISSIONS CHECK
    # ============================================================

    def has_permission(self, user_id: int, permission: str) -> bool:
        """Check if user has specific permission"""
        roles = self.get_user_roles(user_id)
        for role in roles:
            perms = role.get('permissions', {})
            if perms.get(permission, False):
                return True
        return False

    def can_access_department(self, user_id: int, dept_id: int) -> bool:
        """Check if user can access department reports"""
        user_role = self.get_user_primary_role(user_id)
        if not user_role:
            return False

        # Admin can access all
        if user_role['role_name'] == 'admin':
            return True

        user_dept = user_role.get('department_id')
        if not user_dept:
            return False

        # Same department
        if user_dept == dept_id:
            return True

        # Upper manager can access subdepartments
        if user_role['permissions'].get('can_view_subdepartments'):
            dept_hierarchy = self.get_department_hierarchy(user_dept)
            return dept_id in dept_hierarchy

        return False

    # ============================================================
    # REPORT MANAGEMENT
    # ============================================================

    def create_report(self, title: str, content: str, report_type: str,
                     user_id: int, department_id: int, status: str = 'draft',
                     priority: str = 'normal', metadata: Dict = None,
                     tags: List[str] = None) -> int:
        """Create new report"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            metadata_json = json.dumps(metadata) if metadata else None
            tags_json = json.dumps(tags) if tags else None
            submitted_at = datetime.now() if status != 'draft' else None

            cursor.execute(
                '''
                INSERT INTO reports
                (title, content, report_type, status, priority, submitted_by,
                 department_id, metadata, tags, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (title, content, report_type, status, priority, user_id,
                 department_id, metadata_json, tags_json, submitted_at)
            )
            report_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return report_id

    def get_report(self, report_id: int) -> Optional[Dict]:
        """Get report by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT r.*, u.first_name, u.last_name, d.name as dept_name
            FROM reports r
            JOIN users u ON r.submitted_by = u.user_id
            JOIN departments d ON r.department_id = d.id
            WHERE r.id = ?
        ''', (report_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                'id': row[0], 'title': row[1], 'content': row[2],
                'report_type': row[3], 'status': row[4], 'priority': row[5],
                'visibility': row[6], 'submitted_by': row[7],
                'department_id': row[8], 'is_cumulative': row[9],
                'source_report_ids': json.loads(row[10]) if row[10] else None,
                'aggregation_type': row[11], 'aggregation_period': row[12],
                'metadata': json.loads(row[15]) if row[15] else {},
                'tags': json.loads(row[16]) if row[16] else [],
                'submitted_at': row[17], 'created_at': row[18],
                'submitter_name': f"{row[20]} {row[21] or ''}".strip(),
                'department_name': row[22]
            }
        return None

    def get_user_reports(self, user_id: int, limit: int = 10,
                        status: str = None) -> List[Dict]:
        """Get user's own reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT r.*, d.name as dept_name
            FROM reports r
            JOIN departments d ON r.department_id = d.id
            WHERE r.submitted_by = ?
        '''
        params = [user_id]

        if status:
            query += ' AND r.status = ?'
            params.append(status)

        query += ' ORDER BY r.created_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'title': r[1], 'report_type': r[3],
            'status': r[4], 'priority': r[5], 'submitted_at': r[17],
            'department_name': r[-1]
        } for r in rows]

    def get_department_reports(self, dept_id: int, start_date: str = None,
                              end_date: str = None, status: str = 'approved',
                              limit: int = 50) -> List[Dict]:
        """Get reports from specific department"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT r.*, u.first_name, u.last_name
            FROM reports r
            JOIN users u ON r.submitted_by = u.user_id
            WHERE r.department_id = ?
        '''
        params = [dept_id]

        if status:
            query += ' AND r.status = ?'
            params.append(status)

        if start_date:
            query += ' AND DATE(r.submitted_at) >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND DATE(r.submitted_at) <= ?'
            params.append(end_date)

        query += ' ORDER BY r.submitted_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'title': r[1], 'content': r[2],
            'report_type': r[3], 'status': r[4], 'priority': r[5],
            'submitted_by': r[7], 'submitted_at': r[17],
            'submitter_name': f"{r[-2]} {r[-1] or ''}".strip()
        } for r in rows]

    def get_hierarchical_reports(self, dept_id: int, start_date: str = None,
                                end_date: str = None, status: str = 'approved') -> List[Dict]:
        """Get reports from department and all subdepartments"""
        dept_ids = self.get_department_hierarchy(dept_id)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        placeholders = ','.join('?' * len(dept_ids))
        query = f'''
            SELECT r.*, u.first_name, u.last_name, d.name as dept_name
            FROM reports r
            JOIN users u ON r.submitted_by = u.user_id
            JOIN departments d ON r.department_id = d.id
            WHERE r.department_id IN ({placeholders})
        '''
        params = dept_ids

        if status:
            query += ' AND r.status = ?'
            params.append(status)

        if start_date:
            query += ' AND DATE(r.submitted_at) >= ?'
            params.append(start_date)

        if end_date:
            query += ' AND DATE(r.submitted_at) <= ?'
            params.append(end_date)

        query += ' ORDER BY r.department_id, r.submitted_at DESC'

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'title': r[1], 'content': r[2],
            'report_type': r[3], 'status': r[4], 'department_id': r[8],
            'submitted_at': r[17], 'submitter_name': f"{r[-3]} {r[-2] or ''}".strip(),
            'department_name': r[-1]
        } for r in rows]

    def update_report_status(self, report_id: int, status: str,
                            updated_by: int = None) -> bool:
        """Update report status"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            submitted_at = datetime.now() if status == 'submitted' else None
            if submitted_at:
                cursor.execute(
                    'UPDATE reports SET status = ?, submitted_at = ? WHERE id = ?',
                    (status, submitted_at, report_id)
                )
            else:
                cursor.execute(
                    'UPDATE reports SET status = ? WHERE id = ?',
                    (status, report_id)
                )

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()
            return success

    # ============================================================
    # CUMULATIVE REPORTS
    # ============================================================

    def create_cumulative_report(self, title: str, source_report_ids: List[int],
                                 aggregation_type: str, aggregation_period: str,
                                 user_id: int, department_id: int,
                                 content: str, start_date: str = None,
                                 end_date: str = None) -> int:
        """Create cumulative report from multiple source reports"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            source_ids_json = json.dumps(source_report_ids)

            cursor.execute(
                '''
                INSERT INTO reports
                (title, content, report_type, status, submitted_by, department_id,
                 is_cumulative, source_report_ids, aggregation_type, aggregation_period,
                 aggregation_start_date, aggregation_end_date, submitted_at)
                VALUES (?, ?, 'cumulative', 'submitted', ?, ?, 1, ?, ?, ?, ?, ?, ?)
                ''',
                (title, content, user_id, department_id, source_ids_json,
                 aggregation_type, aggregation_period, start_date, end_date,
                 datetime.now())
            )
            cumulative_id = cursor.lastrowid

            # Track aggregations
            for source_id in source_report_ids:
                cursor.execute(
                    'SELECT department_id FROM reports WHERE id = ?',
                    (source_id,)
                )
                source_dept = cursor.fetchone()

                cursor.execute(
                    '''
                    INSERT INTO report_aggregations
                    (cumulative_report_id, source_report_id, department_id)
                    VALUES (?, ?, ?)
                    ''',
                    (cumulative_id, source_id, source_dept[0] if source_dept else None)
                )

            conn.commit()
            conn.close()
            return cumulative_id

    # ============================================================
    # APPROVALS
    # ============================================================

    def add_approval(self, report_id: int, approver_id: int,
                    status: str, notes: str = None) -> int:
        """Add approval record"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            approved_at = datetime.now() if status == 'approved' else None

            cursor.execute(
                '''
                INSERT INTO report_approvals
                (report_id, approver_id, status, notes, approved_at)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (report_id, approver_id, status, notes, approved_at)
            )
            approval_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return approval_id

    # ============================================================
    # COMMENTS
    # ============================================================

    def add_comment(self, report_id: int, user_id: int,
                   comment: str, parent_comment_id: int = None) -> int:
        """Add comment to report"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO report_comments
                (report_id, user_id, parent_comment_id, comment)
                VALUES (?, ?, ?, ?)
                ''',
                (report_id, user_id, parent_comment_id, comment)
            )
            comment_id = cursor.lastrowid
            conn.commit()
            conn.close()
            return comment_id

    def get_report_comments(self, report_id: int) -> List[Dict]:
        """Get all comments for a report"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT c.*, u.first_name, u.last_name
            FROM report_comments c
            JOIN users u ON c.user_id = u.user_id
            WHERE c.report_id = ?
            ORDER BY c.created_at ASC
        ''', (report_id,))
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'comment': r[4], 'created_at': r[6],
            'author': f"{r[-2]} {r[-1] or ''}".strip()
        } for r in rows]

    # ============================================================
    # CONVERSATIONS & SUMMARIES (Existing methods)
    # ============================================================

    def save_conversation(self, user_id: int, message: str, response: str,
                         message_type: str = 'text', context: Dict = None):
        """Save conversation"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            context_json = json.dumps(context) if context else None

            cursor.execute(
                '''
                INSERT INTO conversations (user_id, message, response, message_type, context)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (user_id, message, response, message_type, context_json),
            )
            conn.commit()
            conn.close()

    def get_user_conversations(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user conversations"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            '''
            SELECT message, response, timestamp
            FROM conversations
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
            ''',
            (user_id, limit),
        )

        conversations = []
        for row in cursor.fetchall():
            conversations.append({
                'message': row[0],
                'response': row[1],
                'timestamp': row[2],
            })

        conn.close()
        return conversations

    def get_conversation_summary(self, user_id: int, date: str = None) -> str:
        """Get conversation summary text"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if date:
            cursor.execute(
                '''
                SELECT message, response
                FROM conversations
                WHERE user_id = ? AND DATE(timestamp) = ?
                ORDER BY timestamp
                ''',
                (user_id, date),
            )
        else:
            cursor.execute(
                '''
                SELECT message, response
                FROM conversations
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT 20
                ''',
                (user_id,),
            )

        conversations = cursor.fetchall()
        conn.close()

        text = ""
        for msg, resp in conversations:
            text += f"User: {msg}\nBot: {resp}\n\n"

        return text

    def save_summary(self, user_id: int, summary: str, date: str,
                    report_id: int = None, summary_type: str = 'conversation'):
        """Save summary"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO summaries (user_id, summary, date, report_id, summary_type)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (user_id, summary, date, report_id, summary_type),
            )
            conn.commit()
            conn.close()

    # ============================================================
    # HELPER METHODS FOR WEB INTERFACE
    # ============================================================

    def get_total_reports_count(self) -> int:
        """Get total number of reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reports')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_pending_reports_count(self) -> int:
        """Get number of pending reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reports WHERE status = ?', ('pending',))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_approved_reports_count(self) -> int:
        """Get number of approved reports"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reports WHERE status = ?', ('approved',))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_recent_audit_logs(self, limit: int = 10) -> List[Dict]:
        """Get recent audit log entries"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT al.id, al.user_id, u.username, al.action, al.entity_type, al.entity_id, al.created_at
            FROM audit_log al
            LEFT JOIN users u ON al.user_id = u.user_id
            ORDER BY al.created_at DESC
            LIMIT ?
        ''', (limit,))
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'user_id': r[1], 'username': r[2],
            'action_type': r[3], 'entity_type': r[4], 'entity_id': r[5], 'timestamp': r[6]
        } for r in rows]

    def get_department_user_count(self, dept_id: int) -> int:
        """Get number of users in department"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM user_roles WHERE department_id = ?', (dept_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_department_report_count(self, dept_id: int) -> int:
        """Get number of reports from department"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM reports WHERE department_id = ?', (dept_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_all_reports(self, limit: int = 100, status: str = None) -> List[Dict]:
        """Get all reports (admin view)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = '''
            SELECT r.id, r.title, r.content, r.status, r.submitted_at, r.created_at,
                   u.username, u.first_name, d.name as department_name
            FROM reports r
            LEFT JOIN users u ON r.submitted_by = u.user_id
            LEFT JOIN departments d ON r.department_id = d.id
        '''
        params = []

        if status:
            query += ' WHERE r.status = ?'
            params.append(status)

        query += ' ORDER BY r.submitted_at DESC LIMIT ?'
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return [{
            'id': r[0], 'title': r[1], 'content': r[2], 'status': r[3],
            'submitted_at': r[4], 'created_at': r[5], 'username': r[6],
            'first_name': r[7], 'department_name': r[8]
        } for r in rows]

    def get_all_users(self, active_only: bool = False) -> List[Dict]:
        """Get all users"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        query = 'SELECT * FROM users'
        if active_only:
            query += ' WHERE is_active = 1'
        query += ' ORDER BY created_at DESC'

        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()

        return [{
            'user_id': r[0], 'username': r[1], 'first_name': r[2],
            'last_name': r[3], 'email': r[4], 'phone': r[5],
            'is_active': r[6], 'created_at': r[7], 'updated_at': r[8]
        } for r in rows]

    def deactivate_user(self, user_id: int) -> bool:
        """Deactivate user account"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET is_active = 0 WHERE user_id = ?', (user_id,))
            conn.commit()
            affected = cursor.rowcount
            conn.close()
            return affected > 0

    def get_role_by_name(self, role_name: str) -> Optional[Dict]:
        """Get role by name"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM roles WHERE name = ?', (role_name,))
        row = cursor.fetchone()
        conn.close()

        if row:
            # Handle empty or invalid JSON in permissions
            permissions = {}
            if row[3] and row[3].strip():
                try:
                    permissions = json.loads(row[3])
                except (json.JSONDecodeError, ValueError):
                    permissions = {}

            return {
                'id': row[0], 'name': row[1], 'display_name': row[2],
                'permissions': permissions
            }
        return None

    # ============================================================
    # AUDIT LOG
    # ============================================================

    def log_action(self, user_id: int, action: str, entity_type: str = None,
                   entity_id: int = None, old_value: str = None, new_value: str = None,
                   ip_address: str = None, user_agent: str = None):
        """Log an action to the audit log"""
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO audit_log
                (user_id, action, entity_type, entity_id, old_value, new_value, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (user_id, action, entity_type, entity_id, old_value, new_value, ip_address, user_agent)
            )
            conn.commit()
            conn.close()
