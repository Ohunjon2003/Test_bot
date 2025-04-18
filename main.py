import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from openpyxl import Workbook
from datetime import datetime
import os
from telegram.ext import ApplicationBuilder, CommandHandler
TOKEN = os.getenv("TOKEN")

app = ApplicationBuilder().token(TOKEN).build()

MAIN_ADMIN_ID = 1762920259
MAIN_ADMIN_USERNAME = 'oxunjon_xamitjonov'

conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS admins (username TEXT PRIMARY KEY);
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS tests (key TEXT PRIMARY KEY, creator_username TEXT, questions TEXT, score_per_question INTEGER, created_at TEXT);
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS results (id INTEGER PRIMARY KEY AUTOINCREMENT, test_key TEXT, username TEXT, correct_count INTEGER, total INTEGER, total_score INTEGER, percentage REAL, details TEXT, created_at TEXT, full_name TEXT);
''')
conn.commit()

def back_button():
    return ReplyKeyboardMarkup([[KeyboardButton("⬅️ Orqaga")]], resize_keyboard=True)

def main_menu(user_id, username):
    cursor.execute("SELECT 1 FROM admins WHERE username = ?", (username,))
    is_admin = cursor.fetchone() or user_id == MAIN_ADMIN_ID
    buttons = [[InlineKeyboardButton("✅ Testga javob berish", callback_data="answer_test")]]
    if is_admin:
        buttons.insert(0, [InlineKeyboardButton("📝 Test yaratish", callback_data="create_test")])
        buttons.insert(1, [InlineKeyboardButton("📥 Excel export", callback_data="export_results")])
        buttons.insert(2, [InlineKeyboardButton("❌ Testni o'chirish", callback_data="delete_test")])
        if user_id == MAIN_ADMIN_ID:
            buttons.insert(3, [InlineKeyboardButton("➕ Admin qo'shish", callback_data="add_admin")])
            buttons.insert(4, [InlineKeyboardButton("👥 Adminlar ro'yxati", callback_data="list_admins")])
            buttons.insert(5, [InlineKeyboardButton("➖ Adminni o‘chirish", callback_data="remove_admin")])
            buttons.insert(6, [InlineKeyboardButton("📊 Statistika", callback_data="view_statistics")])
        else:
            buttons.insert(6, [InlineKeyboardButton("📋 Mening testlarim", callback_data="my_tests")])
            buttons.insert(7, [InlineKeyboardButton("📊 Statistika", callback_data="view_statistics")])
    buttons.append([InlineKeyboardButton("ℹ️ Yordam", callback_data="help")])
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.effective_user.username
    await update.message.reply_text("Assalomu alaykum, botga xush kelibsiz!", reply_markup=main_menu(update.effective_user.id, username))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username
    data = query.data

    if data == "view_statistics":
        if user_id == MAIN_ADMIN_ID:
            cursor.execute("""SELECT tests.creator_username, tests.key, COUNT(results.id), AVG(results.percentage)
                              FROM tests LEFT JOIN results ON tests.key = results.test_key
                              GROUP BY tests.key""")
            data_list = cursor.fetchall()
            text = "📊 To‘liq Statistika:\n"
            for row in data_list:
                text += f"👤 @{row[0]} | 🔑 {row[1]} | 🧑‍🎓 {row[2]} ta | O‘rtacha: {round(row[3] or 0,2)}%\n"
            await query.message.reply_text(text if data_list else "Hali testlar yaratib, natija to‘plangan emas.")
        else:
            cursor.execute("""SELECT test_key, COUNT(id), AVG(percentage) FROM results 
                              WHERE test_key IN (SELECT key FROM tests WHERE creator_username = ?)
                              GROUP BY test_key""", (username,))
            stats = cursor.fetchall()
            text = "📊 Siz yaratgan testlar statistikasi:\n"
            for row in stats:
                text += f"🔑 {row[0]} | 🧑‍🎓 {row[1]} ta | O‘rtacha: {round(row[2],2)}%\n"
            await query.message.reply_text(text if stats else "Siz hali test yaratmagansiz yoki natija yo‘q.")

    elif data == "my_tests":
        cursor.execute("SELECT key FROM tests WHERE creator_username = ?", (username,))
        test_list = cursor.fetchall()
        if test_list:
            await query.message.reply_text("📋 Siz yaratgan testlar:\n" + "\n".join(f"🔑 {i[0]}" for i in test_list))
        else:
            await query.message.reply_text("Siz hali test yaratmagansiz.")

    elif data == "answer_test":
        await query.message.reply_text("Test kalitini kiriting:", reply_markup=back_button())
        context.user_data['awaiting_test_key_for_answer'] = True

    elif data == "help":
        await query.message.reply_text(
            "Test tuzish, javob berish va natijalarni ko‘rish uchun botdan foydalaning.\n"
            "Testni faqat admin yaratishi mumkin.\n"
            f"Adminlik uchun @{MAIN_ADMIN_USERNAME} bilan bog‘laning.",
            reply_markup=back_button()
        )

    elif data == "create_test":
        cursor.execute("SELECT 1 FROM admins WHERE username = ?", (username,))
        if cursor.fetchone() or user_id == MAIN_ADMIN_ID:
            await query.message.reply_text("Test uchun kalit (parol) kiriting:", reply_markup=back_button())
            context.user_data['awaiting_test_key'] = True
        else:
            await query.message.reply_text(f"Siz test yaratish huquqiga ega emassiz! @{MAIN_ADMIN_USERNAME} ga murojaat qiling.")

    elif data == "export_results":
        cursor.execute("SELECT 1 FROM admins WHERE username = ?", (username,))
        if cursor.fetchone() or user_id == MAIN_ADMIN_ID:
            await query.message.reply_text("Qaysi test kaliti uchun natijalarni eksport qilmoqchisiz? Kalitni kiriting:", reply_markup=back_button())
            context.user_data['awaiting_export_key'] = True
        else:
            await query.message.reply_text("Faqat adminlar eksport qilishi mumkin!")

    elif data == "delete_test":
        cursor.execute("SELECT 1 FROM admins WHERE username = ?", (username,))
        if cursor.fetchone() or user_id == MAIN_ADMIN_ID:
            await query.message.reply_text("O'chirmoqchi bo'lgan test kalitini kiriting:", reply_markup=back_button())
            context.user_data['awaiting_delete_key'] = True
        else:
            await query.message.reply_text("Faqat admin testlarni o‘chira oladi!")

    elif data == "add_admin":
        if user_id == MAIN_ADMIN_ID:
            await query.message.reply_text("Yangi admin usernamesini '@' belgisisiz kiriting:", reply_markup=back_button())
            context.user_data['awaiting_new_admin'] = True
        else:
            await query.message.reply_text("Faqat asosiy admin admin qo‘sha oladi.")

    elif data == "remove_admin":
        if user_id == MAIN_ADMIN_ID:
            await query.message.reply_text("O‘chirmoqchi bo‘lgan admin usernamesini '@' belgisisiz kiriting:", reply_markup=back_button())
            context.user_data['awaiting_remove_admin'] = True
        else:
            await query.message.reply_text("Bu amal faqat asosiy admin uchun!")

    elif data == "list_admins":
        if user_id == MAIN_ADMIN_ID:
            cursor.execute("SELECT username FROM admins")
            admin_list = cursor.fetchall()
            text = "👥 Adminlar ro‘yxati:\n" + "\n".join("@" + a[0] for a in admin_list)
            await query.message.reply_text(text if admin_list else "Adminlar ro‘yxati bo‘sh.")
        else:
            await query.message.reply_text("Bu amal faqat asosiy admin uchun!")

async def ask_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    next_q = context.user_data['question_list'][0]
    await update.message.reply_text(f"{next_q}-savol javobini kiriting:", reply_markup=back_button())

async def finish_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    correct_answers = context.user_data['test_questions']
    user_answers = context.user_data['answers']
    correct = sum(1 for k, v in correct_answers.items() if user_answers.get(k, '').lower() == v.lower())
    total = len(correct_answers)
    score = correct * context.user_data['score_per_question']
    percentage = round((correct / total) * 100, 2)

    cursor.execute("""INSERT INTO results (test_key, username, correct_count, total, total_score, percentage, details, created_at, full_name) 
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                   (context.user_data['current_test_key'], update.effective_user.username, correct, total, score, percentage,
                    str(user_answers), datetime.now().strftime('%Y-%m-%d %H:%M'), context.user_data['full_name']))
    conn.commit()

    msg = f"✅ Test yakunlandi!\nTo‘g‘ri javoblar: {correct}/{total}\nUmumiy ball: {score}\nBajarganlik: {percentage}%\n"
    for q, correct_a in correct_answers.items():
        user_a = user_answers.get(q, "Hech narsa")
        status = "✅" if user_a.lower() == correct_a.lower() else f"❌ To‘g‘ri: {correct_a}"
        msg += f"{q}) Siz: {user_a} — {status}\n"

    await update.message.reply_text(msg, reply_markup=main_menu(update.effective_user.id, update.effective_user.username))
    context.user_data.clear()

async def export_results(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    cursor.execute("SELECT score_per_question FROM tests WHERE key = ?", (key.lower(),))
    test_info = cursor.fetchone()
    if not test_info:
        await update.message.reply_text("Bunday test topilmadi! Kalitni tekshiring.", reply_markup=back_button())
        return

    score_per_question = test_info[0]
    cursor.execute("SELECT * FROM results WHERE test_key = ?", (key.lower(),))
    results = cursor.fetchall()
    if not results:
        await update.message.reply_text("Bu test bo‘yicha natijalar topilmadi.", reply_markup=back_button())
        return

    wb = Workbook()
    ws = wb.active
    ws.append(["Test Kaliti", "Ism Familya", "Telegram Username", "To‘g‘ri javoblar", "Jami savollar", "Savol balli", "Umumiy ball", "Bajarganlik (%)", "Sana"])
    for row in results:
        ws.append([row[1], row[9], row[2], row[3], row[4], score_per_question, row[5], row[6], row[8]])
    file_path = f"results_{key}.xlsx"
    wb.save(file_path)
    await update.message.reply_document(document=open(file_path, "rb"))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username

    if text == "⬅️ Orqaga":
        await update.message.reply_text("Bosh menyu:", reply_markup=main_menu(user_id, username))
        context.user_data.clear()
        return
    if context.user_data.get('awaiting_remove_admin'):
        cursor.execute("DELETE FROM admins WHERE username = ?", (text,))
        conn.commit()
        await update.message.reply_text(f"Admin o‘chirildi: @{text}", reply_markup=main_menu(user_id, username))
        context.user_data.pop('awaiting_remove_admin', None)
        return

    if context.user_data.get('awaiting_new_admin'):
        cursor.execute("INSERT OR IGNORE INTO admins (username) VALUES (?)", (text,))
        conn.commit()
        await update.message.reply_text(f"Yangi admin qo‘shildi: @{text}")
        context.user_data.pop('awaiting_new_admin', None)
        return

    if context.user_data.get('awaiting_delete_key'):
        key = text.lower()
        cursor.execute("SELECT creator_username FROM tests WHERE key = ?", (key,))
        result = cursor.fetchone()
        if result:
            if username == result[0] or user_id == MAIN_ADMIN_ID:
                cursor.execute("DELETE FROM tests WHERE key = ?", (key,))
                conn.commit()
                await update.message.reply_text("Test muvaffaqiyatli o‘chirildi.", reply_markup=main_menu(user_id, username))
            else:
                await update.message.reply_text("Siz faqat o‘zingiz yaratgan testni o‘chira olasiz.", reply_markup=back_button())
        else:
            await update.message.reply_text("Bunday test topilmadi.", reply_markup=back_button())
        context.user_data.pop('awaiting_delete_key', None)
        return

    if context.user_data.get('awaiting_export_key'):
        await export_results(update, context, text)
        context.user_data.pop('awaiting_export_key', None)
        return

    if context.user_data.get('awaiting_test_key'):
        key = text.lower()
        cursor.execute("SELECT 1 FROM tests WHERE key = ?", (key,))
        if cursor.fetchone():
            await update.message.reply_text("Bu kalit allaqachon mavjud. Iltimos, boshqa kalit kiriting:", reply_markup=back_button())
            return
        context.user_data['creating_test'] = {'key': key}
        await update.message.reply_text("Har bir savol nechchi ballga tengligini kiriting:", reply_markup=back_button())
        context.user_data.pop('awaiting_test_key')
        context.user_data['awaiting_score'] = True
        return

    if context.user_data.get('awaiting_score'):
        if text.isdigit():
            context.user_data['creating_test']['score'] = int(text)
            await update.message.reply_text("Endi test javoblarini kiriting (\n1a\n2b\n3c...).", reply_markup=back_button())
            context.user_data.pop('awaiting_score')
            context.user_data['awaiting_questions'] = True
        else:
            await update.message.reply_text("Iltimos, faqat raqam kiriting!", reply_markup=back_button())
        return

    if context.user_data.get('awaiting_questions'):
        questions = {}
        for line in text.splitlines():
            line = line.strip()
            if len(line) < 2 or not line[:-1].isdigit() or not line[-1].isalpha():
                await update.message.reply_text("Xato! Namuna: 1a\n2b\n3c\n4d", reply_markup=back_button())
                return
            questions[line[:-1]] = line[-1].lower()
        context.user_data['creating_test']['questions'] = questions
        cursor.execute("INSERT INTO tests (key, creator_username, questions, score_per_question, created_at) VALUES (?, ?, ?, ?, ?)",
                       (context.user_data['creating_test']['key'], username, str(questions), context.user_data['creating_test']['score'], datetime.now().isoformat()))
        conn.commit()
        await update.message.reply_text("Test muvaffaqiyatli saqlandi!", reply_markup=main_menu(user_id, username))
        context.user_data.clear()
        return

    if context.user_data.get('awaiting_test_key_for_answer'):
        context.user_data['current_test_key'] = text.lower()
        cursor.execute("SELECT questions, score_per_question FROM tests WHERE key = ?", (text.lower(),))
        row = cursor.fetchone()
        if row:
            context.user_data['test_questions'] = eval(row[0])
            context.user_data['answers'] = {}
            context.user_data['score_per_question'] = row[1]
            context.user_data['question_list'] = list(context.user_data['test_questions'].keys())
            await update.message.reply_text("Ism va familyangizni kiriting (Masalan: Ali Valiyev):", reply_markup=back_button())
            context.user_data['awaiting_full_name'] = True
        else:
            await update.message.reply_text("Bunday test topilmadi!", reply_markup=back_button())
        context.user_data.pop('awaiting_test_key_for_answer', None)
        return

    if context.user_data.get('awaiting_full_name'):
        if not text.replace(" ", "").isalpha():
            await update.message.reply_text("Faqat harflardan iborat ism va familya kiriting!", reply_markup=back_button())
            return
        context.user_data['full_name'] = text.strip().lower()
        cursor.execute("SELECT 1 FROM results WHERE test_key = ? AND full_name = ?",
                       (context.user_data['current_test_key'], context.user_data['full_name']))
        if cursor.fetchone():
            await update.message.reply_text("Siz bu testni allaqachon bajargansiz!", reply_markup=main_menu(user_id, username))
            context.user_data.clear()
            return
        await ask_question(update, context)
        context.user_data.pop('awaiting_full_name', None)
        return

    if context.user_data.get('question_list'):
        current_q = context.user_data['question_list'].pop(0)
        context.user_data['answers'][current_q] = text.strip().lower()
        if context.user_data['question_list']:
            await ask_question(update, context)
        else:
            await finish_test(update, context)
        return

async def export_results(update: Update, context: ContextTypes.DEFAULT_TYPE, key: str):
    cursor.execute("SELECT score_per_question FROM tests WHERE key = ?", (key.lower(),))
    test_info = cursor.fetchone()
    if not test_info:
        await update.message.reply_text("Bunday kalitli test topilmadi! Kalitni tekshirib qayta kiriting.", reply_markup=back_button())
        return
    score_per_question = test_info[0]
    cursor.execute("SELECT * FROM results WHERE test_key = ?", (key.lower(),))
    results = cursor.fetchall()
    if not results:
        await update.message.reply_text("Bu test kaliti bo‘yicha hali natija yo‘q.", reply_markup=back_button())
        return
    wb = Workbook()
    ws = wb.active
    ws.append(["Test Kaliti", "Ism Familya", "Telegram Username", "To‘g‘ri javoblar", "Jami savollar", "Savol balli", "Umumiy ball", "Bajarganlik (%)", "Sana"])
    for row in results:
        ws.append([row[1], row[9], row[2], row[3], row[4], score_per_question, row[5], row[6], row[8]])
    file_path = f"results_{key}.xlsx"
    wb.save(file_path)
    await update.message.reply_document(document=open(file_path, "rb"))

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
