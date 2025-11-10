#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create Initial Departments
Run this once to create the first departments in the system
"""

import sqlite3
import os
import sys
import io

# Set UTF-8 encoding for stdout
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config


def create_initial_departments():
    """Create initial departments for the organization"""

    db_path = config.DB_PATH if hasattr(config, 'DB_PATH') else './data/conversations.db'

    if not os.path.exists(db_path):
        print("[ERROR] Database not found! Run migrate_database.py first.")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute('PRAGMA foreign_keys = ON')

    # Check if departments already exist
    cursor.execute('SELECT COUNT(*) FROM departments')
    existing_count = cursor.fetchone()[0]

    if existing_count > 0:
        print(f"[INFO] Database already has {existing_count} departments.")
        print("[INFO] Existing departments:")
        cursor.execute('SELECT id, name, name_en FROM departments ORDER BY level, id')
        for row in cursor.fetchall():
            print(f"  {row[0]}. {row[1]} / {row[2]}")

        confirm = input("\n[WARNING] Do you want to add MORE departments? (yes/no): ")
        if confirm.lower() != 'yes':
            print("[INFO] Operation cancelled.")
            conn.close()
            sys.exit(0)

    print("\n[INFO] Creating initial departments...\n")

    # Initial departments to create
    departments = [
        {
            'name': 'الإدارة العامة',
            'name_en': 'General Management',
            'description': 'الإدارة العليا للمؤسسة',
            'parent_id': None,
            'level': 0
        },
        {
            'name': 'قسم المبيعات',
            'name_en': 'Sales Department',
            'description': 'قسم المبيعات والتسويق',
            'parent_id': None,
            'level': 0
        },
        {
            'name': 'قسم الهندسة',
            'name_en': 'Engineering Department',
            'description': 'قسم التطوير والهندسة',
            'parent_id': None,
            'level': 0
        },
        {
            'name': 'قسم الموارد البشرية',
            'name_en': 'HR Department',
            'description': 'قسم الموارد البشرية',
            'parent_id': None,
            'level': 0
        },
        {
            'name': 'قسم المالية',
            'name_en': 'Finance Department',
            'description': 'القسم المالي والمحاسبة',
            'parent_id': None,
            'level': 0
        },
    ]

    created_count = 0

    for dept in departments:
        try:
            cursor.execute('''
                INSERT INTO departments (name, name_en, description, parent_department_id, level, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (dept['name'], dept['name_en'], dept['description'], dept['parent_id'], dept['level']))

            dept_id = cursor.lastrowid
            print(f"[OK] Created: {dept['name']} / {dept['name_en']} (ID: {dept_id})")
            created_count += 1

        except sqlite3.IntegrityError as e:
            print(f"[SKIP] Already exists: {dept['name']} / {dept['name_en']}")

    conn.commit()
    conn.close()

    print(f"\n[SUCCESS] Created {created_count} new departments!")
    print("[INFO] Users can now use /register to join a department")
    print("\n[INFO] Available departments:")

    # Show final list
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, name_en FROM departments WHERE is_active = 1 ORDER BY level, id')

    for row in cursor.fetchall():
        print(f"  {row[0]}. {row[1]} / {row[2]}")

    conn.close()


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  CREATE INITIAL DEPARTMENTS")
    print("="*60)

    create_initial_departments()

    print("\n[INFO] Next steps:")
    print("  1. Start the bot: python main_enhanced.py")
    print("  2. Send /start to your bot")
    print("  3. Use /register to join a department")
    print("  4. Contact admin to get manager/admin role if needed")
    print("="*60 + "\n")
