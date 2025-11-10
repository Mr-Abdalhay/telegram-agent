"""
Access Control and Permissions Module
Handles role-based access control for the reporting system
"""

from typing import Optional, List, Dict
from bot.database_enhanced import DatabaseEnhanced
from config import config


class AccessControl:
    """Manages access control and permissions"""

    def __init__(self, db: DatabaseEnhanced):
        self.db = db

    # ============================================================
    # PERMISSION CHECKS
    # ============================================================

    def can_create_report(self, user_id: int) -> bool:
        """Check if user can create reports"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        return self.db.has_permission(user_id, 'can_create_report')

    def can_view_report(self, user_id: int, report_id: int) -> bool:
        """Check if user can view a specific report"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        report = self.db.get_report(report_id)
        if not report:
            return False

        # Report owner can always view
        if report['submitted_by'] == user_id:
            return True

        # Check visibility
        if report['visibility'] == 'public':
            return True

        # Check if user can access the department
        return self.db.can_access_department(user_id, report['department_id'])

    def can_approve_report(self, user_id: int, report_id: int) -> bool:
        """Check if user can approve a report"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        if not self.db.has_permission(user_id, 'can_approve'):
            return False

        report = self.db.get_report(report_id)
        if not report:
            return False

        # Can't approve own report
        if report['submitted_by'] == user_id:
            return False

        # Must be able to access the department
        return self.db.can_access_department(user_id, report['department_id'])

    def can_create_cumulative_report(self, user_id: int) -> bool:
        """Check if user can create cumulative reports"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        return self.db.has_permission(user_id, 'can_create_cumulative')

    def can_manage_users(self, user_id: int) -> bool:
        """Check if user can manage other users"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        return self.db.has_permission(user_id, 'can_manage_users')

    def can_manage_departments(self, user_id: int) -> bool:
        """Check if user can manage departments"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        return self.db.has_permission(user_id, 'can_manage_departments')

    # ============================================================
    # ROLE CHECKS
    # ============================================================

    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        role = self.db.get_user_primary_role(user_id)
        return role and role['role_name'] == 'admin'

    def is_upper_manager(self, user_id: int) -> bool:
        """Check if user is upper manager or higher"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        role = self.db.get_user_primary_role(user_id)
        return role and role['role_name'] in ['upper_manager', 'admin']

    def is_manager(self, user_id: int) -> bool:
        """Check if user is manager or higher"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False

        role = self.db.get_user_primary_role(user_id)
        return role and role['role_name'] in ['manager', 'upper_manager', 'admin']

    # ============================================================
    # DEPARTMENT ACCESS
    # ============================================================

    def get_accessible_departments(self, user_id: int) -> List[int]:
        """Get all departments user can access"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return []

        user_role = self.db.get_user_primary_role(user_id)
        if not user_role:
            return []

        # Admin can access all
        if user_role['role_name'] == 'admin':
            departments = self.db.get_all_departments()
            return [d['id'] for d in departments]

        user_dept = user_role.get('department_id')
        if not user_dept:
            return []

        # Upper manager can access department hierarchy
        if user_role['permissions'].get('can_view_subdepartments'):
            return self.db.get_department_hierarchy(user_dept)

        # Manager can access own department
        if user_role['permissions'].get('can_view_department'):
            return [user_dept]

        # Employee can only access own reports (no department access)
        return []

    def get_accessible_reports(self, user_id: int, limit: int = 50,
                               status: str = None) -> List[Dict]:
        """Get all reports user can access"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return []

        user_role = self.db.get_user_primary_role(user_id)
        if not user_role:
            return []

        # Admin can view all
        if user_role['permissions'].get('can_view_all'):
            # Get all reports (simplified - would need pagination)
            return []  # TODO: Implement admin view all

        # Get accessible departments
        accessible_depts = self.get_accessible_departments(user_id)

        if not accessible_depts:
            # Employee - only own reports
            return self.db.get_user_reports(user_id, limit=limit, status=status)

        # Get reports from accessible departments
        all_reports = []
        for dept_id in accessible_depts:
            dept_reports = self.db.get_department_reports(
                dept_id, status=status, limit=limit
            )
            all_reports.extend(dept_reports)

        # Also include own reports
        own_reports = self.db.get_user_reports(user_id, limit=limit, status=status)

        # Merge and deduplicate
        seen_ids = set()
        unique_reports = []
        for report in all_reports + own_reports:
            if report['id'] not in seen_ids:
                seen_ids.add(report['id'])
                unique_reports.append(report)

        # Sort by date
        unique_reports.sort(key=lambda x: x.get('submitted_at', ''), reverse=True)

        return unique_reports[:limit]

    # ============================================================
    # VALIDATION
    # ============================================================

    def validate_report_creation(self, user_id: int, department_id: int) -> tuple[bool, str]:
        """Validate if user can create report in department"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False, "❌ حسابك غير نشط. يرجى التواصل مع المسؤول"

        if not self.can_create_report(user_id):
            return False, "❌ ليس لديك صلاحية إنشاء التقارير"

        user_dept = self.db.get_user_department(user_id)
        user_role = self.db.get_user_primary_role(user_id)

        # Admin can create in any department
        if user_role and user_role['role_name'] == 'admin':
            return True, ""

        # User must create reports in their own department
        if department_id != user_dept:
            return False, "❌ يمكنك فقط إنشاء تقارير في قسمك"

        return True, ""

    def validate_cumulative_report_creation(self, user_id: int,
                                            source_report_ids: List[int]) -> tuple[bool, str]:
        """Validate if user can create cumulative report from given sources"""
        # First check if user is active
        user = self.db.get_user(user_id)
        if not user or not user.get('is_active', 1):
            return False, "❌ حسابك غير نشط. يرجى التواصل مع المسؤول"

        if not self.can_create_cumulative_report(user_id):
            return False, "❌ ليس لديك صلاحية إنشاء التقارير التجميعية (مدير أعلى فقط)"

        # Check if all source reports are accessible
        accessible_depts = self.get_accessible_departments(user_id)

        for report_id in source_report_ids:
            report = self.db.get_report(report_id)
            if not report:
                return False, f"❌ التقرير {report_id} غير موجود"

            if report['department_id'] not in accessible_depts:
                return False, f"❌ ليس لديك صلاحية الوصول إلى التقرير {report_id}"

        return True, ""

    # ============================================================
    # ROLE ASSIGNMENT VALIDATION
    # ============================================================

    def can_assign_role(self, assigner_id: int, target_user_id: int,
                        role_name: str, department_id: int) -> tuple[bool, str]:
        """Check if assigner can assign role to target user"""
        # First check if assigner is active
        assigner = self.db.get_user(assigner_id)
        if not assigner or not assigner.get('is_active', 1):
            return False, "❌ حسابك غير نشط. يرجى التواصل مع المسؤول"

        if not self.can_manage_users(assigner_id):
            return False, "❌ ليس لديك صلاحية إدارة المستخدمين"

        assigner_role = self.db.get_user_primary_role(assigner_id)
        target_role = self.db.get_role_by_name(role_name)

        if not target_role:
            return False, f"❌ الدور {role_name} غير موجود"

        # Can't assign role higher than own role
        if target_role['level'] >= assigner_role['level']:
            return False, "❌ لا يمكنك منح دور أعلى من دورك"

        # Admin can assign any role in any department
        if assigner_role['role_name'] == 'admin':
            return True, ""

        # Non-admin can only assign in their department
        assigner_dept = assigner_role.get('department_id')
        if department_id != assigner_dept:
            return False, "❌ يمكنك فقط منح الأدوار في قسمك"

        return True, ""

    # ============================================================
    # HELPER METHODS
    # ============================================================

    def get_role_display_name(self, role_name: str) -> str:
        """Get Arabic display name for role"""
        role_names = {
            'employee': 'موظف',
            'manager': 'مدير',
            'upper_manager': 'مدير أعلى',
            'admin': 'مسؤول النظام'
        }
        return role_names.get(role_name, role_name)

    def get_permission_summary(self, user_id: int) -> str:
        """Get user's permission summary as text"""
        role = self.db.get_user_primary_role(user_id)
        if not role:
            return "لا توجد أدوار مخصصة"

        permissions = role.get('permissions', {})
        dept_name = role.get('department_name', 'غير محدد')

        summary = f"🔐 **صلاحياتك:**\n\n"
        summary += f"• الدور: {role['role_name_ar']}\n"
        summary += f"• القسم: {dept_name}\n\n"
        summary += "**الأذونات:**\n"

        perm_labels = {
            'can_create_report': '✅ إنشاء التقارير',
            'can_view_own': '✅ عرض تقاريرك',
            'can_view_department': '✅ عرض تقارير القسم',
            'can_view_subdepartments': '✅ عرض تقارير الأقسام الفرعية',
            'can_approve': '✅ الموافقة على التقارير',
            'can_create_cumulative': '✅ إنشاء التقارير التجميعية',
            'can_manage_users': '✅ إدارة المستخدمين',
            'can_manage_departments': '✅ إدارة الأقسام',
            'can_view_all': '✅ عرض جميع التقارير'
        }

        for perm, label in perm_labels.items():
            if permissions.get(perm):
                summary += f"{label}\n"

        return summary


# Create singleton instance
def get_access_control(db: DatabaseEnhanced) -> AccessControl:
    """Get AccessControl instance"""
    return AccessControl(db)
