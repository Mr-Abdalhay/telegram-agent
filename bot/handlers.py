from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes
from datetime import datetime
from .database_enhanced import DatabaseEnhanced
from .gemini_client import GeminiClient
from config import config
import asyncio


# تهيئة المكونات
db = DatabaseEnhanced(config.DB_PATH)
gemini = GeminiClient(config.GEMINI_API_KEY, config.GEMINI_MODEL)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر البداية"""
    user = update.effective_user

    # حفظ المستخدم في قاعدة البيانات
    db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
    )

    welcome_message = f"""
مرحباً {user.first_name}! 👋

أنا بوت ذكي يمكنني:
• 💬 الإجابة على أسئلتك
• 📝 تلخيص التقارير
• 🧠 التعلم من محادثاتنا
• 📊 عرض سجل المحادثات
• 📋 إدارة التقارير والأقسام

📚 **الأوامر العامة:**
/help - عرض المساعدة
/summary - تلخيص تقاريرك (متاح للجميع)
/history - عرض آخر 5 محادثات
/stats - إحصائيات الاستخدام
/clear - مسح ذاكرة المحادثة

📊 **نظام التقارير:**
/register - التسجيل في النظام
/my_role - عرض دورك وصلاحياتك
/create_report - إنشاء تقرير جديد
/my_reports - عرض تقاريرك
/department_reports - عرض تقارير القسم (للمدراء)
/create_cumulative - إنشاء تقرير تجميعي (للمدراء الأعلى)
/approve_report - الموافقة على تقرير (للمدراء)
/search - البحث في التقارير

اكتب أي سؤال وسأجيب عليه! 🤖
    """

    await update.message.reply_text(welcome_message)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر المساعدة"""
    help_text = """
📚 **قائمة الأوامر:**

**الأوامر العامة:**
• /start - بدء المحادثة
• /help - عرض هذه الرسالة
• /summary - تلخيص تقاريرك (متاح للجميع)
• /history - عرض آخر 5 محادثات
• /stats - عرض إحصائيات الاستخدام
• /clear - مسح سجل المحادثات

**📊 نظام التقارير:**
• /register - التسجيل في النظام
• /my_role - عرض دورك وصلاحياتك
• /create_report - إنشاء تقرير جديد
• /my_reports - عرض تقاريرك
• /view_report <رقم> - عرض تقرير محدد

**👔 أوامر المدراء:**
• /department_reports - عرض تقارير القسم
• /approve_report <رقم> - الموافقة على تقرير

**🎯 أوامر المدراء الأعلى:**
• /create_cumulative - إنشاء تقرير تجميعي
• /search - البحث في التقارير

💡 **نصائح:**
- اكتب أسئلتك بشكل واضح
- يمكنك الكتابة بالعربية أو الإنجليزية
- البوت يتعلم من كل محادثة
- استخدم /register للبدء بنظام التقارير
    """

    await update.message.reply_text(help_text, parse_mode='Markdown')


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية"""
    user_id = update.effective_user.id
    message = update.message.text

    # إظهار أن البوت يكتب
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    try:
        # توليد الرد باستخدام Gemini
        response = await gemini.generate_response(
            prompt=message,
            user_id=user_id,
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
            use_chat_history=True,
            language="ar"
        )

        if not response or len(response.strip()) < 3:
            response = "عذراً، لم أفهم سؤالك. هل يمكنك إعادة صياغته؟"

        # حفظ المحادثة
        db.save_conversation(user_id, message, response)

        # إرسال الرد
        await update.message.reply_text(response)

    except Exception as e:
        print(f"Error processing message: {e}")
        await update.message.reply_text(
            "عذراً، حدث خطأ في معالجة رسالتك. الرجاء المحاولة مرة أخرى."
        )


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """تلخيص تقارير المستخدم"""
    user_id = update.effective_user.id

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    # جلب تقارير المستخدم (آخر 10 تقارير)
    reports = db.get_user_reports(user_id, limit=10)

    if not reports:
        await update.message.reply_text("لا توجد تقارير لتلخيصها.")
        return

    # جمع محتوى التقارير
    reports_text = ""
    for i, report_summary in enumerate(reports, 1):
        # جلب التقرير الكامل
        full_report = db.get_report(report_summary['id'])
        if full_report and full_report.get('content'):
            reports_text += f"\n\n--- التقرير {i}: {full_report['title']} ---\n"
            reports_text += f"النوع: {full_report['report_type']}\n"
            reports_text += f"الحالة: {full_report['status']}\n"
            reports_text += f"المحتوى:\n{full_report['content']}\n"

    if not reports_text.strip():
        await update.message.reply_text("التقارير الموجودة لا تحتوي على محتوى لتلخيصه.")
        return

    # توليد الملخص باستخدام Gemini
    try:
        summary = await gemini.summarize_text(reports_text, language='ar')

        # Check if summary is error message
        if summary.startswith("عذراً") or summary.startswith("تم حظر"):
            await update.message.reply_text(f"❌ فشل التلخيص:\n{summary}")
            return

        # حفظ الملخص
        today = datetime.now().strftime('%Y-%m-%d')
        db.save_summary(user_id, summary, today)

        await update.message.reply_text(
            f"📝 ملخص آخر {len(reports)} تقرير:\n\n{summary}\n\n"
            f"💡 لعرض تقاريرك الكاملة: /my_reports"
        )

    except Exception as e:
        print(f"Error in summary command: {e}")
        await update.message.reply_text(f"❌ خطأ في التلخيص: {str(e)}")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض آخر المحادثات"""
    user_id = update.effective_user.id

    conversations = db.get_user_conversations(user_id, limit=5)

    if not conversations:
        await update.message.reply_text("لا توجد محادثات سابقة.")
        return

    history_text = "📜 **آخر 5 محادثات:**\n\n"

    for i, conv in enumerate(conversations, 1):
        history_text += f"**{i}. محادثة:**\n"
        history_text += f"👤 أنت: {conv['message']}\n"
        history_text += f"🤖 البوت: {conv['response']}\n"
        history_text += f"🕐 {conv['timestamp']}\n\n"

    await update.message.reply_text(history_text, parse_mode='Markdown')


async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معلومات عن النموذج (Gemini لا يحتاج تدريب محلي)"""
    user_id = update.effective_user.id

    # جلب عدد المحادثات
    conversations = db.get_user_conversations(user_id, limit=100)
    
    info_text = f"""
🤖 **معلومات النموذج:**

• النموذج المستخدم: {config.GEMINI_MODEL}
• عدد محادثاتك: {len(conversations)}
• ذاكرة المحادثة: نشطة

💡 **ملاحظة:**
يستخدم البوت نموذج Gemini من Google، والذي يتعلم ويتحسن تلقائياً من كل محادثة.
لا حاجة للتدريب اليدوي!
    """
    
    await update.message.reply_text(info_text, parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مسح ذاكرة المحادثة"""
    user = update.effective_user
    user_id = user.id

    # مسح ذاكرة المحادثة في Gemini
    gemini.clear_chat_history(user_id)

    # Send welcome message again
    welcome_message = f"""
🧹 تم مسح ذاكرة المحادثة!

مرحباً {user.first_name}! 👋

أنا بوت ذكي يمكنني:
• 💬 الإجابة على أسئلتك
• 📝 تلخيص التقارير
• 🧠 التعلم من محادثاتنا
• 📊 عرض سجل المحادثات
• 📋 إدارة التقارير والأقسام

📚 **الأوامر العامة:**
/help - عرض المساعدة
/summary - تلخيص تقاريرك (متاح للجميع)
/history - عرض آخر 5 محادثات
/stats - إحصائيات الاستخدام
/clear - مسح ذاكرة المحادثة

📊 **نظام التقارير:**
/register - التسجيل في النظام
/my_role - عرض دورك وصلاحياتك
/create_report - إنشاء تقرير جديد
/my_reports - عرض تقاريرك
/department_reports - عرض تقارير القسم (للمدراء)
/create_cumulative - إنشاء تقرير تجميعي (للمدراء الأعلى)
/approve_report - الموافقة على تقرير (للمدراء)
/search - البحث في التقارير

اكتب أي سؤال وسأجيب عليه! 🤖
    """

    await update.message.reply_text(welcome_message)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض إحصائيات الاستخدام"""
    user_id = update.effective_user.id

    # جلب الإحصائيات من قاعدة البيانات
    import sqlite3
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()

    # عدد المحادثات
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (user_id,))
    total_conversations = cursor.fetchone()[0]

    # عدد الملخصات
    cursor.execute("SELECT COUNT(*) FROM summaries WHERE user_id = ?", (user_id,))
    total_summaries = cursor.fetchone()[0]

    # تاريخ أول محادثة
    cursor.execute("SELECT MIN(timestamp) FROM conversations WHERE user_id = ?", (user_id,))
    first_chat = cursor.fetchone()[0]

    conn.close()

    stats_text = f"""
📊 **إحصائياتك:**

• 💬 عدد المحادثات: {total_conversations}
• 📝 عدد الملخصات: {total_summaries}
• 📅 أول محادثة: {first_chat if first_chat else 'لا يوجد'}
• 🤖 النموذج: {config.GEMINI_MODEL}
• 🧠 عدد المحادثات المحفوظة: {total_conversations}
    """

    await update.message.reply_text(stats_text, parse_mode='Markdown')


