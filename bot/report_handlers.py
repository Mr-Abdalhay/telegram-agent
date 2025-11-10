"""
Report-related Bot Command Handlers
Handles all reporting system commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, ConversationHandler
from datetime import datetime, timedelta
from bot.database_enhanced import DatabaseEnhanced
from bot.permissions import AccessControl
from bot.gemini_client import GeminiClient
from config import config
import json

# Initialize components
db = DatabaseEnhanced(config.DB_PATH)
access_control = AccessControl(db)
gemini = GeminiClient(config.GEMINI_API_KEY, config.GEMINI_MODEL)

# Conversation states
REPORT_TITLE, REPORT_CONTENT, REPORT_TYPE, REPORT_CONFIRM = range(4)
CUMULATIVE_PERIOD, CUMULATIVE_DEPARTMENTS, CUMULATIVE_CONFIRM = range(10, 13)
DEPT_NAME_AR, DEPT_NAME_EN, DEPT_PARENT, DEPT_CONFIRM = range(20, 24)


# ============================================================
# REGISTRATION & ROLE MANAGEMENT
# ============================================================

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register user with department and role"""
    user = update.effective_user

    # Ensure user exists in database (in case they skipped /start)
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    # Get all departments
    departments = db.get_all_departments()

    if not departments:
        await update.message.reply_text(
            "❌ لا توجد أقسام متاحة. يرجى التواصل مع المسؤول."
        )
        return

    # Show departments
    keyboard = []
    for dept in departments[:10]:  # Show first 10
        keyboard.append([InlineKeyboardButton(
            dept['name'],
            callback_data=f"register_dept_{dept['id']}"
        )])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 مرحباً {user.first_name}!\n\n"
        "لتسجيلك في النظام، يرجى اختيار قسمك:",
        reply_markup=reply_markup
    )


async def register_department_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle department selection for registration"""
    query = update.callback_query
    await query.answer()

    user = update.effective_user

    # Extract department ID from callback data (format: register_dept_1)
    dept_id = int(query.data.split('_')[-1])

    # Get department info
    dept = db.get_department(dept_id)
    if not dept:
        await query.edit_message_text("❌ القسم غير موجود.")
        return

    # Check if user already has a role
    existing_roles = db.get_user_roles(user.id)
    if existing_roles:
        await query.edit_message_text(
            f"✅ أنت مسجل بالفعل في النظام!\n\n"
            f"القسم: {existing_roles[0]['department_name']}\n"
            f"الدور: {existing_roles[0]['role_name_ar']}\n\n"
            f"استخدم /my_role لعرض صلاحياتك."
        )
        return

    # Assign employee role to user in selected department
    success = db.assign_role(
        user_id=user.id,
        role_name='employee',
        department_id=dept_id
    )

    if success:
        await query.edit_message_text(
            f"✅ تم تسجيلك بنجاح!\n\n"
            f"👤 الاسم: {user.first_name}\n"
            f"🏢 القسم: {dept['name']}\n"
            f"👔 الدور: موظف\n\n"
            f"يمكنك الآن:\n"
            f"• إنشاء التقارير: /create_report\n"
            f"• عرض تقاريرك: /my_reports\n"
            f"• عرض صلاحياتك: /my_role"
        )
    else:
        await query.edit_message_text(
            "❌ حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى."
        )


async def my_role_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's role and permissions"""
    user_id = update.effective_user.id

    # Get user roles
    roles = db.get_user_roles(user_id)

    if not roles:
        await update.message.reply_text(
            "❌ لم يتم تعيين دور لك بعد.\n"
            "استخدم /register للتسجيل في النظام."
        )
        return

    # Get permission summary
    summary = access_control.get_permission_summary(user_id)

    await update.message.reply_text(summary)


# ============================================================
# DEPARTMENT MANAGEMENT
# ============================================================

async def create_department_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start department creation wizard - Managers and above only"""
    user_id = update.effective_user.id

    # Check if user is manager or above
    user_role = db.get_user_primary_role(user_id)

    if not user_role:
        await update.message.reply_text(
            "❌ يجب أن تكون مسجلاً في النظام أولاً.\n"
            "استخدم /register للتسجيل."
        )
        return ConversationHandler.END

    role_name = user_role.get('role_name', '')

    if role_name not in ['manager', 'upper_manager', 'admin']:
        await update.message.reply_text(
            "❌ هذا الأمر متاح للمدراء فقط."
        )
        return ConversationHandler.END

    # Start wizard
    await update.message.reply_text(
        "📋 *إنشاء قسم جديد*\n\n"
        "👉 أدخل اسم القسم بالعربية:",
        
    )

    return DEPT_NAME_AR


async def dept_name_ar_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive Arabic name"""
    dept_name_ar = update.message.text.strip()

    if len(dept_name_ar) < 2:
        await update.message.reply_text(
            "❌ الاسم قصير جداً. أدخل اسم القسم بالعربية:"
        )
        return DEPT_NAME_AR

    # Save to context
    context.user_data['dept_name_ar'] = dept_name_ar

    await update.message.reply_text(
        f"✅ الاسم بالعربية: *{dept_name_ar}*\n\n"
        f"👉 الآن أدخل اسم القسم بالإنجليزية:",
        
    )

    return DEPT_NAME_EN


async def dept_name_en_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive English name"""
    dept_name_en = update.message.text.strip()

    if len(dept_name_en) < 2:
        await update.message.reply_text(
            "❌ الاسم قصير جداً. أدخل اسم القسم بالإنجليزية:"
        )
        return DEPT_NAME_EN

    # Save to context
    context.user_data['dept_name_en'] = dept_name_en

    # Ask for parent department
    departments = db.get_all_departments()

    if departments:
        keyboard = [[InlineKeyboardButton(
            "📁 قسم رئيسي (بدون قسم أب)",
            callback_data="dept_parent_none"
        )]]

        for dept in departments:
            keyboard.append([InlineKeyboardButton(
                f"📂 {dept['name']}",
                callback_data=f"dept_parent_{dept['id']}"
            )])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ الاسم بالإنجليزية: *{dept_name_en}*\n\n"
            f"👉 اختر القسم الأب (إذا كان قسم فرعي):",
            reply_markup=reply_markup,
            
        )
    else:
        # No departments exist, create as root
        context.user_data['parent_dept_id'] = None
        context.user_data['parent_dept_name'] = 'لا يوجد (قسم رئيسي)'

        await show_dept_confirmation(update, context)

    return DEPT_PARENT


async def dept_parent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle parent department selection"""
    query = update.callback_query
    await query.answer()

    if query.data == "dept_parent_none":
        context.user_data['parent_dept_id'] = None
        context.user_data['parent_dept_name'] = 'لا يوجد (قسم رئيسي)'
    else:
        parent_id = int(query.data.replace("dept_parent_", ""))
        parent_dept = db.get_department(parent_id)

        if parent_dept:
            context.user_data['parent_dept_id'] = parent_id
            context.user_data['parent_dept_name'] = parent_dept['name']
        else:
            await query.edit_message_text("❌ القسم الأب غير موجود.")
            return ConversationHandler.END

    await show_dept_confirmation(update, context, is_callback=True)

    return DEPT_CONFIRM


async def show_dept_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    """Show confirmation message"""
    dept_name_ar = context.user_data.get('dept_name_ar')
    dept_name_en = context.user_data.get('dept_name_en')
    parent_name = context.user_data.get('parent_dept_name')

    message = (
        "📋 *ملخص القسم الجديد*\n\n"
        f"• الاسم بالعربية: {dept_name_ar}\n"
        f"• الاسم بالإنجليزية: {dept_name_en}\n"
        f"• القسم الأب: {parent_name}\n\n"
        f"هل تريد إنشاء هذا القسم؟"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ نعم، أنشئ القسم", callback_data="dept_confirm_yes"),
            InlineKeyboardButton("❌ إلغاء", callback_data="dept_confirm_no")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_callback:
        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup,
            
        )
    else:
        await update.message.reply_text(
            message,
            reply_markup=reply_markup,
            
        )


async def dept_confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle confirmation"""
    query = update.callback_query
    await query.answer()

    if query.data == "dept_confirm_no":
        await query.edit_message_text("❌ تم إلغاء إنشاء القسم.")
        context.user_data.clear()
        return ConversationHandler.END

    # Create department
    user_id = update.effective_user.id
    dept_name_ar = context.user_data.get('dept_name_ar')
    dept_name_en = context.user_data.get('dept_name_en')
    parent_id = context.user_data.get('parent_dept_id')

    # Calculate level
    level = 0
    if parent_id:
        parent_dept = db.get_department(parent_id)
        if parent_dept:
            level = parent_dept['level'] + 1

    # Create department
    dept_id = db.create_department(
        name=dept_name_ar,
        name_en=dept_name_en,
        parent_department_id=parent_id,
        level=level,
        manager_id=None
    )

    if dept_id:
        # Log action
        db.log_action(
            user_id=user_id,
            action_type='create_department',
            details={'department_id': dept_id, 'name': dept_name_ar}
        )

        await query.edit_message_text(
            f"✅ *تم إنشاء القسم بنجاح!*\n\n"
            f"📂 {dept_name_ar} / {dept_name_en}\n"
            f"🆔 رقم القسم: {dept_id}\n\n"
            f"يمكن للمستخدمين الآن التسجيل في هذا القسم.",
            
        )
    else:
        await query.edit_message_text(
            "❌ فشل إنشاء القسم. قد يكون الاسم مستخدماً بالفعل."
        )

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_dept_creation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel department creation"""
    await update.message.reply_text("❌ تم إلغاء إنشاء القسم.")
    context.user_data.clear()
    return ConversationHandler.END


# ============================================================
# REPORT CREATION
# ============================================================

async def create_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start report creation wizard"""
    user_id = update.effective_user.id

    # Check permission
    if not access_control.can_create_report(user_id):
        await update.message.reply_text(
            "❌ ليس لديك صلاحية إنشاء التقارير.\n"
            "يرجى التواصل مع المسؤول."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📝 **إنشاء تقرير جديد**\n\n"
        "الخطوة 1/3: أدخل عنوان التقرير:",
        
    )

    return REPORT_TITLE


async def report_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive report title"""
    context.user_data['report_title'] = update.message.text

    await update.message.reply_text(
        "✅ تم حفظ العنوان.\n\n"
        "الخطوة 2/3: أدخل محتوى التقرير (يمكنك الكتابة بحرية):"
    )

    return REPORT_CONTENT


async def report_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive report content"""
    context.user_data['report_content'] = update.message.text

    # Show report type selection
    keyboard = [
        [InlineKeyboardButton("📅 يومي", callback_data="rtype_daily")],
        [InlineKeyboardButton("📆 أسبوعي", callback_data="rtype_weekly")],
        [InlineKeyboardButton("📊 شهري", callback_data="rtype_monthly")],
        [InlineKeyboardButton("🚨 حادث", callback_data="rtype_incident")],
        [InlineKeyboardButton("📋 عام", callback_data="rtype_custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "✅ تم حفظ المحتوى.\n\n"
        "الخطوة 3/3: اختر نوع التقرير:",
        reply_markup=reply_markup
    )

    return REPORT_TYPE


async def report_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm and create report"""
    query = update.callback_query
    await query.answer()

    # Get report type from callback
    report_type = query.data.replace('rtype_', '')
    context.user_data['report_type'] = report_type

    title = context.user_data.get('report_title')
    content = context.user_data.get('report_content')

    type_names = {
        'daily': '📅 يومي',
        'weekly': '📆 أسبوعي',
        'monthly': '📊 شهري',
        'incident': '🚨 حادث',
        'custom': '📋 عام'
    }

    # Show confirmation
    keyboard = [
        [InlineKeyboardButton("✅ إرسال التقرير", callback_data="submit_report")],
        [InlineKeyboardButton("💾 حفظ كمسودة", callback_data="draft_report")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_report")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"📋 **مراجعة التقرير:**\n\n"
        f"**العنوان:** {title}\n"
        f"**النوع:** {type_names.get(report_type, report_type)}\n"
        f"**المحتوى:**\n{content[:200]}{'...' if len(content) > 200 else ''}\n\n"
        f"اختر الإجراء:",
        reply_markup=reply_markup
    )

    return REPORT_CONFIRM


async def save_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save report to database"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    action = query.data  # 'submit_report' or 'draft_report'

    title = context.user_data.get('report_title')
    content = context.user_data.get('report_content')
    report_type = context.user_data.get('report_type')

    # Get user department
    user_dept = db.get_user_department(user_id)

    if not user_dept:
        await query.edit_message_text(
            "❌ لم يتم تحديد قسمك. يرجى استخدام /register أولاً."
        )
        return ConversationHandler.END

    # Validate
    valid, msg = access_control.validate_report_creation(user_id, user_dept)
    if not valid:
        await query.edit_message_text(msg)
        return ConversationHandler.END

    # Create report
    status = 'submitted' if action == 'submit_report' else 'draft'

    report_id = db.create_report(
        title=title,
        content=content,
        report_type=report_type,
        user_id=user_id,
        department_id=user_dept,
        status=status,
        priority='normal'
    )

    if action == 'submit_report':
        await query.edit_message_text(
            f"✅ تم إرسال التقرير بنجاح!\n\n"
            f"📊 رقم التقرير: #{report_id}\n"
            f"⏰ وقت الإرسال: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"يمكنك عرض التقرير باستخدام:\n"
            f"/view_report {report_id}"
        )
    else:
        await query.edit_message_text(
            f"💾 تم حفظ التقرير كمسودة\n\n"
            f"📊 رقم التقرير: #{report_id}\n\n"
            f"يمكنك عرض وتعديل المسودة لاحقاً:\n"
            f"/view_report {report_id}"
        )

    # Clear user data
    context.user_data.clear()

    return ConversationHandler.END


async def cancel_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel report creation"""
    query = update.callback_query
    await query.answer()

    context.user_data.clear()

    await query.edit_message_text(
        "❌ تم إلغاء إنشاء التقرير."
    )

    return ConversationHandler.END


# ============================================================
# VIEW REPORTS
# ============================================================

async def my_reports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user's own reports"""
    user_id = update.effective_user.id

    reports = db.get_user_reports(user_id, limit=10)

    if not reports:
        await update.message.reply_text(
            "📭 لا توجد لديك تقارير حتى الآن.\n\n"
            "استخدم /create_report لإنشاء تقرير جديد."
        )
        return

    message = "📊 **تقاريرك:**\n\n"

    status_emoji = {
        'draft': '✏️',
        'submitted': '📤',
        'pending_approval': '⏳',
        'approved': '✅',
        'rejected': '❌'
    }

    for report in reports:
        emoji = status_emoji.get(report['status'], '📄')
        message += f"{emoji} **#{report['id']}** - {report['title']}\n"
        message += f"   النوع: {report['report_type']} | الحالة: {report['status']}\n"
        message += f"   التاريخ: {report['submitted_at'] or 'مسودة'}\n\n"

    message += "\nلعرض تقرير محدد: /view_report <رقم التقرير>"

    await update.message.reply_text(message)


async def department_reports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View department reports (managers only)"""
    user_id = update.effective_user.id

    # Check if user is at least a manager
    if not access_control.is_manager(user_id):
        await update.message.reply_text(
            "❌ هذا الأمر متاح للمدراء فقط."
        )
        return

    user_dept = db.get_user_department(user_id)
    if not user_dept:
        await update.message.reply_text("❌ لم يتم تحديد قسمك.")
        return

    # Get department info
    dept = db.get_department(user_dept)

    # Get reports based on role
    if access_control.is_upper_manager(user_id):
        # Get hierarchical reports
        reports = db.get_hierarchical_reports(user_dept, status='submitted')
        title = f"📊 **تقارير {dept['name']} والأقسام الفرعية:**"
    else:
        # Get only department reports
        reports = db.get_department_reports(user_dept, status='submitted', limit=20)
        title = f"📊 **تقارير {dept['name']}:**"

    if not reports:
        await update.message.reply_text(
            f"{title}\n\n📭 لا توجد تقارير."
        )
        return

    message = f"{title}\n\n"

    for report in reports[:15]:  # Show first 15
        message += f"📄 **#{report['id']}** - {report['title']}\n"
        message += f"   بواسطة: {report['submitter_name']}\n"
        if 'department_name' in report:
            message += f"   القسم: {report['department_name']}\n"
        message += f"   التاريخ: {report['submitted_at']}\n\n"

    if len(reports) > 15:
        message += f"\n... و {len(reports) - 15} تقرير آخر\n"

    message += "\nلعرض تقرير: /view_report <رقم التقرير>"
    message += "\nللموافقة على تقرير: /approve_report <رقم التقرير>"

    await update.message.reply_text(message)


async def view_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View specific report"""
    user_id = update.effective_user.id

    # Get report ID from args
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ يرجى تحديد رقم التقرير.\n"
            "مثال: /view_report 123"
        )
        return

    report_id = int(context.args[0])

    # Check access
    if not access_control.can_view_report(user_id, report_id):
        await update.message.reply_text(
            "❌ ليس لديك صلاحية عرض هذا التقرير."
        )
        return

    # Get report
    report = db.get_report(report_id)

    if not report:
        await update.message.reply_text("❌ التقرير غير موجود.")
        return

    # Get comments
    comments = db.get_report_comments(report_id)

    message = f"📋 **تقرير #{report['id']}**\n\n"
    message += f"**العنوان:** {report['title']}\n"
    message += f"**النوع:** {report['report_type']}\n"
    message += f"**الحالة:** {report['status']}\n"
    message += f"**الأولوية:** {report['priority']}\n"
    message += f"**القسم:** {report['department_name']}\n"
    message += f"**المُرسل:** {report['submitter_name']}\n"
    message += f"**التاريخ:** {report['submitted_at'] or 'مسودة'}\n\n"
    message += f"**المحتوى:**\n{report['content']}\n\n"

    if report['is_cumulative']:
        message += f"📊 **تقرير تجميعي**\n"
        message += f"النوع: {report['aggregation_type']}\n"
        message += f"الفترة: {report['aggregation_period']}\n\n"

    if comments:
        message += f"\n💬 **التعليقات ({len(comments)}):**\n"
        for comment in comments[:3]:
            message += f"• {comment['author']}: {comment['comment'][:100]}...\n"

    # Add action buttons
    keyboard = []
    if access_control.can_approve_report(user_id, report_id):
        keyboard.append([InlineKeyboardButton(
            "✅ الموافقة",
            callback_data=f"approve_{report_id}"
        )])
    keyboard.append([InlineKeyboardButton(
        "💬 إضافة تعليق",
        callback_data=f"comment_{report_id}"
    )])

    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

    await update.message.reply_text(
        message,
        reply_markup=reply_markup
    )


# ============================================================
# APPROVALS
# ============================================================

async def approve_report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a report"""
    user_id = update.effective_user.id

    # Get report ID from args
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "❌ يرجى تحديد رقم التقرير.\n"
            "مثال: /approve_report 123"
        )
        return

    report_id = int(context.args[0])

    # Check permission
    if not access_control.can_approve_report(user_id, report_id):
        await update.message.reply_text(
            "❌ ليس لديك صلاحية الموافقة على هذا التقرير."
        )
        return

    # Add approval
    db.add_approval(report_id, user_id, 'approved')

    # Update report status
    db.update_report_status(report_id, 'approved')

    await update.message.reply_text(
        f"✅ تمت الموافقة على التقرير #{report_id}"
    )


async def approve_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle approve button click from view_report"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id

    # Extract report ID from callback_data (format: approve_123)
    report_id = int(query.data.split('_')[1])

    # Check permission
    if not access_control.can_approve_report(user_id, report_id):
        await query.edit_message_text(
            "❌ ليس لديك صلاحية الموافقة على هذا التقرير."
        )
        return

    # Add approval
    db.add_approval(report_id, user_id, 'approved')

    # Update report status
    db.update_report_status(report_id, 'approved')

    await query.edit_message_text(
        f"✅ **تمت الموافقة على التقرير #{report_id}**\n\n"
        f"تم تحديث حالة التقرير إلى: معتمد ✅\n\n"
        f"يمكنك عرض التقرير مرة أخرى: /view_report {report_id}",
        
    )


async def comment_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle comment button click from view_report"""
    query = update.callback_query
    await query.answer()

    # Extract report ID
    report_id = int(query.data.split('_')[1])

    # Store report ID for next step
    context.user_data['comment_report_id'] = report_id

    await query.edit_message_text(
        f"💬 **إضافة تعليق على التقرير #{report_id}**\n\n"
        f"أرسل تعليقك الآن:\n"
        f"(أو استخدم /cancel للإلغاء)"
    )


async def receive_comment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and save comment text"""
    user_id = update.effective_user.id
    comment_text = update.message.text

    # Get report ID from context
    report_id = context.user_data.get('comment_report_id')

    if not report_id:
        await update.message.reply_text(
            "❌ خطأ: لم يتم تحديد التقرير. يرجى المحاولة مرة أخرى."
        )
        return

    # Check if user can view the report
    if not access_control.can_view_report(user_id, report_id):
        await update.message.reply_text(
            "❌ ليس لديك صلاحية التعليق على هذا التقرير."
        )
        context.user_data.pop('comment_report_id', None)
        return

    # Save comment
    db.add_comment(report_id, user_id, comment_text)

    await update.message.reply_text(
        f"✅ **تم إضافة تعليقك بنجاح!**\n\n"
        f"📋 التقرير: #{report_id}\n"
        f"💬 التعليق: {comment_text[:100]}{'...' if len(comment_text) > 100 else ''}\n\n"
        f"عرض التقرير: /view_report {report_id}",
        
    )

    # Clear context
    context.user_data.pop('comment_report_id', None)


# ============================================================
# CUMULATIVE REPORTS
# ============================================================

async def create_cumulative_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create cumulative report (upper managers only)"""
    user_id = update.effective_user.id

    # Check permission
    if not access_control.can_create_cumulative_report(user_id):
        await update.message.reply_text(
            "❌ هذا الأمر متاح للمدراء الأعلى فقط."
        )
        return

    # Show period selection
    keyboard = [
        [InlineKeyboardButton("📅 أسبوعي", callback_data="cum_weekly")],
        [InlineKeyboardButton("📆 شهري", callback_data="cum_monthly")],
        [InlineKeyboardButton("📊 ربع سنوي", callback_data="cum_quarterly")],
        [InlineKeyboardButton("📋 مخصص", callback_data="cum_custom")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📊 **إنشاء تقرير تجميعي**\n\n"
        "اختر الفترة الزمنية:",
        reply_markup=reply_markup
    )


async def cumulative_period_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle cumulative report period selection"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    period = query.data.replace('cum_', '')

    # Calculate date range
    end_date = datetime.now()
    if period == 'weekly':
        start_date = end_date - timedelta(days=7)
    elif period == 'monthly':
        start_date = end_date - timedelta(days=30)
    elif period == 'quarterly':
        start_date = end_date - timedelta(days=90)
    else:
        start_date = end_date - timedelta(days=7)

    context.user_data['cumulative_period'] = period
    context.user_data['cumulative_start'] = start_date.strftime('%Y-%m-%d')
    context.user_data['cumulative_end'] = end_date.strftime('%Y-%m-%d')

    # Get user's department
    user_dept = db.get_user_department(user_id)
    accessible_depts = db.get_department_hierarchy(user_dept)

    # Get reports from these departments
    reports = db.get_hierarchical_reports(
        user_dept,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d'),
        status='approved'
    )

    if not reports:
        await query.edit_message_text(
            f"❌ لا توجد تقارير معتمدة في الفترة المحددة.\n"
            f"من {start_date.strftime('%Y-%m-%d')} إلى {end_date.strftime('%Y-%m-%d')}"
        )
        return

    context.user_data['cumulative_source_ids'] = [r['id'] for r in reports]

    # Show confirmation
    await query.edit_message_text(
        f"📊 **التقرير التجميعي**\n\n"
        f"الفترة: {period}\n"
        f"من: {start_date.strftime('%Y-%m-%d')}\n"
        f"إلى: {end_date.strftime('%Y-%m-%d')}\n\n"
        f"✅ تم العثور على {len(reports)} تقرير معتمد\n"
        f"📁 من {len(accessible_depts)} قسم\n\n"
        f"🔄 جاري إنشاء التقرير التجميعي..."
    )

    # Generate cumulative report using AI
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING
    )

    # Combine all report contents
    combined_text = "\n\n---\n\n".join([
        f"تقرير من {r['department_name']}:\n{r['content']}"
        for r in reports
    ])

    # Use Gemini to summarize
    summary = await gemini.summarize_text(
        combined_text,
        language='ar'
    )

    # Create cumulative report
    cumulative_id = db.create_cumulative_report(
        title=f"تقرير تجميعي - {period}",
        source_report_ids=[r['id'] for r in reports],
        aggregation_type='summary',
        aggregation_period=period,
        user_id=user_id,
        department_id=user_dept,
        content=summary,
        start_date=start_date.strftime('%Y-%m-%d'),
        end_date=end_date.strftime('%Y-%m-%d')
    )

    await update.effective_chat.send_message(
        f"✅ **تم إنشاء التقرير التجميعي #{cumulative_id}**\n\n"
        f"📊 ملخص التقرير:\n\n{summary[:500]}...\n\n"
        f"لعرض التقرير الكامل: /view_report {cumulative_id}",
        
    )


# ============================================================
# SEARCH & FILTERS
# ============================================================

async def search_reports_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Search reports (basic implementation)"""
    user_id = update.effective_user.id

    accessible_reports = access_control.get_accessible_reports(
        user_id, limit=20, status='approved'
    )

    if not accessible_reports:
        await update.message.reply_text("📭 لا توجد تقارير متاحة.")
        return

    message = "🔍 **التقارير المتاحة:**\n\n"

    for report in accessible_reports[:10]:
        message += f"📄 **#{report['id']}** - {report['title']}\n"
        message += f"   التاريخ: {report['submitted_at']}\n\n"

    await update.message.reply_text(message)


# ============================================================
# HIDDEN ADMIN COMMANDS (Not shown in /help)
# ============================================================

async def create_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to create admin account
    Usage: /createadmin <user_id>
    Only existing admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        # Don't reveal this command exists - just ignore
        return

    # Check args
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "🔐 **Create Admin Account**\n\n"
            "Usage: `/createadmin <user_id>`\n\n"
            "Example: `/createadmin 123456789`\n\n"
            "Note: User must have used /start first.",
            
        )
        return

    target_user_id = int(context.args[0])

    # Check if target user exists
    target_user = db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text(
            f"❌ User {target_user_id} not found.\n"
            f"User must send /start to the bot first."
        )
        return

    # Check if already admin
    existing_roles = db.get_user_roles(target_user_id)
    for role in existing_roles:
        if role['role_name'] == 'admin':
            await update.message.reply_text(
                f"⚠️ User {target_user['first_name']} is already an admin."
            )
            return

    # Assign admin role
    success = db.assign_role(
        user_id=target_user_id,
        role_name='admin',
        department_id=None,  # Admin doesn't need department
        assigned_by=user_id
    )

    if success:
        await update.message.reply_text(
            f"✅ **Admin Created Successfully**\n\n"
            f"👤 User: {target_user['first_name']} (@{target_user['username']})\n"
            f"🔑 User ID: {target_user_id}\n"
            f"👔 Role: Administrator\n\n"
            f"**Permissions:**\n"
            f"• Full system access\n"
            f"• View all reports\n"
            f"• Manage users & departments\n"
            f"• Create cumulative reports\n"
            f"• Approve any report\n\n"
            f"User can verify with /my_role",
            
        )
    else:
        await update.message.reply_text(
            "❌ Failed to assign admin role. Try again or check database."
        )


async def remove_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to remove admin role
    Usage: /removeadmin <user_id>
    Only admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        # Don't reveal this command exists
        return

    # Check args
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "🔐 **Remove Admin Role**\n\n"
            "Usage: `/removeadmin <user_id>`\n\n"
            "Example: `/removeadmin 123456789`",
            
        )
        return

    target_user_id = int(context.args[0])

    # Prevent self-removal
    if target_user_id == user_id:
        await update.message.reply_text(
            "❌ You cannot remove your own admin role.\n"
            "Ask another admin to do this."
        )
        return

    # Check if target user exists
    target_user = db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text(f"❌ User {target_user_id} not found.")
        return

    # Check if user is admin
    existing_roles = db.get_user_roles(target_user_id)
    is_admin = False

    for role in existing_roles:
        if role['role_name'] == 'admin':
            is_admin = True
            break

    if not is_admin:
        await update.message.reply_text(
            f"⚠️ User {target_user['first_name']} is not an admin."
        )
        return

    # Remove admin role from database
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    cursor.execute(
        '''
        UPDATE user_roles
        SET is_active = 0
        WHERE user_id = ? AND role_id = (SELECT id FROM roles WHERE name = 'admin')
        ''',
        (target_user_id,)
    )

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ **Admin Role Removed**\n\n"
        f"👤 User: {target_user['first_name']} (@{target_user['username']})\n"
        f"🔑 User ID: {target_user_id}\n\n"
        f"User is no longer an administrator.\n"
        f"They can use /my_role to see their current permissions.",
        
    )


async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to list all admins
    Usage: /listadmins
    Only admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        # Don't reveal this command exists
        return

    # Query all users with admin role
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT u.user_id, u.username, u.first_name, u.last_name, ur.assigned_at
        FROM users u
        JOIN user_roles ur ON u.user_id = ur.user_id
        JOIN roles r ON ur.role_id = r.id
        WHERE r.name = 'admin' AND ur.is_active = 1
        ORDER BY ur.assigned_at DESC
    ''')

    admins = cursor.fetchall()
    conn.close()

    if not admins:
        await update.message.reply_text("📭 No administrators found.")
        return

    message = "👑 **System Administrators**\n\n"

    for admin in admins:
        user_id_admin, username, first_name, last_name, assigned_at = admin
        full_name = f"{first_name} {last_name or ''}".strip()
        message += f"👤 **{full_name}**\n"
        message += f"   @{username or 'N/A'}\n"
        message += f"   ID: `{user_id_admin}`\n"
        message += f"   Since: {assigned_at[:10]}\n\n"

    message += f"**Total:** {len(admins)} administrator(s)"

    await update.message.reply_text(message)


async def promote_manager_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to promote user to manager or upper_manager
    Usage: /promote <user_id> <role> [department_id]
    Only admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        return

    # Check args
    if len(context.args) < 2:
        await update.message.reply_text(
            "🔐 **Promote User**\n\n"
            "Usage: `/promote <user_id> <role> [department_id]`\n\n"
            "Roles: manager, upper_manager\n\n"
            "Examples:\n"
            "• `/promote 123456789 manager 2`\n"
            "• `/promote 123456789 upper_manager 2`",
            
        )
        return

    target_user_id = int(context.args[0])
    role_name = context.args[1].lower()
    dept_id = int(context.args[2]) if len(context.args) > 2 else None

    # Validate role
    if role_name not in ['manager', 'upper_manager']:
        await update.message.reply_text(
            "❌ Invalid role. Use: manager or upper_manager"
        )
        return

    # Check if user exists
    target_user = db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text(f"❌ User {target_user_id} not found.")
        return

    # Get user's department if not specified
    if not dept_id:
        user_dept = db.get_user_department(target_user_id)
        if not user_dept:
            await update.message.reply_text(
                "❌ User has no department. Please specify department_id."
            )
            return
        dept_id = user_dept

    # Assign new role
    success = db.assign_role(
        user_id=target_user_id,
        role_name=role_name,
        department_id=dept_id,
        assigned_by=user_id
    )

    if success:
        dept = db.get_department(dept_id)
        role_ar = "مدير" if role_name == "manager" else "مدير أعلى"

        await update.message.reply_text(
            f"✅ **User Promoted**\n\n"
            f"👤 User: {target_user['first_name']}\n"
            f"🔑 User ID: {target_user_id}\n"
            f"👔 New Role: {role_ar} ({role_name})\n"
            f"🏢 Department: {dept['name']}\n\n"
            f"User can verify with /my_role",
            
        )
    else:
        await update.message.reply_text(
            "❌ Failed to promote user. May already have this role."
        )


async def remove_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to remove/deactivate a user
    Usage: /removeuser <user_id>
    Only admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        return

    # Check args
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "🔐 **Remove User**\n\n"
            "Usage: `/removeuser <user_id>`\n\n"
            "Example: `/removeuser 123456789`\n\n"
            "⚠️ This will:\n"
            "• Deactivate the user account\n"
            "• Remove all their roles\n"
            "• Keep their data for audit purposes\n\n"
            "User can be reactivated later if needed.",
            
        )
        return

    target_user_id = int(context.args[0])

    # Prevent self-removal
    if target_user_id == user_id:
        await update.message.reply_text(
            "❌ You cannot remove yourself.\n"
            "Ask another admin to do this."
        )
        return

    # Check if target user exists
    target_user = db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text(f"❌ User {target_user_id} not found.")
        return

    # Check if user is admin - warn if removing another admin
    existing_roles = db.get_user_roles(target_user_id)
    is_target_admin = any(role['role_name'] == 'admin' for role in existing_roles)

    if is_target_admin:
        await update.message.reply_text(
            f"⚠️ **WARNING: Removing Administrator**\n\n"
            f"User {target_user['first_name']} is an administrator!\n\n"
            f"To proceed:\n"
            f"1. First use: `/removeadmin {target_user_id}`\n"
            f"2. Then use: `/removeuser {target_user_id}`\n\n"
            f"This prevents accidental admin removal.",
            
        )
        return

    # Deactivate user
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # Deactivate user
    cursor.execute(
        'UPDATE users SET is_active = 0 WHERE user_id = ?',
        (target_user_id,)
    )

    # Deactivate all user roles
    cursor.execute(
        'UPDATE user_roles SET is_active = 0 WHERE user_id = ?',
        (target_user_id,)
    )

    # Get user's roles before removal for logging
    role_names = [role['role_name_ar'] for role in existing_roles]

    conn.commit()
    conn.close()

    # Format roles for display
    roles_text = ", ".join(role_names) if role_names else "لا يوجد"

    await update.message.reply_text(
        f"✅ **User Removed Successfully**\n\n"
        f"👤 User: {target_user['first_name']} {target_user['last_name'] or ''}\n"
        f"🔑 User ID: `{target_user_id}`\n"
        f"📧 Username: @{target_user['username'] or 'N/A'}\n"
        f"👔 Previous Roles: {roles_text}\n\n"
        f"**Actions taken:**\n"
        f"• User account deactivated\n"
        f"• All roles removed\n"
        f"• User can no longer access the bot\n"
        f"• Data retained for audit purposes\n\n"
        f"💡 To reactivate: `/activateuser {target_user_id}`",
        
    )


async def activate_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to reactivate a deactivated user
    Usage: /activateuser <user_id>
    Only admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        return

    # Check args
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "🔐 **Activate User**\n\n"
            "Usage: `/activateuser <user_id>`\n\n"
            "Example: `/activateuser 123456789`\n\n"
            "This will reactivate a previously removed user.",
            
        )
        return

    target_user_id = int(context.args[0])

    # Check if user exists
    target_user = db.get_user(target_user_id)
    if not target_user:
        await update.message.reply_text(f"❌ User {target_user_id} not found in database.")
        return

    # Check if user is already active
    if target_user.get('is_active', 1):
        await update.message.reply_text(
            f"⚠️ User {target_user['first_name']} is already active."
        )
        return

    # Reactivate user
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # Reactivate user account
    cursor.execute(
        'UPDATE users SET is_active = 1 WHERE user_id = ?',
        (target_user_id,)
    )

    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ **User Reactivated Successfully**\n\n"
        f"👤 User: {target_user['first_name']} {target_user['last_name'] or ''}\n"
        f"🔑 User ID: `{target_user_id}`\n\n"
        f"**Actions taken:**\n"
        f"• User account reactivated\n"
        f"• User can now use /start to re-register\n\n"
        f"⚠️ Note: User's previous roles were NOT restored.\n"
        f"Use /promote to assign new roles if needed.",
        
    )


async def list_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Hidden command to list all users
    Usage: /listusers [active|inactive|all]
    Only admins can use this
    """
    user_id = update.effective_user.id

    # Check if requester is admin
    if not access_control.is_admin(user_id):
        return

    # Get filter parameter
    status_filter = context.args[0].lower() if context.args else 'active'

    if status_filter not in ['active', 'inactive', 'all']:
        await update.message.reply_text(
            "🔐 **List Users**\n\n"
            "Usage: `/listusers [active|inactive|all]`\n\n"
            "Examples:\n"
            "• `/listusers` - Show active users (default)\n"
            "• `/listusers all` - Show all users\n"
            "• `/listusers inactive` - Show deactivated users",
            
        )
        return

    # Query users
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    if status_filter == 'active':
        query = 'SELECT user_id, username, first_name, last_name, created_at FROM users WHERE is_active = 1 ORDER BY created_at DESC'
    elif status_filter == 'inactive':
        query = 'SELECT user_id, username, first_name, last_name, created_at FROM users WHERE is_active = 0 ORDER BY created_at DESC'
    else:  # all
        query = 'SELECT user_id, username, first_name, last_name, created_at, is_active FROM users ORDER BY created_at DESC'

    cursor.execute(query)
    users = cursor.fetchall()
    conn.close()

    if not users:
        await update.message.reply_text(f"📭 No {status_filter} users found.")
        return

    # Build message
    status_emoji = {
        'active': '✅',
        'inactive': '❌',
        'all': '👥'
    }

    message = f"{status_emoji.get(status_filter, '👥')} **{status_filter.title()} Users** ({len(users)})\n\n"

    for i, user in enumerate(users[:20], 1):  # Show first 20
        if status_filter == 'all':
            user_id_val, username, first_name, last_name, created_at, is_active = user
            status_icon = "✅" if is_active else "❌"
        else:
            user_id_val, username, first_name, last_name, created_at = user
            status_icon = status_emoji.get(status_filter, '')

        full_name = f"{first_name} {last_name or ''}".strip()

        # Get user role
        user_roles = db.get_user_roles(user_id_val)
        role_text = user_roles[0]['role_name_ar'] if user_roles else "لا يوجد"

        message += f"{status_icon} **{i}. {full_name}**\n"
        message += f"   @{username or 'N/A'} | ID: `{user_id_val}`\n"
        message += f"   Role: {role_text}\n"
        message += f"   Joined: {created_at[:10]}\n\n"

    if len(users) > 20:
        message += f"\n... and {len(users) - 20} more users\n"

    message += f"\n**Total:** {len(users)} {status_filter} user(s)"

    await update.message.reply_text(message)
