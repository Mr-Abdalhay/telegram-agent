#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add is_primary column to user_roles table
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


def add_is_primary_column():
    """Add is_primary column if it doesn't exist"""

    db_path = config.DB_PATH if hasattr(config, 'DB_PATH') else './data/conversations.db'

    if not os.path.exists(db_path):
        print("[ERROR] Database not found!")
        sys.exit(1)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("[INFO] Checking user_roles table...")

    # Check if column exists
    cursor.execute('PRAGMA table_info(user_roles)')
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]

    print(f"[INFO] Current columns: {', '.join(column_names)}")

    if 'is_primary' in column_names:
        print("[INFO] Column 'is_primary' already exists!")
        conn.close()
        return

    print("[INFO] Adding 'is_primary' column...")

    # Add the column
    cursor.execute('ALTER TABLE user_roles ADD COLUMN is_primary INTEGER DEFAULT 1')

    # Set all existing roles to primary
    cursor.execute('UPDATE user_roles SET is_primary = 1')

    conn.commit()
    conn.close()

    print("[OK] Column added successfully!")
    print("[INFO] All existing roles set to primary=1")


if __name__ == '__main__':
    print("\n" + "="*60)
    print("  ADD is_primary COLUMN TO user_roles")
    print("="*60 + "\n")

    add_is_primary_column()

    print("\n" + "="*60 + "\n")
