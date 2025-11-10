# 👔 Manager Commands Guide

**FOR MANAGERS, UPPER MANAGERS, AND ADMINISTRATORS**

This document contains commands available to users with manager role and above. These commands allow you to manage departments and perform administrative tasks within your department.

---

## 🎯 Command Overview

| Command | Purpose | Access | Visibility |
|---------|---------|--------|-----------|
| `/create_department` | Create new department or sub-department | Managers+ | Hidden (not in /help) |
| `/create_report` | Create a new report | All registered users | Visible in /help |
| `/approve_report` | Approve or reject reports | Managers+ | Visible in /help |
| `/create_cumulative` | Create cumulative report from sub-departments | Upper Managers+ | Visible in /help |

**Note:** The `/create_department` command is intentionally hidden from the `/help` menu to keep it available only to those who know about it (managers and above).

---

## 📋 Department Management

### Create Department

**Command:** `/create_department`

**Description:** Creates a new department or sub-department. This is a wizard-style command that guides you through the process step by step.

**Access:** Managers, Upper Managers, and Administrators only

**Features:**
- Create root departments (no parent)
- Create sub-departments under existing departments
- Support for Arabic and English names
- Automatic hierarchy level calculation
- Audit logging of department creation

**Usage Flow:**

1. **Send the command:**
   ```
   /create_department
   ```

2. **Enter Arabic name:**
   ```
   Bot: 📋 إنشاء قسم جديد
        👉 أدخل اسم القسم بالعربية:

   You: قسم المبيعات
   ```

3. **Enter English name:**
   ```
   Bot: ✅ الاسم بالعربية: قسم المبيعات
        👉 الآن أدخل اسم القسم بالإنجليزية:

   You: Sales Department
   ```

4. **Choose parent department (optional):**
   ```
   Bot: Shows buttons:
        [📁 قسم رئيسي (بدون قسم أب)]
        [📂 الإدارة العامة]
        [📂 قسم الهندسة]
        ...

   You: Click on desired parent or "قسم رئيسي" for root department
   ```

5. **Confirm creation:**
   ```
   Bot: 📋 ملخص القسم الجديد
        • الاسم بالعربية: قسم المبيعات
        • الاسم بالإنجليزية: Sales Department
        • القسم الأب: لا يوجد (قسم رئيسي)

        هل تريد إنشاء هذا القسم؟

        [✅ نعم، أنشئ القسم] [❌ إلغاء]

   You: Click "نعم، أنشئ القسم"
   ```

6. **Success:**
   ```
   Bot: ✅ تم إنشاء القسم بنجاح!

        📂 قسم المبيعات / Sales Department
        🆔 رقم القسم: 5

        يمكن للمستخدمين الآن التسجيل في هذا القسم.
   ```

**Example Scenarios:**

#### Scenario 1: Create Root Department
```
Command: /create_department
Arabic Name: قسم الموارد البشرية
English Name: HR Department
Parent: 📁 قسم رئيسي (بدون قسم أب)
Result: Root department at level 0
```

#### Scenario 2: Create Sub-Department
```
Command: /create_department
Arabic Name: فريق التوظيف
English Name: Recruitment Team
Parent: 📂 قسم الموارد البشرية
Result: Sub-department at level 1 under HR
```

#### Scenario 3: Create Nested Sub-Department
```
Command: /create_department
Arabic Name: وحدة التوظيف الدولي
English Name: International Recruitment Unit
Parent: 📂 فريق التوظيف
Result: Sub-department at level 2 under Recruitment Team
```

**Canceling Department Creation:**

At any step, you can type `/cancel` to abort the process:
```
/cancel
Bot: ❌ تم إلغاء إنشاء القسم.
```

**Permissions Required:**
- Your role must be `manager`, `upper_manager`, or `admin`
- If you're not registered, you'll be asked to use `/register` first
- Employees cannot use this command

**Error Handling:**

1. **Not a manager:**
   ```
   ❌ هذا الأمر متاح للمدراء فقط.
   ```

2. **Not registered:**
   ```
   ❌ يجب أن تكون مسجلاً في النظام أولاً.
   استخدم /register للتسجيل.
   ```

3. **Duplicate department name:**
   ```
   ❌ فشل إنشاء القسم. قد يكون الاسم مستخدماً بالفعل.
   ```

4. **Invalid parent department:**
   ```
   ❌ القسم الأب غير موجود.
   ```

**Best Practices:**

1. **Naming Convention:**
   - Use clear, descriptive names
   - Arabic name for primary users
   - English name for technical reference
   - Avoid special characters

2. **Department Hierarchy:**
   - Start with root departments (General Management, Sales, Engineering, etc.)
   - Create sub-departments as needed for teams
   - Don't create too many levels (3 levels max recommended)

3. **After Creation:**
   - Inform team members to use `/register` and select the new department
   - Assign a manager to the department if needed (using admin commands)
   - Create initial reports to test the workflow

**Technical Details:**

- Department IDs are auto-incremented integers
- Names must be unique (case-sensitive)
- Level is automatically calculated based on parent
- Creation is logged in the audit_log table
- All departments are active by default (is_active = 1)

---

## 🔄 Department Hierarchy Examples

### Example 1: Simple Organization
```
📁 الإدارة العامة (General Management) [Level 0]

📁 قسم المبيعات (Sales Department) [Level 0]
   └── 📂 فريق المبيعات أ (Sales Team A) [Level 1]
   └── 📂 فريق المبيعات ب (Sales Team B) [Level 1]

📁 قسم الهندسة (Engineering Department) [Level 0]
   └── 📂 فريق Backend (Backend Team) [Level 1]
   └── 📂 فريق Frontend (Frontend Team) [Level 1]
```

### Example 2: Complex Organization
```
📁 الشركة (Company) [Level 0]
   └── 📂 قسم التكنولوجيا (Technology Dept) [Level 1]
       └── 📂 فريق التطوير (Development Team) [Level 2]
           └── 📂 وحدة Backend (Backend Unit) [Level 3]
           └── 📂 وحدة Mobile (Mobile Unit) [Level 3]
       └── 📂 فريق الأمن السيبراني (Security Team) [Level 2]
```

**Access Rights in Hierarchy:**
- Employee in "Backend Unit": Can view only their own reports
- Manager of "Development Team": Can view reports from Backend Unit and Mobile Unit
- Upper Manager of "Technology Dept": Can view ALL reports from Development, Security, and their sub-units
- Administrator: Can view everything

---

## 📊 Integration with Reporting System

### After Creating a Department:

1. **User Registration:**
   - Users can now select this department when using `/register`
   - They will be assigned "employee" role by default

2. **Report Creation:**
   - Users in the department can create reports using `/create_report`
   - Reports are tagged with their department

3. **Manager Approval:**
   - Managers can approve reports from their department
   - Upper managers can approve from sub-departments too

4. **Cumulative Reports:**
   - Upper managers can create cumulative reports that aggregate data from the new department and its children

---

## 🔒 Security & Audit

All department creation actions are logged with:
- User ID who created the department
- Timestamp of creation
- Department details (name, parent, level)
- Action type: "create_department"

Administrators can view audit logs through the database or future audit commands.

---

## 💡 Tips & Tricks

1. **First-Time Setup:**
   - Create all root departments first
   - Then add sub-departments in a logical order
   - Test registration after each department creation

2. **Department Naming:**
   - Keep names short and clear
   - Use consistent naming patterns
   - Arabic names should be natural and professional

3. **Organizational Planning:**
   - Plan your hierarchy before creating departments
   - Consider how reports will flow up the hierarchy
   - Think about who should be upper managers

4. **User Management:**
   - After creating a department, announce it to the team
   - Guide users to use `/register` to join
   - Monitor registrations to ensure users select the correct department

---

## 🆘 Troubleshooting

### Problem: Command doesn't respond
**Cause:** You don't have manager role
**Solution:** Contact an administrator to promote you with `/promote` command

### Problem: "اسم مستخدم بالفعل" (Name already exists)
**Cause:** Department name is duplicate
**Solution:** Choose a different name or check existing departments

### Problem: Can't see newly created department in /register
**Cause:** Database not updated or department inactive
**Solution:** Restart the bot or check database

### Problem: Parent department doesn't appear in list
**Cause:** Parent department might be inactive
**Solution:** Check with administrator

---

## 📚 Related Commands

- `/register` - Join a department (all users)
- `/my_role` - Check your current role and department
- `/create_report` - Create a report for your department
- `/department_reports` - View all reports from your department
- `/approve_report` - Approve pending reports (managers+)
- `/create_cumulative` - Create aggregated report (upper managers+)

For administrator commands (user management, role assignment), see [ADMIN_COMMANDS.md](ADMIN_COMMANDS.md).

