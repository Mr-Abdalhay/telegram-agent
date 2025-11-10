#!/usr/bin/env python3
"""
Database Migration Script
Migrates existing database to new reporting system schema
"""

import sqlite3
import os
import json
from datetime import datetime
import shutil


class DatabaseMigration:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.backup_path = f"{db_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.conn = None
        self.cursor = None

    def backup_database(self):
        """Create backup of existing database"""
        if os.path.exists(self.db_path):
            print(f"[INFO] Creating backup: {self.backup_path}")
            shutil.copy2(self.db_path, self.backup_path)
            print(f"[SUCCESS] Backup created successfully")
        else:
            print(f"[WARNING] No existing database found at {self.db_path}")

    def connect(self):
        """Connect to database"""
        self.conn = sqlite3.connect(self.db_path)
        self.cursor = self.conn.cursor()
        print(f"[INFO] Connected to database: {self.db_path}")

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            print("[INFO] Database connection closed")

    def table_exists(self, table_name: str) -> bool:
        """Check if table exists"""
        self.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return self.cursor.fetchone() is not None

    def column_exists(self, table_name: str, column_name: str) -> bool:
        """Check if column exists in table"""
        self.cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in self.cursor.fetchall()]
        return column_name in columns

    def migrate_users_table(self):
        """Enhance users table with new fields"""
        print("\n[STEP] Migrating users table...")

        if not self.table_exists('users'):
            print("[ERROR] Users table does not exist. Creating from scratch...")
            return False

        # Add new columns if they don't exist
        new_columns = [
            ('email', 'TEXT UNIQUE'),
            ('phone', 'TEXT'),
            ('is_active', 'BOOLEAN DEFAULT 1'),
            ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        ]

        for col_name, col_type in new_columns:
            if not self.column_exists('users', col_name):
                self.cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
                print(f"  [OK] Added column: {col_name}")
            else:
                print(f"  [SKIP]  Column already exists: {col_name}")

        self.conn.commit()
        print("[OK] Users table migrated")
        return True

    def create_departments_table(self):
        """Create departments table"""
        print("\n[STEP] Creating departments table...")

        if self.table_exists('departments'):
            print("  [SKIP]  Departments table already exists")
            return True

        self.cursor.execute('''
            CREATE TABLE departments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                name_en TEXT,
                description TEXT,
                parent_department_id INTEGER,
                level INTEGER DEFAULT 0,
                manager_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_department_id) REFERENCES departments(id) ON DELETE SET NULL,
                FOREIGN KEY (manager_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        ''')

        # Create indexes
        self.cursor.execute('CREATE INDEX idx_departments_parent ON departments(parent_department_id)')
        self.cursor.execute('CREATE INDEX idx_departments_manager ON departments(manager_id)')
        self.cursor.execute('CREATE INDEX idx_departments_name ON departments(name)')

        # Insert default departments
        default_departments = [
            ('الإدارة العامة', 'General Management', 'الإدارة العامة للشركة', None, 0),
            ('المبيعات', 'Sales', 'قسم المبيعات', None, 0),
            ('التسويق', 'Marketing', 'قسم التسويق', None, 0),
            ('الموارد البشرية', 'Human Resources', 'قسم الموارد البشرية', None, 0),
            ('تقنية المعلومات', 'IT', 'قسم تقنية المعلومات', None, 0),
        ]

        for dept in default_departments:
            self.cursor.execute(
                'INSERT INTO departments (name, name_en, description, parent_department_id, level) VALUES (?, ?, ?, ?, ?)',
                dept
            )

        self.conn.commit()
        print("[OK] Departments table created with sample data")
        return True

    def create_roles_table(self):
        """Create roles table with predefined roles"""
        print("\n[STEP] Creating roles table...")

        if self.table_exists('roles'):
            print("  [SKIP]  Roles table already exists")
            return True

        self.cursor.execute('''
            CREATE TABLE roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                name_ar TEXT,
                description TEXT,
                level INTEGER DEFAULT 0,
                permissions TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        self.cursor.execute('CREATE INDEX idx_roles_name ON roles(name)')

        # Insert default roles
        roles = [
            ('employee', 'موظف', 'Basic employee - can create and view own reports', 10,
             json.dumps({"can_create_report": True, "can_view_own": True, "can_view_department": False, "can_approve": False, "can_create_cumulative": False})),

            ('manager', 'مدير', 'Department manager - can view and approve department reports', 50,
             json.dumps({"can_create_report": True, "can_view_own": True, "can_view_department": True, "can_approve": True, "can_create_cumulative": False})),

            ('upper_manager', 'مدير أعلى', 'Upper management - can view hierarchical reports and create cumulative reports', 70,
             json.dumps({"can_create_report": True, "can_view_own": True, "can_view_department": True, "can_view_subdepartments": True, "can_approve": True, "can_create_cumulative": True})),

            ('admin', 'مسؤول النظام', 'System administrator - full access', 99,
             json.dumps({"can_create_report": True, "can_view_all": True, "can_approve": True, "can_create_cumulative": True, "can_manage_users": True, "can_manage_departments": True}))
        ]

        for role in roles:
            self.cursor.execute(
                'INSERT INTO roles (name, name_ar, description, level, permissions) VALUES (?, ?, ?, ?, ?)',
                role
            )

        self.conn.commit()
        print("[OK] Roles table created with default roles")
        return True

    def create_user_roles_table(self):
        """Create user_roles table"""
        print("\n[STEP] Creating user_roles table...")

        if self.table_exists('user_roles'):
            print("  [SKIP]  User_roles table already exists")
            return True

        self.cursor.execute('''
            CREATE TABLE user_roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                department_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                assigned_by INTEGER,
                assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                FOREIGN KEY (assigned_by) REFERENCES users(user_id) ON DELETE SET NULL,
                UNIQUE(user_id, role_id, department_id)
            )
        ''')

        # Create indexes
        self.cursor.execute('CREATE INDEX idx_user_roles_user ON user_roles(user_id)')
        self.cursor.execute('CREATE INDEX idx_user_roles_role ON user_roles(role_id)')
        self.cursor.execute('CREATE INDEX idx_user_roles_department ON user_roles(department_id)')

        # Assign all existing users the 'employee' role by default
        self.cursor.execute("SELECT user_id FROM users")
        existing_users = self.cursor.fetchall()

        self.cursor.execute("SELECT id FROM roles WHERE name = 'employee'")
        employee_role_id = self.cursor.fetchone()[0]

        self.cursor.execute("SELECT id FROM departments LIMIT 1")
        default_dept = self.cursor.fetchone()
        default_dept_id = default_dept[0] if default_dept else None

        for (user_id,) in existing_users:
            self.cursor.execute(
                'INSERT OR IGNORE INTO user_roles (user_id, role_id, department_id) VALUES (?, ?, ?)',
                (user_id, employee_role_id, default_dept_id)
            )

        self.conn.commit()
        print(f"[OK] User_roles table created and {len(existing_users)} users assigned employee role")
        return True

    def create_reports_table(self):
        """Create reports table"""
        print("\n[STEP] Creating reports table...")

        if self.table_exists('reports'):
            print("  [SKIP]  Reports table already exists")
            return True

        self.cursor.execute('''
            CREATE TABLE reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                report_type TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                priority TEXT DEFAULT 'normal',
                visibility TEXT DEFAULT 'department',
                submitted_by INTEGER NOT NULL,
                department_id INTEGER NOT NULL,
                is_cumulative BOOLEAN DEFAULT 0,
                source_report_ids TEXT,
                aggregation_type TEXT,
                aggregation_period TEXT,
                aggregation_start_date DATE,
                aggregation_end_date DATE,
                metadata TEXT,
                tags TEXT,
                submitted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submitted_by) REFERENCES users(user_id) ON DELETE CASCADE,
                FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
            )
        ''')

        # Create indexes
        indexes = [
            'CREATE INDEX idx_reports_department ON reports(department_id)',
            'CREATE INDEX idx_reports_submitter ON reports(submitted_by)',
            'CREATE INDEX idx_reports_status ON reports(status)',
            'CREATE INDEX idx_reports_type ON reports(report_type)',
            'CREATE INDEX idx_reports_cumulative ON reports(is_cumulative)',
            'CREATE INDEX idx_reports_submitted_at ON reports(submitted_at)',
            'CREATE INDEX idx_reports_dates ON reports(aggregation_start_date, aggregation_end_date)'
        ]

        for index_sql in indexes:
            self.cursor.execute(index_sql)

        self.conn.commit()
        print("[OK] Reports table created")
        return True

    def create_supporting_tables(self):
        """Create all supporting tables"""
        print("\n[STEP] Creating supporting tables...")

        tables = {
            'report_aggregations': '''
                CREATE TABLE report_aggregations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cumulative_report_id INTEGER NOT NULL,
                    source_report_id INTEGER NOT NULL,
                    department_id INTEGER,
                    weight REAL DEFAULT 1.0,
                    included_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (cumulative_report_id) REFERENCES reports(id) ON DELETE CASCADE,
                    FOREIGN KEY (source_report_id) REFERENCES reports(id) ON DELETE CASCADE,
                    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
                )
            ''',
            'report_access': '''
                CREATE TABLE report_access (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    user_id INTEGER,
                    role_id INTEGER,
                    department_id INTEGER,
                    access_type TEXT NOT NULL,
                    granted_by INTEGER,
                    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP,
                    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                    FOREIGN KEY (granted_by) REFERENCES users(user_id) ON DELETE SET NULL
                )
            ''',
            'report_approvals': '''
                CREATE TABLE report_approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    approver_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    approved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
                    FOREIGN KEY (approver_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''',
            'report_comments': '''
                CREATE TABLE report_comments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    report_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    parent_comment_id INTEGER,
                    comment TEXT NOT NULL,
                    is_internal BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
                    FOREIGN KEY (parent_comment_id) REFERENCES report_comments(id) ON DELETE CASCADE
                )
            ''',
            'audit_log': '''
                CREATE TABLE audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT NOT NULL,
                    entity_type TEXT,
                    entity_id INTEGER,
                    old_value TEXT,
                    new_value TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
                )
            ''',
            'notifications': '''
                CREATE TABLE notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT,
                    related_entity_type TEXT,
                    related_entity_id INTEGER,
                    is_read BOOLEAN DEFAULT 0,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    read_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''',
            'report_templates': '''
                CREATE TABLE report_templates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    template_structure TEXT NOT NULL,
                    department_id INTEGER,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
                    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
                )
            '''
        }

        for table_name, create_sql in tables.items():
            if not self.table_exists(table_name):
                self.cursor.execute(create_sql)
                print(f"  [OK] Created table: {table_name}")
            else:
                print(f"  [SKIP]  Table already exists: {table_name}")

        self.conn.commit()
        print("[OK] Supporting tables created")
        return True

    def migrate_conversations_table(self):
        """Enhance conversations table"""
        print("\n[STEP] Migrating conversations table...")

        if not self.table_exists('conversations'):
            print("  [ERROR] Conversations table does not exist")
            return False

        new_columns = [
            ('message_type', "TEXT DEFAULT 'text'"),
            ('context', 'TEXT')
        ]

        for col_name, col_type in new_columns:
            if not self.column_exists('conversations', col_name):
                self.cursor.execute(f"ALTER TABLE conversations ADD COLUMN {col_name} {col_type}")
                print(f"  [OK] Added column: {col_name}")
            else:
                print(f"  [SKIP]  Column already exists: {col_name}")

        self.conn.commit()
        print("[OK] Conversations table migrated")
        return True

    def migrate_summaries_table(self):
        """Enhance summaries table"""
        print("\n[STEP] Migrating summaries table...")

        if not self.table_exists('summaries'):
            print("  [ERROR] Summaries table does not exist")
            return False

        new_columns = [
            ('report_id', 'INTEGER'),
            ('summary_type', "TEXT DEFAULT 'conversation'")
        ]

        for col_name, col_type in new_columns:
            if not self.column_exists('summaries', col_name):
                self.cursor.execute(f"ALTER TABLE summaries ADD COLUMN {col_name} {col_type}")
                print(f"  [OK] Added column: {col_name}")
            else:
                print(f"  [SKIP]  Column already exists: {col_name}")

        self.conn.commit()
        print("[OK] Summaries table migrated")
        return True

    def create_views(self):
        """Create useful views"""
        print("\n[STEP] Creating views...")

        # Drop views if they exist
        views_to_drop = ['v_user_roles', 'v_reports_full', 'v_department_hierarchy']
        for view in views_to_drop:
            self.cursor.execute(f"DROP VIEW IF EXISTS {view}")

        # Create views
        self.cursor.execute('''
            CREATE VIEW v_user_roles AS
            SELECT
                u.user_id,
                u.username,
                u.first_name,
                u.last_name,
                r.name as role_name,
                r.name_ar as role_name_ar,
                r.level as role_level,
                d.name as department_name,
                d.id as department_id,
                ur.is_active,
                ur.assigned_at
            FROM users u
            LEFT JOIN user_roles ur ON u.user_id = ur.user_id AND ur.is_active = 1
            LEFT JOIN roles r ON ur.role_id = r.id
            LEFT JOIN departments d ON ur.department_id = d.id
        ''')

        print("  [OK] Created view: v_user_roles")

        self.cursor.execute('''
            CREATE VIEW v_reports_full AS
            SELECT
                r.id,
                r.title,
                r.report_type,
                r.status,
                r.priority,
                r.is_cumulative,
                r.aggregation_type,
                r.submitted_at,
                u.username as submitter_username,
                u.first_name as submitter_first_name,
                d.name as department_name,
                d.level as department_level
            FROM reports r
            JOIN users u ON r.submitted_by = u.user_id
            JOIN departments d ON r.department_id = d.id
        ''')

        print("  [OK] Created view: v_reports_full")

        self.conn.commit()
        print("[OK] Views created")
        return True

    def create_triggers(self):
        """Create update triggers"""
        print("\n[STEP] Creating triggers...")

        triggers = {
            'update_users_timestamp': '''
                CREATE TRIGGER IF NOT EXISTS update_users_timestamp
                AFTER UPDATE ON users
                BEGIN
                    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
                END
            ''',
            'update_reports_timestamp': '''
                CREATE TRIGGER IF NOT EXISTS update_reports_timestamp
                AFTER UPDATE ON reports
                BEGIN
                    UPDATE reports SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            ''',
            'update_departments_timestamp': '''
                CREATE TRIGGER IF NOT EXISTS update_departments_timestamp
                AFTER UPDATE ON departments
                BEGIN
                    UPDATE departments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
            '''
        }

        for trigger_name, trigger_sql in triggers.items():
            self.cursor.execute(trigger_sql)
            print(f"  [OK] Created trigger: {trigger_name}")

        self.conn.commit()
        print("[OK] Triggers created")
        return True

    def run_migration(self):
        """Run complete migration"""
        print("=" * 60)
        print("🚀 Starting Database Migration")
        print("=" * 60)

        try:
            # Backup
            self.backup_database()

            # Connect
            self.connect()

            # Run migrations in order
            self.migrate_users_table()
            self.create_departments_table()
            self.create_roles_table()
            self.create_user_roles_table()
            self.create_reports_table()
            self.create_supporting_tables()
            self.migrate_conversations_table()
            self.migrate_summaries_table()
            self.create_views()
            self.create_triggers()

            print("\n" + "=" * 60)
            print("[OK] Migration completed successfully!")
            print("=" * 60)
            print(f"\n📊 Database Schema Summary:")
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = self.cursor.fetchall()
            print(f"\nTotal tables: {len(tables)}")
            for (table_name,) in tables:
                print(f"  • {table_name}")

            # Close connection
            self.close()

            return True

        except Exception as e:
            print(f"\n[ERROR] Migration failed: {e}")
            print(f"💾 Database backup available at: {self.backup_path}")
            if self.conn:
                self.conn.rollback()
                self.close()
            return False


def create_fresh_database(db_path: str) -> bool:
    """Create fresh database from schema file"""
    import sys

    print(f"\n[INFO] No existing database found. Creating fresh database at: {db_path}")

    # Ensure data directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        print(f"[INFO] Created directory: {db_dir}")

    # Read schema file
    schema_path = os.path.join(os.path.dirname(__file__), '..', 'database_schema.sql')

    if not os.path.exists(schema_path):
        print(f"[ERROR] Schema file not found at: {schema_path}")
        return False

    print(f"[INFO] Reading schema from: {schema_path}")

    try:
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()

        # Connect to database (will create it)
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute('PRAGMA foreign_keys = ON')

        # Execute schema
        print("[INFO] Creating database tables...")
        cursor.executescript(schema_sql)

        conn.commit()
        conn.close()

        print("[SUCCESS] Database created successfully!")
        return True

    except Exception as e:
        print(f"[ERROR] Failed to create database: {str(e)}")
        return False


def mainDataBase():
    """Main entry point"""
    import sys
    # from config import config

    db_path = './data/conversations.db'

    print(f"\n[INFO] Database path: {db_path}\n")

    # Check if database exists
    if not os.path.exists(db_path):
        # Create fresh database
        success = create_fresh_database(db_path)
        if success:
            print("\n[SUCCESS] Fresh database created successfully!")
            print("[INFO] You can now start the bot with: python main_enhanced.py")
        else:
            print("\n[ERROR] Failed to create database.")
        sys.exit(0 if success else 1)

    # Database exists, perform migration
    print("[INFO] Existing database found. Running migration...")

    # Confirm migration
    if len(sys.argv) > 1 and sys.argv[1] == '--force':
        confirm = 'yes'
    else:
        confirm = input("[WARNING] This will modify your database. Continue? (yes/no): ")

    if confirm.lower() != 'yes':
        print("[INFO] Migration cancelled")
        return

    # Run migration
    migration = DatabaseMigration(db_path)
    success = migration.run_migration()

    if success:
        print("\n[SUCCESS] You can now use the new reporting system!")
        print("[INFO] Next steps:")
        print("  1. Update bot/database.py with new methods")
        print("  2. Add new bot command handlers")
        print("  3. Test the system with sample data")
    else:
        print("\n[ERROR] Migration failed. Please check the errors above.")

    # sys.exit(0 if success else 1)


if __name__ == '__main__':
    mainDataBase()
