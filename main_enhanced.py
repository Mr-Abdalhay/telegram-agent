#!/usr/bin/env python3
"""
Enhanced Telegram Bot with Reporting System
Supports hierarchical departments, roles, and cumulative reporting
"""

import logging
import os
import sys
from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Import existing handlers
from bot.handlers import (
    start,
    help_command,
    handle_message,
    summary_command,
    history_command,
    train_command,
    stats_command,
    clear_command,
)

# Import new report handlers
from bot.report_handlers import (
    # Registration
    register_command,
    register_department_callback,
    my_role_command,
    # Department Management
    create_department_command,
    dept_name_ar_handler,
    dept_name_en_handler,
    dept_parent_callback,
    dept_confirm_callback,
    cancel_dept_creation,
    DEPT_NAME_AR,
    DEPT_NAME_EN,
    DEPT_PARENT,
    DEPT_CONFIRM,
    # Report creation
    create_report_command,
    report_title,
    report_content,
    report_confirm,
    save_report,
    cancel_report,
    REPORT_TITLE,
    REPORT_CONTENT,
    REPORT_TYPE,
    REPORT_CONFIRM,
    # View reports
    my_reports_command,
    department_reports_command,
    view_report_command,
    # Approvals
    approve_report_command,
    approve_button_callback,
    comment_button_callback,
    receive_comment,
    # Cumulative reports
    create_cumulative_command,
    cumulative_period_handler,
    # Search
    search_reports_command,
    # Hidden admin commands
    create_admin_command,
    remove_admin_command,
    list_admins_command,
    promote_manager_command,
    remove_user_command,
    activate_user_command,
    list_users_command,
)

from config import config


# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def setup_bot_commands(application):
    """Setup bot command menu"""
    commands = [
        # General commands
        BotCommand("start", "بدء المحادثة - Start the bot"),
        BotCommand("help", "عرض المساعدة - Show help"),
        BotCommand("summary", "تلخيص تقاريرك - Summarize your reports"),
        BotCommand("history", "عرض آخر المحادثات - Show conversation history"),
        BotCommand("stats", "إحصائيات الاستخدام - Usage statistics"),
        BotCommand("clear", "مسح ذاكرة المحادثة - Clear chat history"),

        # Reporting system
        BotCommand("register", "التسجيل في النظام - Register in system"),
        BotCommand("my_role", "عرض دورك وصلاحياتك - Show your role"),
        BotCommand("create_report", "إنشاء تقرير جديد - Create new report"),
        BotCommand("my_reports", "عرض تقاريرك - View your reports"),
        BotCommand("view_report", "عرض تقرير محدد - View specific report"),

        # Manager commands
        BotCommand("department_reports", "تقارير القسم - Department reports"),
        BotCommand("approve_report", "الموافقة على تقرير - Approve report"),
        BotCommand("create_department", "إنشاء قسم - Create department"),

        # Upper manager commands
        BotCommand("create_cumulative", "تقرير تجميعي - Cumulative report"),
        BotCommand("search", "البحث في التقارير - Search reports"),
    ]

    await application.bot.set_my_commands(commands)
    logger.info("✅ Bot commands menu set successfully")


def main():
    """Start the bot"""

    # Check for token
    if not config.BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in .env file")
        return

    # Create data directories
    os.makedirs('./data', exist_ok=True)
    os.makedirs('./data/model', exist_ok=True)
    os.makedirs('./data/training_data', exist_ok=True)

    # Create application
    application = Application.builder().token(config.BOT_TOKEN).build()

    # ========================================
    # EXISTING COMMANDS
    # ========================================
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("summary", summary_command))
    application.add_handler(CommandHandler("history", history_command))
    application.add_handler(CommandHandler("model", train_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("clear", clear_command))

    # ========================================
    # NEW REPORTING SYSTEM COMMANDS
    # ========================================

    # Registration & Role Management
    application.add_handler(CommandHandler("register", register_command))
    application.add_handler(CommandHandler("my_role", my_role_command))
    application.add_handler(CommandHandler("permissions", my_role_command))  # Alias

    # Department Creation (Conversation Handler - Managers Only)
    create_dept_conv = ConversationHandler(
        entry_points=[CommandHandler("create_department", create_department_command)],
        states={
            DEPT_NAME_AR: [MessageHandler(filters.TEXT & ~filters.COMMAND, dept_name_ar_handler)],
            DEPT_NAME_EN: [MessageHandler(filters.TEXT & ~filters.COMMAND, dept_name_en_handler)],
            DEPT_PARENT: [CallbackQueryHandler(dept_parent_callback, pattern=r'^dept_parent_')],
            DEPT_CONFIRM: [CallbackQueryHandler(dept_confirm_callback, pattern=r'^dept_confirm_')],
        },
        fallbacks=[CommandHandler("cancel", cancel_dept_creation)],
    )
    application.add_handler(create_dept_conv)

    # Report Creation (Conversation Handler)
    create_report_conv = ConversationHandler(
        entry_points=[CommandHandler("create_report", create_report_command)],
        states={
            REPORT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_title)],
            REPORT_CONTENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, report_content)],
            REPORT_TYPE: [CallbackQueryHandler(report_confirm, pattern=r'^rtype_')],
            REPORT_CONFIRM: [
                CallbackQueryHandler(save_report, pattern=r'^(submit|draft)_report$'),
                CallbackQueryHandler(cancel_report, pattern=r'^cancel_report$'),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_report)],
    )
    application.add_handler(create_report_conv)

    # View Reports
    application.add_handler(CommandHandler("my_reports", my_reports_command))
    application.add_handler(CommandHandler("department_reports", department_reports_command))
    application.add_handler(CommandHandler("dept_reports", department_reports_command))  # Alias
    application.add_handler(CommandHandler("view_report", view_report_command))

    # Approvals
    application.add_handler(CommandHandler("approve_report", approve_report_command))
    application.add_handler(CommandHandler("approve", approve_report_command))  # Alias

    # Cumulative Reports
    application.add_handler(CommandHandler("create_cumulative", create_cumulative_command))
    application.add_handler(CommandHandler("cumulative", create_cumulative_command))  # Alias
    application.add_handler(CallbackQueryHandler(cumulative_period_handler, pattern=r'^cum_'))

    # Search
    application.add_handler(CommandHandler("search_reports", search_reports_command))
    application.add_handler(CommandHandler("search", search_reports_command))  # Alias

    # ========================================
    # HIDDEN ADMIN COMMANDS (Not in /help)
    # ========================================
    application.add_handler(CommandHandler("createadmin", create_admin_command))
    application.add_handler(CommandHandler("removeadmin", remove_admin_command))
    application.add_handler(CommandHandler("listadmins", list_admins_command))
    application.add_handler(CommandHandler("promote", promote_manager_command))
    application.add_handler(CommandHandler("removeuser", remove_user_command))
    application.add_handler(CommandHandler("activateuser", activate_user_command))
    application.add_handler(CommandHandler("listusers", list_users_command))

    # ========================================
    # CALLBACK QUERY HANDLERS
    # ========================================
    # Callback query handlers (for buttons)
    # Registration callback
    application.add_handler(CallbackQueryHandler(
        register_department_callback,
        pattern=r'^register_dept_'
    ))

    # Approve button callback
    application.add_handler(CallbackQueryHandler(
        approve_button_callback,
        pattern=r'^approve_\d+$'
    ))

    # Comment button callback
    application.add_handler(CallbackQueryHandler(
        comment_button_callback,
        pattern=r'^comment_\d+$'
    ))

    # ========================================
    # MESSAGE HANDLERS
    # ========================================

    # Comment text receiver (must be before general message handler)
    # This handles text messages when user is adding a comment
    async def comment_or_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Route message to comment handler or general handler"""
        if 'comment_report_id' in context.user_data:
            await receive_comment(update, context)
        else:
            await handle_message(update, context)

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, comment_or_message)
    )

    # Setup bot commands menu
    application.post_init = setup_bot_commands

    # Start bot
    logger.info("🚀 البوت يعمل الآن مع نظام التقارير المحسّن...")
    logger.info("📊 الأوامر الجديدة:")
    logger.info("   /register - التسجيل في النظام")
    logger.info("   /my_role - عرض دورك وصلاحياتك")
    logger.info("   /create_report - إنشاء تقرير جديد")
    logger.info("   /my_reports - عرض تقاريرك")
    logger.info("   /department_reports - عرض تقارير القسم")
    logger.info("   /create_cumulative - إنشاء تقرير تجميعي")
    logger.info("   /approve_report - الموافقة على تقرير")
    logger.info("💡 Command menu will appear when you type '/' in Telegram")

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    import scripts.migrate_database as DatabaseMigration
    db_path = './data/conversations.db'
    DatabaseMigration.create_fresh_database(db_path)
    import sys, os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import web.app as wb
    import scripts.create_default_admin as init_admin
    from scripts.add_is_primary_column import add_is_primary_column
    add_is_primary_column()
    init_admin.create_default_admin()
    wb.port = int(os.getenv('WEB_PORT', 5000))
    wb.debug = os.getenv('WEB_DEBUG', 'False').lower() == 'true'
    print(f"\n{'='*60}")
    print(f"  WEB ADMIN PANEL STARTING")
    print(f"{'='*60}")
    print(f"  URL: http://localhost:{wb.port}")
    print(f"  Debug: {wb.debug}")
    print(f"{'='*60}\n")
    import threading

    # Start web app in a background thread
    threading.Thread(
        target=wb.app.run,
        kwargs={"host": "0.0.0.0", "port": wb.port, "debug": wb.debug},
        daemon=True
    ).start()

    main()
    

  
