#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fix Roles Permissions
Updates roles table with proper JSON permissions
"""

import sqlite3
import os
import sys
import io
import json

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config


def fix_roles():
    """Fix roles permissions with proper JSON"""

    db_path = config.DB_PATH if hasattr(config, 'DB_PATH') else './data/conversations.db'

    if not os.path.exists(db_path):
        print("[ERROR] Database not found!")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n[INFO] Checking roles table...")

    # Check table structure
    cursor.execute('PRAGMA table_info(roles)')
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"[INFO] Columns: {', '.join(column_names)}")

    # Get all roles
    cursor.execute('SELECT * FROM roles')
    roles = cursor.fetchall()

    print(f"[INFO] Found {len(roles)} roles\n")

    # Define proper permissions for each role
    # IMPORTANT: Use singular form to match permissions.py checks
    role_permissions = {
        'employee': {
            'can_create_report': True,
            'can_view_own_report': True,
            'can_edit_own_report': True,
            'can_approve_report': False,
            'can_view_all_report': False,
            'can_create_cumulative_report': False,
            'can_view_subdepartments': False,
            'can_manage_users': False,
            'can_manage_departments': False
        },
        'manager': {
            'can_create_report': True,
            'can_view_own_report': True,
            'can_edit_own_report': True,
            'can_approve_report': True,
            'can_view_all_report': False,
            'can_create_cumulative_report': False,
            'can_view_subdepartments': False,
            'can_manage_users': False,
            'can_manage_departments': False
        },
        'upper_manager': {
            'can_create_report': True,
            'can_view_own_report': True,
            'can_edit_own_report': True,
            'can_approve_report': True,
            'can_view_all_report': False,
            'can_create_cumulative_report': True,
            'can_view_subdepartments': True,
            'can_manage_users': False,
            'can_manage_departments': False
        },
        'admin': {
            'can_create_report': True,
            'can_view_own_report': True,
            'can_edit_own_report': True,
            'can_approve_report': True,
            'can_view_all_report': True,
            'can_create_cumulative_report': True,
            'can_view_subdepartments': True,
            'can_manage_users': True,
            'can_manage_departments': True
        }
    }

    # Update each role
    for role in roles:
        role_id = role[0]
        role_name = role[1]

        if role_name in role_permissions:
            new_permissions = json.dumps(role_permissions[role_name])

            cursor.execute(
                'UPDATE roles SET permissions = ? WHERE id = ?',
                (new_permissions, role_id)
            )

            print(f"[OK] Updated: {role_name}")
        else:
            print(f"[SKIP] Unknown role: {role_name}")

    conn.commit()

    # Verify
    print("\n[INFO] Verifying updates...")
    cursor.execute('SELECT name, permissions FROM roles')
    roles = cursor.fetchall()

    for role_name, permissions_json in roles:
        try:
            perms = json.loads(permissions_json)
            print(f"[OK] {role_name}: {len(perms)} permissions")
        except:
            print(f"[ERROR] {role_name}: Invalid JSON")

    conn.close()

    print("\n[SUCCESS] Roles permissions fixed!")
    print("[INFO] Try /register again in the bot\n")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  FIX ROLES PERMISSIONS")
    print("="*60)

    fix_roles()

    print("="*60 + "\n")
