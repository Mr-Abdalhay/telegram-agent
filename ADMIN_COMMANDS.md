# 🔐 Hidden Administrator Commands

**⚠️ CONFIDENTIAL - FOR ADMINISTRATORS ONLY**

This document contains all hidden administrator commands. These commands are **NOT** shown in `/start` or `/help` messages and are only accessible to users with administrator role.

---

## 🎯 Command Overview

| Command | Purpose | Access |
|---------|---------|--------|
| `/createadmin` | Create new administrator | Admins only |
| `/removeadmin` | Remove admin role | Admins only (can't self-remove) |
| `/listadmins` | List all administrators | Admins only |
| `/promote` | Promote user to manager/upper_manager | Admins only |
| `/removeuser` | **Deactivate/Remove a user** | Admins only |
| `/activateuser` | **Reactivate a removed user** | Admins only |
| `/listusers` | **List all users with filters** | Admins only |

---

## 📋 Command Details

### 1. Create Administrator

**Command:** `/createadmin <user_id>`

**Description:** Assigns administrator role to a user.

**Requirements:**
- User must have sent `/start` to the bot first
- Only existing admins can use this command
- Non-admins who try this command get NO response (command is invisible)

**Usage:**
```
/createadmin 123456789
```

**Example Output:**
```
✅ Admin Created Successfully

👤 User: Ahmad (@ahmad_user)
🔑 User ID: 123456789
👔 Role: Administrator

Permissions:
• Full system access
• View all reports
• Manage users & departments
• Create cumulative reports
• Approve any report

User can verify with /my_role
```

**How to get User ID:**
1. Ask user to send `/start` to the bot
2. Check bot logs for their user_id
3. Or ask user to use @userinfobot in Telegram

---

### 2. Remove Administrator

**Command:** `/removeadmin <user_id>`

**Description:** Removes administrator role from a user.

**Requirements:**
- Only admins can use this
- Cannot remove your own admin role (requires another admin)
- User returns to their previous role (if any)

**Usage:**
```
/removeadmin 123456789
```

**Example Output:**
```
✅ Admin Role Removed

👤 User: Ahmad (@ahmad_user)
🔑 User ID: 123456789

User is no longer an administrator.
They can use /my_role to see their current permissions.
```

**Safety Features:**
- Prevents self-removal to avoid locking out all admins
- User retains their other roles (e.g., manager, employee)
- Graceful degradation - user can still use the bot

---

### 3. List All Administrators

**Command:** `/listadmins`

**Description:** Shows all users with administrator role.

**Requirements:**
- Only admins can use this
- Shows active admins only

**Usage:**
```
/listadmins
```

**Example Output:**
```
👑 System Administrators

👤 Ahmad Ali
   @ahmad_admin
   ID: `123456789`
   Since: 2025-01-26

👤 Sarah Mohammed
   @sarah_manager
   ID: `987654321`
   Since: 2025-01-25

Total: 2 administrator(s)
```

---

### 4. Promote User to Manager

**Command:** `/promote <user_id> <role> [department_id]`

**Description:** Promotes a user to manager or upper_manager role.

**Roles:**
- `manager` - Can manage one department
- `upper_manager` - Can manage department + sub-departments + create cumulative reports

**Requirements:**
- Only admins can use this
- User must be registered first (`/register`)
- Department ID is optional (uses user's current department if not specified)

**Usage:**
```
# Promote to manager in their current department
/promote 123456789 manager

# Promote to upper_manager in specific department
/promote 123456789 upper_manager 2

# Promote to manager in Sales department
/promote 123456789 manager 2
```

**Department IDs (default):**
- 1 = الإدارة العامة (General Management)
- 2 = المبيعات (Sales)
- 3 = التسويق (Marketing)
- 4 = الموارد البشرية (HR)
- 5 = تقنية المعلومات (IT)

**Example Output:**
```
✅ User Promoted

👤 User: Ahmad
🔑 User ID: 123456789
👔 New Role: مدير (manager)
🏢 Department: المبيعات

User can verify with /my_role
```

---

### 5. Remove User

**Command:** `/removeuser <user_id>`

**Description:** Deactivates a user account and removes all their roles.

**Requirements:**
- Only admins can use this
- Cannot remove yourself
- Cannot remove admins directly (must use `/removeadmin` first)
- User data is retained for audit purposes

**Usage:**
```
/removeuser 123456789
```

**Example Output:**
```
✅ User Removed Successfully

👤 User: Ahmad Ali
🔑 User ID: `123456789`
📧 Username: @ahmad_user
👔 Previous Roles: موظف, مدير

Actions taken:
• User account deactivated
• All roles removed
• User can no longer access the bot
• Data retained for audit purposes

💡 To reactivate: /activateuser 123456789
```

**What Happens:**
- User account set to `is_active = 0`
- All user roles deactivated
- User cannot use bot commands
- Reports and data remain in database
- Can be reactivated later

**Safety Features:**
- Blocks admin removal (requires `/removeadmin` first)
- Prevents self-removal
- Retains all audit data
- Reversible action

---

### 6. Reactivate User

**Command:** `/activateuser <user_id>`

**Description:** Reactivates a previously removed user account.

**Requirements:**
- Only admins can use this
- User must exist in database
- User must be currently inactive

**Usage:**
```
/activateuser 123456789
```

**Example Output:**
```
✅ User Reactivated Successfully

👤 User: Ahmad Ali
🔑 User ID: `123456789`

Actions taken:
• User account reactivated
• User can now use /start to re-register

⚠️ Note: User's previous roles were NOT restored.
Use /promote to assign new roles if needed.
```

**Important Notes:**
- Reactivates account ONLY
- Does NOT restore previous roles
- User must use `/register` again
- Then use `/promote` to assign roles

**Workflow for Reactivation:**
```
1. Admin: /activateuser 123456789
2. User: /start (in bot)
3. User: /register (select department)
4. Admin: /promote 123456789 manager 2
5. ✅ User fully restored
```

---

### 7. List All Users

**Command:** `/listusers [active|inactive|all]`

**Description:** Lists all users with optional status filter.

**Requirements:**
- Only admins can use this
- Shows up to 20 users per request

**Usage:**
```
# Show active users (default)
/listusers

# Show all users
/listusers all

# Show deactivated users only
/listusers inactive
```

**Example Output:**
```
✅ Active Users (15)

✅ **1. Ahmad Ali**
   @ahmad_admin | ID: `123456789`
   Role: مسؤول النظام
   Joined: 2025-01-25

✅ **2. Sarah Mohammed**
   @sarah_manager | ID: `987654321`
   Role: مدير
   Joined: 2025-01-26

✅ **3. Khalid Ahmed**
   @khalid_user | ID: `111222333`
   Role: موظف
   Joined: 2025-01-26

... and 12 more users

Total: 15 active user(s)
```

**Filters:**
- `active` - Shows only active users (default)
- `inactive` - Shows only deactivated users
- `all` - Shows all users with status indicators

**Use Cases:**
1. **User Management:** See all registered users
2. **Audit:** Check who's active vs inactive
3. **Cleanup:** Identify accounts to remove
4. **Monitoring:** Track user registrations

---

## 🔒 Security Features

### Command Invisibility
- Non-admin users get **NO response** when using admin commands
- Commands don't appear in `/help` or `/start`
- Bot silently ignores admin commands from non-admins
- No error messages = no hint that command exists

### Permission Checks
Every admin command checks:
1. Is user an admin? (`access_control.is_admin(user_id)`)
2. If not → Silent return (no response)
3. If yes → Process command

### Example Code:
```python
if not access_control.is_admin(user_id):
    # Don't reveal this command exists - just ignore
    return
```

---

## 🚀 Getting Started as First Admin

### Scenario: No admins exist yet

**Option 1: Direct Database Assignment (Recommended)**

```bash
# Run Python in project directory
python

# Execute:
from bot.database_enhanced import DatabaseEnhanced
from config import config

db = DatabaseEnhanced(config.DB_PATH)

# YOUR_USER_ID = get from /start or @userinfobot
db.assign_role(
    user_id=YOUR_USER_ID,
    role_name='admin',
    department_id=None
)

print("✅ First admin created!")
```

**Option 2: Direct SQL**

```bash
sqlite3 data/conversations.db

INSERT INTO user_roles (user_id, role_id, department_id, is_active)
VALUES (
    YOUR_USER_ID,
    (SELECT id FROM roles WHERE name = 'admin'),
    NULL,
    1
);

.quit
```

**Option 3: Migration Script**

After running migration, manually edit:
```sql
UPDATE user_roles
SET role_id = (SELECT id FROM roles WHERE name = 'admin')
WHERE user_id = YOUR_USER_ID;
```

---

## 📊 Admin Workflow Examples

### Example 1: Add New Admin

```
Step 1: User sends /start to bot
Step 2: You get their user_id from logs (e.g., 123456789)
Step 3: You send: /createadmin 123456789
Step 4: ✅ Done! They're now admin
```

### Example 2: Promote User to Manager

```
Step 1: User registers via /register
Step 2: You send: /promote 123456789 manager
Step 3: ✅ User is now manager of their department
```

### Example 3: Create Upper Manager for Sales

```
Step 1: User exists in system
Step 2: You send: /promote 123456789 upper_manager 2
Step 3: ✅ User can now create cumulative reports for Sales dept
```

### Example 4: Remove Problematic Admin

```
Step 1: Get admin list: /listadmins
Step 2: Find user_id of person to remove
Step 3: Send: /removeadmin 987654321
Step 4: ✅ User's admin access revoked
```

### Example 5: Remove Problematic User

```
Step 1: Check user list: /listusers
Step 2: Identify problematic user (ID: 555666777)
Step 3: Send: /removeuser 555666777
Step 4: ✅ User deactivated and cannot access bot
```

### Example 6: Reactivate User After Investigation

```
Scenario: User was removed, issue resolved, need to restore access

Step 1: Send: /activateuser 555666777
Step 2: User sends: /start (to bot)
Step 3: User sends: /register (selects department)
Step 4: You send: /promote 555666777 employee 2
Step 5: ✅ User fully restored with employee access
```

### Example 7: Audit All Users

```
Step 1: Check active users: /listusers
Step 2: Check inactive users: /listusers inactive
Step 3: Check ALL users: /listusers all
Step 4: Identify any anomalies or cleanup needed
```

### Example 8: Remove Admin Completely

```
Scenario: Need to fully remove an administrator

Step 1: First remove admin role: /removeadmin 789012345
Step 2: Then remove user: /removeuser 789012345
Step 3: ✅ User completely deactivated
```

---

## 🔍 Finding User IDs

### Method 1: Bot Logs
```bash
# Start bot and watch logs
python main_enhanced.py

# User sends /start
# Logs show: User 123456789 (@username) started the bot
```

### Method 2: @userinfobot (Telegram)
```
1. User chats with @userinfobot in Telegram
2. Bot replies with user's ID
3. Use that ID in admin commands
```

### Method 3: Database Query
```sql
sqlite3 data/conversations.db

SELECT user_id, username, first_name FROM users;
```

---

## ⚠️ Important Notes

### Do NOT:
- ❌ Share these commands publicly
- ❌ Mention admin commands in public channels
- ❌ Remove all admins (you'll lock yourself out)
- ❌ Give admin access to untrusted users

### Always:
- ✅ Keep this document secure
- ✅ Verify user identity before promoting
- ✅ Maintain at least 2 admins (backup)
- ✅ Document admin changes
- ✅ Review admin list regularly: `/listadmins`

### Best Practices:
1. **Least Privilege:** Start users as employees
2. **Gradual Promotion:** employee → manager → upper_manager → admin
3. **Backup Admin:** Always have 2+ admins
4. **Regular Audits:** Run `/listadmins` monthly
5. **Secure Access:** Only store this document in secure location

---

## 🆘 Troubleshooting

### Command doesn't work
**Problem:** Sent `/createadmin 123` but nothing happened

**Solutions:**
1. Check if YOU are admin: `/my_role`
2. Check user exists: User must send `/start` first
3. Check bot logs for errors
4. Verify database migration ran successfully

### User ID not found
**Problem:** "User not found" error

**Solutions:**
1. User must send `/start` to bot first
2. Check user_id is correct (numbers only)
3. Query database: `SELECT * FROM users WHERE user_id = 123456789`

### Can't remove admin
**Problem:** Trying to remove own admin role

**Solution:**
- You can't remove yourself
- Ask another admin to remove you
- Or use direct database access

---

## 🔐 Admin Permissions Summary

Admins can:
- ✅ View ALL reports (across all departments)
- ✅ Approve ANY report
- ✅ Create/remove other admins
- ✅ Promote users to manager/upper_manager
- ✅ Create cumulative reports
- ✅ Manage departments
- ✅ Access all bot features
- ✅ Use hidden commands

---

## 📞 Emergency Procedures

### Lost Admin Access

If all admins are removed:

```bash
# Direct database restoration
sqlite3 data/conversations.db

INSERT INTO user_roles (user_id, role_id, is_active)
VALUES (
    YOUR_USER_ID,
    (SELECT id FROM roles WHERE name = 'admin'),
    1
);

.quit
```

### Database Corruption

```bash
# Restore from backup
cp data/conversations.db.backup_YYYYMMDD data/conversations.db

# Or check migration backups
ls data/*.backup_*
```

---

## 📅 Changelog

| Date | Change |
|------|--------|
| 2025-01-26 | Initial admin commands created |
| 2025-01-26 | Added hidden command system |
| 2025-01-26 | Documented all admin features |
| 2025-01-26 | **Added user management commands** (`/removeuser`, `/activateuser`, `/listusers`) |

---

**Version:** 1.1.0
**Last Updated:** 2025-01-26
**Classification:** CONFIDENTIAL
**Access:** Administrators Only

---

**Remember:** With great power comes great responsibility. Use admin commands wisely! 👑
