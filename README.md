# Quick Start Guide - Reporting System

## 🚀 Getting Started (5 Minutes)

### 1. Install and Migrate

```bash
# Install dependencies
pip install -r requirements.txt

# Migrate database (creates backup automatically)
python scripts/migrate_database.py

# Start enhanced bot
python main_enhanced.py
```

### 2. First Time Setup

Open Telegram and chat with your bot:

```
You: /start
Bot: [Welcome message]

You: /register
Bot: [Select your department]
[Click on your department]

You: /my_role
Bot: Shows your role (موظف - Employee by default)
```

### 3. Create Your First Report

```
You: /create_report
Bot: أدخل عنوان التقرير:

You: تقرير مبيعات يوم 26 يناير
Bot: أدخل محتوى التقرير:

You: المبيعات اليوم: 50,000 ريال
     عدد العملاء: 15 عميل
     أفضل منتج: المنتج A
Bot: [Shows type selection]

[Select: يومي]
Bot: [Shows confirmation]

[Click: إرسال التقرير]
Bot: ✅ تم إرسال التقرير بنجاح! #1
```

---

## 👔 For Managers

### Assign Manager Role

```bash
# Open Python shell
python

# Run these commands:
from bot.database_enhanced import DatabaseEnhanced
from config import config

db = DatabaseEnhanced(config.DB_PATH)

# Assign manager role to user
# Replace USER_ID with actual Telegram user ID
# Replace DEPT_ID with department ID (1-5 for defaults)

db.assign_role(
    user_id=123456789,  # Your Telegram user ID
    role_name='manager',
    department_id=2  # 1=General, 2=Sales, 3=Marketing, etc.
)

print("✅ Manager role assigned!")
```

### Manager Commands

```
/department_reports - View all reports from your department
/approve_report 1 - Approve report #1
/view_report 1 - View detailed report
```

---

## 🎯 For Upper Managers

### Assign Upper Manager Role

```python
from bot.database_enhanced import DatabaseEnhanced
from config import config

db = DatabaseEnhanced(config.DB_PATH)

db.assign_role(
    user_id=YOUR_USER_ID,
    role_name='upper_manager',
    department_id=YOUR_DEPT_ID
)
```

### Create Cumulative Report

```
You: /create_cumulative
Bot: [Shows period selection]

[Select: شهري (Monthly)]
Bot: 📊 التقرير التجميعي
     ✅ تم العثور على 25 تقرير معتمد
     📁 من 5 أقسام
     🔄 جاري إنشاء التقرير التجميعي...

Bot: ✅ تم إنشاء التقرير التجميعي #10
     [Shows AI-generated summary]
```

---

## 📊 Useful Commands Reference

### Everyone
- `/start` - Start bot
- `/help` - Get help
- `/register` - Register in system
- `/my_role` - View your role
- `/create_report` - Create new report
- `/my_reports` - View your reports
- `/view_report <id>` - View specific report

### Managers
- `/department_reports` - View department reports
- `/approve_report <id>` - Approve report
- `/dept_reports` - Alias for department_reports

### Upper Managers
- `/create_cumulative` - Create cumulative report
- `/cumulative` - Alias for create_cumulative

### Admins
- `/search_reports` - Search all reports
- All above commands

---

## 🗂️ Department IDs (Default)

| ID | Arabic Name | English Name |
|----|-------------|--------------|
| 1 | الإدارة العامة | General Management |
| 2 | المبيعات | Sales |
| 3 | التسويق | Marketing |
| 4 | الموارد البشرية | Human Resources |
| 5 | تقنية المعلومات | IT |

---

## 🔐 Role Capabilities

### Employee (موظف)
✅ Create reports
✅ View own reports
❌ View department reports
❌ Approve reports
❌ Create cumulative reports

### Manager (مدير)
✅ All Employee capabilities
✅ View department reports
✅ Approve department reports
❌ View sub-departments
❌ Create cumulative reports

### Upper Manager (مدير أعلى)
✅ All Manager capabilities
✅ View sub-department reports
✅ **Create cumulative reports**
✅ Approve hierarchical reports

### Admin (مسؤول النظام)
✅ Full system access
✅ Manage users
✅ Manage departments

---

## 🛠️ Common Tasks

### Check User ID

In Telegram, send any message to the bot and check logs:
```bash
# View logs
tail -f your_log_file.log

# Or use this bot command
/start
# Your user ID appears in the logs
```

### Add Department

```python
from bot.database_enhanced import DatabaseEnhanced
db = DatabaseEnhanced('./data/conversations.db')

# Add top-level department
dept_id = db.create_department(
    name="المشتريات",
    name_en="Procurement",
    description="قسم المشتريات",
    parent_id=None
)

print(f"Department created with ID: {dept_id}")
```

### Add Sub-Department

```python
# First, find parent department ID
departments = db.get_all_departments()
for dept in departments:
    print(f"{dept['id']}: {dept['name']}")

# Add sub-department
sub_dept_id = db.create_department(
    name="المبيعات - الرياض",
    name_en="Sales - Riyadh",
    description="فرع الرياض",
    parent_id=2  # Parent is "المبيعات"
)
```

### View Database

```bash
# Open SQLite database
sqlite3 data/conversations.db

# List all tables
.tables

# View all departments
SELECT * FROM departments;

# View all roles
SELECT * FROM roles;

# View user roles
SELECT * FROM v_user_roles;

# Exit
.quit
```

---

## 🐛 Quick Troubleshooting

### "Old database schema detected"
```bash
python scripts/migrate_database.py
```

### "Permission denied"
Check your role:
```
/my_role
```

### No departments available
Run migration or add departments manually (see above)

### Bot not responding
1. Check bot token in `.env`
2. Check bot is running: `ps aux | grep python`
3. Check logs for errors

---

## 📞 Need Help?

1. Check `/help` in the bot
2. Read full documentation: `SETUP_REPORTING_SYSTEM.md`
3. View database schema: `database_schema.sql`
4. Check existing handlers: `bot/report_handlers.py`

---

**Quick Tip:** Upper Managers can create weekly, monthly, or quarterly cumulative reports that automatically aggregate all approved reports from their department and all sub-departments using AI-powered summarization!

---

**Version:** 2.0.0

