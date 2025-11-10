-- ============================================================
-- TELEGRAM BOT REPORTING SYSTEM - DATABASE SCHEMA
-- ============================================================
-- Version: 2.0
-- Description: Hierarchical reporting system with role-based access control
-- Features: Departments, Roles, Reports, Cumulative Reports, Approvals
-- ============================================================

-- ============================================================
-- 1. USERS TABLE (Enhanced)
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    email TEXT UNIQUE,
    phone TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- ============================================================
-- 2. DEPARTMENTS TABLE (Hierarchical Structure)
-- ============================================================
CREATE TABLE IF NOT EXISTS departments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_en TEXT,
    description TEXT,
    parent_department_id INTEGER,
    level INTEGER DEFAULT 0, -- 0=root, 1=first level, etc.
    manager_id INTEGER, -- Department manager
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_department_id) REFERENCES departments(id) ON DELETE SET NULL,
    FOREIGN KEY (manager_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_departments_parent ON departments(parent_department_id);
CREATE INDEX idx_departments_manager ON departments(manager_id);
CREATE INDEX idx_departments_name ON departments(name);

-- ============================================================
-- 3. ROLES TABLE (Access Control)
-- ============================================================
CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE, -- 'employee', 'manager', 'upper_manager', 'admin'
    name_ar TEXT, -- Arabic name
    description TEXT,
    level INTEGER DEFAULT 0, -- Role hierarchy level (0=lowest, 99=highest)
    permissions TEXT, -- JSON: {"can_create_report": true, "can_approve": false}
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pre-populate roles
INSERT OR IGNORE INTO roles (name, name_ar, description, level, permissions) VALUES
('employee', 'موظف', 'Basic employee - can create and view own reports', 10,
 '{"can_create_report": true, "can_view_own": true, "can_view_department": false, "can_approve": false, "can_create_cumulative": false}'),

('manager', 'مدير', 'Department manager - can view and approve department reports', 50,
 '{"can_create_report": true, "can_view_own": true, "can_view_department": true, "can_approve": true, "can_create_cumulative": false}'),

('upper_manager', 'مدير أعلى', 'Upper management - can view hierarchical reports and create cumulative reports', 70,
 '{"can_create_report": true, "can_view_own": true, "can_view_department": true, "can_view_subdepartments": true, "can_approve": true, "can_create_cumulative": true}'),

('admin', 'مسؤول النظام', 'System administrator - full access', 99,
 '{"can_create_report": true, "can_view_all": true, "can_approve": true, "can_create_cumulative": true, "can_manage_users": true, "can_manage_departments": true}');

CREATE INDEX idx_roles_name ON roles(name);

-- ============================================================
-- 4. USER ROLES TABLE (User-Role-Department Assignment)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    department_id INTEGER, -- Nullable for admin role
    is_active BOOLEAN DEFAULT 1,
    assigned_by INTEGER, -- Who assigned this role
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- Optional expiration date
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    FOREIGN KEY (assigned_by) REFERENCES users(user_id) ON DELETE SET NULL,
    UNIQUE(user_id, role_id, department_id) -- User can't have duplicate role in same department
);

CREATE INDEX idx_user_roles_user ON user_roles(user_id);
CREATE INDEX idx_user_roles_role ON user_roles(role_id);
CREATE INDEX idx_user_roles_department ON user_roles(department_id);

-- ============================================================
-- 5. REPORTS TABLE (Main Reports)
-- ============================================================
CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL, -- Main report content (can be JSON for structured data)
    report_type TEXT NOT NULL, -- 'daily', 'weekly', 'monthly', 'incident', 'cumulative', 'custom'
    status TEXT DEFAULT 'draft', -- 'draft', 'submitted', 'pending_approval', 'approved', 'rejected', 'archived'
    priority TEXT DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    visibility TEXT DEFAULT 'department', -- 'private', 'department', 'public'

    -- Ownership
    submitted_by INTEGER NOT NULL,
    department_id INTEGER NOT NULL,

    -- Cumulative Report Fields
    is_cumulative BOOLEAN DEFAULT 0,
    source_report_ids TEXT, -- JSON array: [1, 2, 3, 4]
    aggregation_type TEXT, -- 'summary', 'statistical', 'detailed'
    aggregation_period TEXT, -- 'daily', 'weekly', 'monthly', 'quarterly', 'yearly', 'custom'
    aggregation_start_date DATE,
    aggregation_end_date DATE,

    -- Metadata
    metadata TEXT, -- JSON: {"metrics": {...}, "attachments": [...]}
    tags TEXT, -- JSON: ["sales", "q1", "important"]

    -- Timestamps
    submitted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (submitted_by) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE
);

CREATE INDEX idx_reports_department ON reports(department_id);
CREATE INDEX idx_reports_submitter ON reports(submitted_by);
CREATE INDEX idx_reports_status ON reports(status);
CREATE INDEX idx_reports_type ON reports(report_type);
CREATE INDEX idx_reports_cumulative ON reports(is_cumulative);
CREATE INDEX idx_reports_submitted_at ON reports(submitted_at);
CREATE INDEX idx_reports_dates ON reports(aggregation_start_date, aggregation_end_date);

-- ============================================================
-- 6. REPORT AGGREGATIONS TABLE (Track Cumulative Report Sources)
-- ============================================================
CREATE TABLE IF NOT EXISTS report_aggregations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cumulative_report_id INTEGER NOT NULL,
    source_report_id INTEGER NOT NULL,
    department_id INTEGER,
    weight REAL DEFAULT 1.0, -- For weighted calculations
    included_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cumulative_report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (source_report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE SET NULL
);

CREATE INDEX idx_report_agg_cumulative ON report_aggregations(cumulative_report_id);
CREATE INDEX idx_report_agg_source ON report_aggregations(source_report_id);
CREATE INDEX idx_report_agg_department ON report_aggregations(department_id);

-- ============================================================
-- 7. REPORT ACCESS TABLE (Fine-grained Access Control)
-- ============================================================
CREATE TABLE IF NOT EXISTS report_access (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    user_id INTEGER, -- Specific user (nullable if role-based)
    role_id INTEGER, -- Specific role (nullable if user-based)
    department_id INTEGER, -- Specific department (nullable)
    access_type TEXT NOT NULL, -- 'view', 'edit', 'approve', 'delete'
    granted_by INTEGER,
    granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP, -- Optional expiration
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    FOREIGN KEY (granted_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_report_access_report ON report_access(report_id);
CREATE INDEX idx_report_access_user ON report_access(user_id);
CREATE INDEX idx_report_access_role ON report_access(role_id);

-- ============================================================
-- 8. REPORT APPROVALS TABLE (Approval Workflow)
-- ============================================================
CREATE TABLE IF NOT EXISTS report_approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    approver_id INTEGER NOT NULL,
    status TEXT NOT NULL, -- 'pending', 'approved', 'rejected', 'changes_requested'
    notes TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (approver_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_report_approvals_report ON report_approvals(report_id);
CREATE INDEX idx_report_approvals_approver ON report_approvals(approver_id);
CREATE INDEX idx_report_approvals_status ON report_approvals(status);

-- ============================================================
-- 9. REPORT COMMENTS TABLE (Discussions & Feedback)
-- ============================================================
CREATE TABLE IF NOT EXISTS report_comments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    parent_comment_id INTEGER, -- For threaded comments
    comment TEXT NOT NULL,
    is_internal BOOLEAN DEFAULT 0, -- Internal notes vs public comments
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_comment_id) REFERENCES report_comments(id) ON DELETE CASCADE
);

CREATE INDEX idx_report_comments_report ON report_comments(report_id);
CREATE INDEX idx_report_comments_user ON report_comments(user_id);
CREATE INDEX idx_report_comments_parent ON report_comments(parent_comment_id);

-- ============================================================
-- 10. CONVERSATIONS TABLE (Existing - Enhanced)
-- ============================================================
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    message TEXT,
    response TEXT,
    message_type TEXT DEFAULT 'text', -- 'text', 'command', 'report_related'
    context TEXT, -- JSON: {"report_id": 123, "action": "create"}
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_conversations_user ON conversations(user_id);
CREATE INDEX idx_conversations_timestamp ON conversations(timestamp);

-- ============================================================
-- 11. SUMMARIES TABLE (Existing - Enhanced)
-- ============================================================
CREATE TABLE IF NOT EXISTS summaries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    report_id INTEGER, -- Link to report if summary is for a report
    summary TEXT,
    summary_type TEXT DEFAULT 'conversation', -- 'conversation', 'report', 'cumulative'
    date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (report_id) REFERENCES reports(id) ON DELETE CASCADE
);

CREATE INDEX idx_summaries_user ON summaries(user_id);
CREATE INDEX idx_summaries_report ON summaries(report_id);
CREATE INDEX idx_summaries_date ON summaries(date);

-- ============================================================
-- 12. AUDIT LOG TABLE (Track All Important Actions)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL, -- 'create_report', 'approve_report', 'assign_role', etc.
    entity_type TEXT, -- 'report', 'user', 'department', etc.
    entity_id INTEGER,
    old_value TEXT, -- JSON of previous state
    new_value TEXT, -- JSON of new state
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

-- ============================================================
-- 13. NOTIFICATIONS TABLE (Alert System)
-- ============================================================
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT, -- 'report_submitted', 'approval_required', 'comment_added', etc.
    related_entity_type TEXT, -- 'report', 'comment', etc.
    related_entity_id INTEGER,
    is_read BOOLEAN DEFAULT 0,
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    read_at TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_notifications_user ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(is_read);
CREATE INDEX idx_notifications_type ON notifications(notification_type);

-- ============================================================
-- 14. REPORT TEMPLATES TABLE (Optional - For Standardized Reports)
-- ============================================================
CREATE TABLE IF NOT EXISTS report_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    template_structure TEXT NOT NULL, -- JSON schema for report fields
    department_id INTEGER, -- Department-specific template
    is_active BOOLEAN DEFAULT 1,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (department_id) REFERENCES departments(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(user_id) ON DELETE SET NULL
);

CREATE INDEX idx_report_templates_department ON report_templates(department_id);

-- ============================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================

-- View: User with their roles and departments
CREATE VIEW IF NOT EXISTS v_user_roles AS
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
LEFT JOIN departments d ON ur.department_id = d.id;

-- View: Reports with submitter and department info
CREATE VIEW IF NOT EXISTS v_reports_full AS
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
    d.level as department_level,
    (SELECT COUNT(*) FROM report_comments WHERE report_id = r.id) as comments_count,
    (SELECT COUNT(*) FROM report_approvals WHERE report_id = r.id) as approvals_count
FROM reports r
JOIN users u ON r.submitted_by = u.user_id
JOIN departments d ON r.department_id = d.id;

-- View: Department hierarchy with manager info
CREATE VIEW IF NOT EXISTS v_department_hierarchy AS
WITH RECURSIVE dept_tree AS (
    SELECT id, name, parent_department_id, level, manager_id, 0 as depth
    FROM departments
    WHERE parent_department_id IS NULL

    UNION ALL

    SELECT d.id, d.name, d.parent_department_id, d.level, d.manager_id, dt.depth + 1
    FROM departments d
    JOIN dept_tree dt ON d.parent_department_id = dt.id
)
SELECT
    dt.*,
    u.first_name || ' ' || COALESCE(u.last_name, '') as manager_name
FROM dept_tree dt
LEFT JOIN users u ON dt.manager_id = u.user_id;

-- ============================================================
-- TRIGGERS FOR AUTO-UPDATE timestamps
-- ============================================================

-- Users table
CREATE TRIGGER IF NOT EXISTS update_users_timestamp
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE user_id = NEW.user_id;
END;

-- Reports table
CREATE TRIGGER IF NOT EXISTS update_reports_timestamp
AFTER UPDATE ON reports
BEGIN
    UPDATE reports SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- Departments table
CREATE TRIGGER IF NOT EXISTS update_departments_timestamp
AFTER UPDATE ON departments
BEGIN
    UPDATE departments SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- ============================================================
-- END OF SCHEMA
-- ============================================================
