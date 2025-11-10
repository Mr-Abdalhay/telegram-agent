# Web Admin Panel Documentation

## Overview

The Web Admin Panel is a browser-based interface for managing your Telegram bot. It provides an easy-to-use dashboard for admins and managers to control users, departments, and reports without using Telegram commands.

## Features

### For All Managers+
- View dashboard with statistics
- Browse users and departments
- View reports based on access level

### For Admins
- Create new administrators
- Promote users to managers/upper managers
- Remove/deactivate users
- Create departments
- View complete audit log
- Access all reports system-wide

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install Flask 3.0.0 and all other dependencies.

### 2. Configure Environment

Add these lines to your `.env` file:

```env
# Web Admin Panel Configuration
WEB_SECRET_KEY=your-secret-key-here-change-this
WEB_PORT=5000
WEB_DEBUG=False
```

**Important:** Change `WEB_SECRET_KEY` to a random string in production!

Generate a secret key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start the Web Server

```bash
python web/app.py
```

Or run both bot and web server in separate terminals:

**Terminal 1 - Telegram Bot:**
```bash
python main_enhanced.py
```

**Terminal 2 - Web Admin Panel:**
```bash
python web/app.py
```

### 4. Access the Panel

Open your browser and go to:
```
http://localhost:5000
```

## Login

### Authentication

The web panel uses a simple authentication system:

1. **User ID:** Your Telegram user ID (numeric)
2. **Password:** For now, use your user_id or "admin"

### Getting Your User ID

Option 1: From Telegram
- Send `/start` to your bot
- Check the bot console logs for your user ID

Option 2: Use @userinfobot
- Open [@userinfobot](https://t.me/userinfobot) in Telegram
- Send any message
- It will reply with your user ID

### Access Levels

| Role | Web Access | Capabilities |
|------|-----------|--------------|
| Employee | ❌ No | Must use Telegram bot only |
| Manager | ✅ Yes | View users, manage departments |
| Upper Manager | ✅ Yes | Same as manager + hierarchical access |
| Administrator | ✅ Yes | Full access to everything |

**Note:** Only Manager role and above can access the web panel.

## Dashboard

### Statistics Cards

The dashboard shows 4 key metrics:

1. **Total Users** - All registered users
2. **Departments** - Total departments
3. **Total Reports** - All reports created
4. **Pending** - Reports awaiting approval

### Quick Actions

Depending on your role, you'll see buttons for:

**Admins:**
- Create Admin
- Promote User
- Create Department
- View Reports

**Managers:**
- Create Department
- View Reports

### Recent Activity

Shows the last 10 audit log entries with:
- User who performed the action
- Action type
- Details
- Timestamp

## User Management

### Viewing Users

Navigate to **Users** from the sidebar to see:

- User profile (name, username)
- User ID (for admin commands)
- Current role and department
- Active/Inactive status
- Action buttons

### Creating Admin (Admins Only)

1. Click **Dashboard** → **Create Admin** button
2. Enter the target user's User ID
3. Click **Create Admin**

The user will immediately get admin privileges.

**Requirements:**
- User must have used `/start` in bot first
- User must be registered with `/register`
- Only existing admins can create new admins

### Promoting Users (Admins Only)

1. Click **Dashboard** → **Promote User** button
2. Enter user ID
3. Select role: Manager or Upper Manager
4. Click **Promote**

### Removing Users (Admins Only)

From the Users list:

1. Click on a user
2. Click **Remove** button
3. Confirm removal

**Notes:**
- Users are deactivated, not deleted (soft delete)
- You cannot remove yourself
- You cannot remove other admins (remove admin role first)
- User data is preserved for audit purposes

## Department Management

### Viewing Departments

Navigate to **Departments** to see:

- Department ID
- Arabic and English names
- Hierarchy level
- Parent department
- Number of users
- Number of reports
- Active status

### Creating Departments

1. Go to **Departments** → **Create Department**
2. Fill in:
   - **Arabic Name:** e.g., قسم المبيعات
   - **English Name:** e.g., Sales Department
   - **Parent Department:** Select parent or leave as root
   - **Description:** Optional description
3. Click **Create**

### Department Hierarchy

The system supports unlimited nesting:

```
Root Department (Level 0)
└── Sub-Department (Level 1)
    └── Team (Level 2)
        └── Unit (Level 3)
```

**Best Practice:** Keep hierarchy to 3 levels max for simplicity.

## Reports

### Viewing Reports

Navigate to **Reports** to see reports based on your role:

- **Employees:** Their own reports only
- **Managers:** Department reports
- **Upper Managers:** Department + sub-department reports
- **Admins:** All reports system-wide

### Report Information

Each report shows:
- Report ID
- Title and content
- Creator
- Department
- Status (Pending, Approved, Rejected)
- Creation date

## API Endpoints

The web panel exposes these API endpoints:

### GET /api/stats
Returns dashboard statistics in JSON format.

```json
{
  "total_users": 25,
  "active_users": 23,
  "total_departments": 8,
  "total_reports": 156,
  "pending_reports": 12,
  "approved_reports": 120
}
```

### POST /users/create-admin
Create new administrator.

**Parameters:**
- `user_id` (required): Target user ID

**Response:**
```json
{
  "success": true,
  "message": "User @john is now an admin"
}
```

### POST /users/promote
Promote user to manager/upper_manager.

**Parameters:**
- `user_id` (required): Target user ID
- `role` (required): "manager" or "upper_manager"

### POST /users/remove
Deactivate user account.

**Parameters:**
- `user_id` (required): Target user ID

### POST /departments/create
Create new department.

**Parameters:**
- `name_ar` (required): Arabic name
- `name_en` (required): English name
- `parent_id` (optional): Parent department ID
- `description` (optional): Department description

## Security

### Authentication

- Session-based authentication
- Sessions expire on browser close
- No password hashing yet (use unique passwords in production)

### Authorization

- Role-based access control (RBAC)
- Decorators check permissions before every action:
  - `@login_required` - Must be logged in
  - `@manager_required` - Manager or above
  - `@admin_required` - Admin only

### Best Practices

1. **Change Secret Key:** Never use default secret key in production
2. **HTTPS:** Use HTTPS in production (not HTTP)
3. **Firewall:** Restrict access to trusted IPs only
4. **Strong Passwords:** Implement proper password system in production
5. **Audit Logs:** Review audit logs regularly

## Production Deployment

### Using Gunicorn (Linux/Mac)

```bash
# Install gunicorn
pip install gunicorn

# Run with 4 workers
gunicorn -w 4 -b 0.0.0.0:5000 web.app:app
```

### Using Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Using Docker

Add to your `docker-compose.yml`:

```yaml
services:
  telegram_bot:
    # existing bot configuration...

  web_panel:
    build: .
    command: python web/app.py
    ports:
      - "5000:5000"
    environment:
      - WEB_SECRET_KEY=${WEB_SECRET_KEY}
      - WEB_PORT=5000
      - WEB_DEBUG=False
    volumes:
      - ./data:/app/data
```

## Troubleshooting

### Cannot Login

**Problem:** Login fails with "User not found"

**Solution:**
1. Ensure you've sent `/start` to the bot first
2. Use `/register` to join a department
3. Verify your user ID is correct

---

**Problem:** Login fails with "Manager role required"

**Solution:**
- You need manager role or above
- Contact an admin to promote you
- Or manually update database (see README.md)

### Cannot Create Admin

**Problem:** "User not found" error

**Solution:**
- Target user must have sent `/start` to bot
- Target user must be registered
- Verify user ID is correct (numeric)

---

**Problem:** Button doesn't respond

**Solution:**
- Check browser console for JavaScript errors
- Ensure you have internet connection (for Bootstrap CDN)
- Try refreshing the page

### Cannot Create Department

**Problem:** "Name already exists" error

**Solution:**
- Department names must be unique
- Check existing departments list
- Try a different name

### Web Server Won't Start

**Problem:** "Address already in use" error

**Solution:**
```bash
# Kill process on port 5000
# Linux/Mac:
lsof -ti:5000 | xargs kill -9

# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

---

**Problem:** "Module 'Flask' not found"

**Solution:**
```bash
pip install Flask==3.0.0
# Or
pip install -r requirements.txt
```

## Advanced Configuration

### Custom Port

Change port in `.env`:
```env
WEB_PORT=8080
```

Or pass as environment variable:
```bash
WEB_PORT=8080 python web/app.py
```

### Debug Mode

Enable debug mode for development:
```env
WEB_DEBUG=True
```

**Warning:** Never use debug mode in production!

### Custom Secret Key

Generate and set a secure secret key:

```bash
# Generate key
python -c "import secrets; print(secrets.token_hex(32))"

# Add to .env
WEB_SECRET_KEY=generated_key_here
```

## Integration with Telegram Bot

The web panel and Telegram bot share the same database, so:

- Changes in web panel reflect immediately in bot
- Actions in bot appear in web panel
- Audit logs capture both bot and web actions
- Both can run simultaneously

**Recommended Setup:**
- Run bot 24/7 for user interactions
- Run web panel when admins need to manage system
- Or run both 24/7 for maximum convenience

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Alt+D` | Go to Dashboard |
| `Alt+U` | Go to Users |
| `Alt+R` | Go to Reports |
| `Alt+L` | Logout |

*Keyboard shortcuts work when focus is not in an input field.*

## Mobile Support

The web panel is fully responsive and works on:
- Desktop browsers (Chrome, Firefox, Safari, Edge)
- Tablets (iPad, Android tablets)
- Mobile phones (iOS, Android)

**Recommended:** Use desktop for best experience, especially for creating departments and managing users.

## Future Enhancements

Planned features:

- [ ] Proper password authentication with hashing
- [ ] Two-factor authentication (2FA)
- [ ] Real-time notifications with WebSocket
- [ ] Advanced report analytics and charts
- [ ] Export users/reports to CSV/Excel
- [ ] Batch operations (bulk user import)
- [ ] Theme switcher (dark/light mode)
- [ ] Multi-language support
- [ ] Mobile app (React Native)

## Support

If you encounter issues:

1. Check this documentation
2. Review [README.md](README.md) for general setup
3. Check [ADMIN_COMMANDS.md](ADMIN_COMMANDS.md) for Telegram commands
4. Open an issue on GitHub

---

**Version:** 1.0.0
**Last Updated:** 2025-10-30
**Minimum Requirements:** Python 3.9+, Flask 3.0+, Modern browser
