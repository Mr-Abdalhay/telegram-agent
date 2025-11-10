#!/usr/bin/env python3
"""
Create Default Admin User Script
Creates a default admin user with username 'admin' and password 'admin'
"""

import sqlite3
import os
import sys
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from bot.database_enhanced import DatabaseEnhanced
from config import config


def create_default_admin():
    """Create default admin user"""
    print("=" * 60)
    print("Creating Default Admin User")
    print("=" * 60)

    # Initialize database
    db = DatabaseEnhanced(config.DB_PATH)

    # Admin user details
    ADMIN_USER_ID = 0  # Reserved ID for system admin
    ADMIN_USERNAME = "admin"
    ADMIN_FIRST_NAME = "Admin"
    ADMIN_LAST_NAME = "User"
    ADMIN_EMAIL = "admin@system.local"

    try:
        # Check if admin user already exists
        existing_user = db.get_user(ADMIN_USER_ID)

        if existing_user:
            print(f"\n[INFO] Admin user already exists!")
            print(f"  User ID: {existing_user['user_id']}")
            print(f"  Username: {existing_user['username']}")
            print(f"  Name: {existing_user['first_name']} {existing_user.get('last_name', '')}")

            # Check if has admin role
            user_role = db.get_user_primary_role(ADMIN_USER_ID)
            if user_role and user_role['role_name'] == 'admin':
                print(f"  Role: admin (level {user_role['level']})")
                print("\n[SUCCESS] Default admin user is already set up!")
                print("\n" + "=" * 60)
                print("Login Credentials:")
                print("=" * 60)
                print(f"  User ID: {ADMIN_USER_ID}")
                print(f"  Password: admin")
                print("=" * 60)
                return True
            else:
                print("\n[INFO] Admin user exists but doesn't have admin role. Assigning admin role...")
        else:
            print("\n[STEP 1] Creating admin user...")

            # Add admin user
            db.add_user(
                user_id=ADMIN_USER_ID,
                username=ADMIN_USERNAME,
                first_name=ADMIN_FIRST_NAME,
                last_name=ADMIN_LAST_NAME,
                email=ADMIN_EMAIL,
                phone=None
            )

            print(f"  [OK] Admin user created successfully")
            print(f"  User ID: {ADMIN_USER_ID}")
            print(f"  Username: {ADMIN_USERNAME}")

        # Assign admin role
        print("\n[STEP 2] Assigning admin role...")

        # Get admin role
        admin_role = db.get_role_by_name('admin')

        if not admin_role:
            print("[ERROR] Admin role not found in database!")
            print("[INFO] Please run the migration script first:")
            print("  python scripts/migrate_database.py")
            return False

        # Assign role (no department needed for admin)
        success = db.assign_role(
            user_id=ADMIN_USER_ID,
            role_name='admin',
            department_id=None,
            assigned_by=None,
            is_primary=True
        )

        if success:
            print(f"  [OK] Admin role assigned successfully")
            print(f"  Role: {admin_role['name']}")
            level = admin_role.get('level', 'N/A')
            print(f"  Level: {level}")
            print(f"  Permissions: {admin_role.get('permissions', {})}")
        else:
            print("[ERROR] Failed to assign admin role")
            return False

        # Verify creation
        print("\n[STEP 3] Verifying admin user...")

        user = db.get_user(ADMIN_USER_ID)
        user_role = db.get_user_primary_role(ADMIN_USER_ID)

        if user and user_role and user_role['role_name'] == 'admin':
            print("  [OK] Verification successful!")
            print(f"  User: {user['first_name']} {user.get('last_name', '')} (@{user['username']})")
            level = user_role.get('level', 'N/A')
            print(f"  Role: {user_role['role_name']} (level {level})")

            print("\n" + "=" * 60)
            print("[SUCCESS] Default Admin User Created!")
            print("=" * 60)
            print("\nYou can now login to the web panel with:")
            print("-" * 60)
            print(f"  User ID: {ADMIN_USER_ID}")
            print(f"  Password: admin")
            print("-" * 60)
            print("\nWeb Panel URL: http://localhost:5000/login")
            print("=" * 60)

            return True
        else:
            print("[ERROR] Verification failed!")
            return False

    except Exception as e:
        print(f"\n[ERROR] Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_database_exists():
    """Check if database exists and is migrated"""
    if not os.path.exists(config.DB_PATH):
        print("[ERROR] Database not found!")
        print(f"[INFO] Expected location: {config.DB_PATH}")
        print("\n[INFO] Please run the migration script first:")
        print("  python scripts/migrate_database.py")
        return False

    # Check if database has required tables
    conn = sqlite3.connect(config.DB_PATH)
    cursor = conn.cursor()

    required_tables = ['users', 'roles', 'user_roles', 'departments']
    missing_tables = []

    for table in required_tables:
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table,)
        )
        if not cursor.fetchone():
            missing_tables.append(table)

    conn.close()

    if missing_tables:
        print("[ERROR] Database is missing required tables:")
        for table in missing_tables:
            print(f"  - {table}")
        print("\n[INFO] Please run the migration script first:")
        print("  python scripts/migrate_database.py")
        return False

    return True


def main():
    """Main entry point"""
    print("\n")

    # Check if database exists
    if not check_database_exists():
        return

    # Create default admin
    success = create_default_admin()

    if success:
        print("\n[INFO] Next steps:")
        print("  1. Start the web server: python web/app.py")
        print("  2. Open http://localhost:5000/login")
        print("  3. Login with User ID: 0, Password: admin")
        print("\n")
    else:
        print("\n[ERROR] Failed to create default admin user.")
        print("[INFO] Please check the errors above and try again.")
        print("\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
