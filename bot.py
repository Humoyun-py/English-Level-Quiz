import asyncio
import logging
import sqlite3
import json
import csv
import io
from enum import Enum
from datetime import datetime, date
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton,
    BufferedInputFile
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ================== ENUMS ==================
class EnglishLevel(Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"

# ================== DATABASE ==================
def init_db():
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()

    # Users
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        username TEXT,
        full_name TEXT,
        joined_date TEXT
    )''')

    # Levels
    c.execute('''CREATE TABLE IF NOT EXISTS english_levels (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT UNIQUE,
        description TEXT
    )''')

    # Questions
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level_id INTEGER,
        question_text TEXT,
        options TEXT,  -- JSON array
        correct_answer INTEGER,  -- index of correct option
        FOREIGN KEY (level_id) REFERENCES english_levels (id)
    )''')

    # Results
    c.execute('''CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        level TEXT,
        score INTEGER,
        total_questions INTEGER,
        wrong_answers TEXT,  -- JSON list of wrong question ids
        time_taken INTEGER,  -- seconds
        date TEXT,
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')

    # Banned users
    c.execute('''CREATE TABLE IF NOT EXISTS banned_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        reason TEXT,
        banned_date TEXT
    )''')

    # Question reports
    c.execute('''CREATE TABLE IF NOT EXISTS question_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER,
        user_id INTEGER,
        reason TEXT,
        report_date TEXT,
        FOREIGN KEY (question_id) REFERENCES questions (id),
        FOREIGN KEY (user_id) REFERENCES users (user_id)
    )''')

    # Daily bonus
    c.execute('''CREATE TABLE IF NOT EXISTS daily_bonus (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        date TEXT,
        claimed INTEGER DEFAULT 0,
        UNIQUE(user_id, date)
    )''')

    # User hints
    c.execute('''CREATE TABLE IF NOT EXISTS user_hints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        hints_count INTEGER DEFAULT 0
    )''')

    # Insert default levels if not exist
    levels = [
        ("A1", "Beginner - Basic phrases and vocabulary"),
        ("A2", "Elementary - Simple conversations"),
        ("B1", "Intermediate - Everyday language"),
        ("B2", "Upper Intermediate - Complex topics"),
        ("C1", "Advanced - Fluent and natural")
    ]
    for level, desc in levels:
        c.execute("INSERT OR IGNORE INTO english_levels (level, description) VALUES (?, ?)", (level, desc))

    # Insert sample questions if not exist
    sample_questions = {
        "A1": [
            ("What is your name?", ["My name is John", "I am fine", "Thank you", "Goodbye"], 0),
            ("How are you?", ["I am fine", "My name is Anna", "Thank you", "Hello"], 0),
            ("What color is the sky?", ["Blue", "Red", "Green", "Yellow"], 0),
            ("How many fingers do you have?", ["10", "5", "20", "15"], 0),
            ("What is this? (pointing to a book)", ["Book", "Pen", "Table", "Chair"], 0),
            ("Where is the door?", ["Here", "There", "Up", "Down"], 1),
            ("What time is it?", ["12 o'clock", "Monday", "Summer", "Rain"], 0),
            ("Do you like apples?", ["Yes", "No", "Maybe", "I don't know"], 0),
            ("What is your favorite color?", ["Red", "Book", "Dog", "Car"], 0),
            ("How old are you?", ["25", "Apple", "Blue", "Run"], 0),
            ("What do you eat for breakfast?", ["Bread", "Shoes", "Car", "Book"], 0),
            ("Where do you live?", ["In a house", "On the moon", "In a book", "With animals"], 0),
            ("What is the weather like?", ["Sunny", "Happy", "Fast", "Big"], 0),
            ("Can you swim?", ["Yes", "No", "Maybe", "I don't know"], 0),
            ("What animal is this? (cat)", ["Cat", "Dog", "Bird", "Fish"], 0),
        ],
        "A2": [
            ("What ___ you doing?", ["are", "is", "am", "be"], 0),
            ("I ___ to school every day.", ["go", "goes", "going", "went"], 0),
            ("She ___ a teacher.", ["is", "are", "am", "be"], 0),
            ("They ___ playing football.", ["are", "is", "am", "be"], 0),
            ("What did you ___ yesterday?", ["do", "does", "doing", "did"], 0),
            ("I have ___ brothers.", ["two", "to", "too", "tree"], 0),
            ("Where ___ you from?", ["are", "is", "am", "be"], 0),
            ("He ___ like pizza.", ["doesn't", "don't", "isn't", "aren't"], 1),
            ("What time ___ you wake up?", ["do", "does", "doing", "did"], 0),
            ("She can ___ very fast.", ["run", "runs", "running", "ran"], 0),
            ("We ___ to the park last weekend.", ["went", "go", "goes", "going"], 0),
            ("___ you speak English?", ["Do", "Does", "Doing", "Did"], 0),
            ("I ___ my homework now.", ["am doing", "do", "does", "did"], 0),
            ("They ___ in London.", ["live", "lives", "living", "lived"], 0),
            ("What ___ your hobby?", ["is", "are", "am", "be"], 0),
        ],
        "B1": [
            ("If I ___ rich, I would travel the world.", ["am", "were", "was", "be"], 1),
            ("I wish I ___ taller.", ["am", "were", "was", "be"], 1),
            ("She has been ___ for two hours.", ["waiting", "wait", "waits", "waited"], 0),
            ("By the time we arrive, the movie ___ .", ["will start", "starts", "started", "starting"], 0),
            ("I ___ to music while I study.", ["listen", "listens", "listening", "listened"], 0),
            ("He asked me where I ___ .", ["live", "lives", "lived", "living"], 0),
            ("If it rains tomorrow, we ___ the picnic.", ["cancel", "cancels", "canceling", "canceled"], 0),
            ("She ___ her homework yet.", ["hasn't finished", "doesn't finish", "isn't finishing", "didn't finish"], 0),
            ("I ___ in this city for 5 years.", ["have lived", "live", "lives", "lived"], 0),
            ("What would you do if you ___ a million dollars?", ["win", "won", "wins", "winning"], 0),
            ("They ___ when I called them.", ["were sleeping", "slept", "sleep", "sleeping"], 0),
            ("I regret ___ that decision.", ["making", "make", "makes", "made"], 0),
            ("She is used to ___ up early.", ["getting", "get", "gets", "got"], 0),
            ("If I had known, I ___ you.", ["would tell", "tell", "told", "telling"], 0),
            ("He ___ his car repaired.", ["had", "has", "have", "having"], 0),
        ],
        "B2": [
            ("Had I known about the party, I ___ there.", ["would go", "would have gone", "went", "go"], 1),
            ("The book ___ by the time you finish it.", ["will have been read", "will read", "reads", "reading"], 0),
            ("She accused him of ___ her.", ["lying", "lie", "lies", "lied"], 0),
            ("I object ___ treated like this.", ["to being", "to be", "being", "be"], 0),
            ("Under no circumstances ___ I agree to that.", ["would", "will", "do", "am"], 0),
            ("The manager demanded that the report ___ immediately.", ["be submitted", "is submitted", "was submitted", "submit"], 0),
            ("It was only when I got home that I realized I ___ my keys.", ["had left", "left", "leave", "leaving"], 0),
            ("She is not accustomed ___ in such cold weather.", ["to working", "to work", "working", "work"], 0),
            ("The proposal was rejected on the grounds that it ___ too expensive.", ["was", "is", "were", "be"], 0),
            ("I would rather you ___ here now.", ["are not", "were not", "not be", "not are"], 0),
            ("By the time the police arrived, the thief ___ .", ["had escaped", "escaped", "escapes", "escaping"], 0),
            ("He prides himself ___ being honest.", ["on", "in", "at", "for"], 0),
            ("The committee consists ___ five members.", ["of", "in", "at", "on"], 0),
            ("She succeeded ___ passing the exam.", ["in", "on", "at", "for"], 0),
            ("I am looking forward ___ you soon.", ["to seeing", "to see", "seeing", "see"], 0),
        ],
        "C1": [
            ("Notwithstanding the difficulties, the project ___ successfully.", ["proceeded", "proceeds", "proceeding", "proceed"], 0),
            ("His explanation was so convoluted that I could barely ___ it.", ["comprehend", "comprehends", "comprehending", "comprehended"], 0),
            ("The politician's rhetoric was replete ___ clichés.", ["with", "in", "at", "on"], 0),
            ("She has an uncanny ability to ___ people's thoughts.", ["discern", "discerns", "discerning", "discerned"], 0),
            ("The CEO's decision was predicated ___ inaccurate data.", ["on", "in", "at", "with"], 0),
            ("His proposal was met with widespread ___ from the board.", ["acclaim", "acclaims", "acclaiming", "acclaimed"], 0),
            ("The archaeologist unearthed artifacts that ___ back centuries.", ["date", "dates", "dating", "dated"], 0),
            ("The treaty was signed amid much ___ and ceremony.", ["pomp", "pomps", "pomping", "pomped"], 0),
            ("She is renowned for her ___ in diplomatic negotiations.", ["acumen", "acumens", "acumening", "acumened"], 0),
            ("The novel's plot is ___ with intrigue and suspense.", ["imbued", "imbues", "imbuing", "imbue"], 0),
            ("His argument was so specious that it ___ no scrutiny.", ["withstood", "withstands", "withstanding", "withstand"], 0),
            ("The philanthropist bequeathed a substantial ___ to charity.", ["bequest", "bequests", "bequesting", "bequested"], 0),
            ("The scientist's hypothesis was ___ by empirical evidence.", ["corroborated", "corroborates", "corroborating", "corroborate"], 0),
            ("She exhibited remarkable ___ in the face of adversity.", ["fortitude", "fortitudes", "fortituding", "fortituded"], 0),
            ("The artist's work is characterized by its ___ and originality.", ["audacity", "audacities", "audacitying", "audacityed"], 0),
        ]
    }

    for level, questions in sample_questions.items():
        c.execute("SELECT id FROM english_levels WHERE level = ?", (level,))
        level_id = c.fetchone()[0]
        for q_text, options, correct in questions:
            # Check if question already exists
            c.execute("SELECT id FROM questions WHERE level_id = ? AND question_text = ?", (level_id, q_text))
            if not c.fetchone():
                c.execute("INSERT INTO questions (level_id, question_text, options, correct_answer) VALUES (?, ?, ?, ?)",
                          (level_id, q_text, json.dumps(options), correct))

    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = c.fetchone()
    conn.close()
    return user

def add_user(user_id, username, full_name):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, joined_date) VALUES (?, ?, ?, datetime('now'))",
              (user_id, username, full_name))
    conn.commit()
    conn.close()

def get_questions(level=None):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    if level:
        c.execute("""
            SELECT q.id, q.question_text, q.options, q.correct_answer, l.level
            FROM questions q
            JOIN english_levels l ON q.level_id = l.id
            WHERE l.level = ?
            ORDER BY q.id
        """, (level,))
    else:
        c.execute("""
            SELECT q.id, q.question_text, q.options, q.correct_answer, l.level
            FROM questions q
            JOIN english_levels l ON q.level_id = l.id
            ORDER BY l.id, q.id
        """)
    questions = c.fetchall()
    conn.close()
    return questions

def add_question(level, question_text, options, correct_answer):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT id FROM english_levels WHERE level = ?", (level,))
    level_id = c.fetchone()
    if level_id:
        c.execute("INSERT INTO questions (level_id, question_text, options, correct_answer) VALUES (?, ?, ?, ?)",
                  (level_id[0], question_text, json.dumps(options), correct_answer))
        conn.commit()
    conn.close()

def save_result(user_id, level, score, total, wrong_answers=None, time_taken=0):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    wrong_json = json.dumps(wrong_answers) if wrong_answers else None
    c.execute("INSERT INTO results (user_id, level, score, total_questions, wrong_answers, time_taken, date) VALUES (?, ?, ?, ?, ?, ?, datetime('now'))",
              (user_id, level, score, total, wrong_json, time_taken))
    conn.commit()
    conn.close()

def get_user_results(user_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT level, score, total_questions, date FROM results WHERE user_id = ? ORDER BY date DESC LIMIT 5",
              (user_id,))
    results = c.fetchall()
    conn.close()
    return results

def is_banned(user_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT id FROM banned_users WHERE user_id = ?", (user_id,))
    banned = c.fetchone()
    conn.close()
    return banned is not None

def unban_user(user_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("DELETE FROM banned_users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def ban_user(user_id, reason):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO banned_users (user_id, reason, banned_date) VALUES (?, ?, datetime('now'))",
              (user_id, reason))
    conn.commit()
    conn.close()


def report_question(question_id, user_id, reason):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("INSERT INTO question_reports (question_id, user_id, reason, report_date) VALUES (?, ?, ?, datetime('now'))",
              (question_id, user_id, reason))
    conn.commit()
    conn.close()

def get_daily_bonus(user_id):
    today = date.today().isoformat()
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT claimed FROM daily_bonus WHERE user_id = ? AND date = ?", (user_id, today))
    claimed = c.fetchone()
    if claimed:
        conn.close()
        return claimed[0]
    # Not claimed, give bonus
    c.execute("INSERT INTO daily_bonus (user_id, date, claimed) VALUES (?, ?, 1)", (user_id, today))
    # Give hints
    c.execute("INSERT INTO user_hints (user_id, hints_count) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET hints_count = hints_count + 1",
              (user_id,))
    conn.commit()
    conn.close()
    return 1

def get_user_hints(user_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT hints_count FROM user_hints WHERE user_id = ?", (user_id,))
    hints = c.fetchone()
    conn.close()
    return hints[0] if hints else 0

def use_hint(user_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("UPDATE user_hints SET hints_count = hints_count - 1 WHERE user_id = ? AND hints_count > 0", (user_id,))
    conn.commit()
    conn.close()

def get_leaderboard():
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("""
        SELECT u.full_name, r.level, (r.score * 100.0 / r.total_questions) as percentage
        FROM results r
        JOIN users u ON r.user_id = u.user_id
        ORDER BY percentage DESC
        LIMIT 10
    """)
    leaderboard = c.fetchall()
    conn.close()
    return leaderboard

def generate_certificate(user_id, level, score, total, date_str):
    if not PDF_AVAILABLE:
        return None

    user = get_user(user_id)
    if not user:
        return None

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 24)
    c.drawCentredString(width/2, height-100, "English Level Certificate")

    # Content
    c.setFont("Helvetica", 14)
    c.drawString(100, height-150, f"This certifies that")
    c.setFont("Helvetica-Bold", 18)
    c.drawString(100, height-180, user[3])  # full_name
    c.setFont("Helvetica", 14)
    c.drawString(100, height-210, f"has successfully completed the English Level Test")
    c.drawString(100, height-230, f"and achieved level: {level}")
    c.drawString(100, height-250, f"Score: {score}/{total} ({int(score*100/total)}%)")
    c.drawString(100, height-270, f"Date: {date_str}")

    c.save()
    buffer.seek(0)
    return buffer

def delete_question(question_id):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE id = ?", (question_id,))
    conn.commit()
    conn.close()

def update_question(question_id, q_text, options, correct):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("UPDATE questions SET question_text = ?, options = ?, correct_answer = ? WHERE id = ?",
              (q_text, json.dumps(options), correct, question_id))
    conn.commit()
    conn.close()

def import_questions_from_csv(csv_content):
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    reader = csv.DictReader(io.StringIO(csv_content))
    for row in reader:
        level = row['level']
        q_text = row['question']
        options = [row['option1'], row['option2'], row['option3'], row['option4']]
        correct = int(row['correct']) - 1  # assuming 1-4 in CSV
        c.execute("SELECT id FROM english_levels WHERE level = ?", (level,))
        level_id = c.fetchone()
        if level_id:
            c.execute("INSERT INTO questions (level_id, question_text, options, correct_answer) VALUES (?, ?, ?, ?)",
                      (level_id[0], q_text, json.dumps(options), correct))
    conn.commit()
    conn.close()

# ================== FSM STATES ==================
class QuizStates(StatesGroup):
    taking_quiz = State()
    waiting_answer = State()

class AdminStates(StatesGroup):
    adding_question = State()
    waiting_level = State()
    waiting_question = State()
    waiting_options = State()
    waiting_correct = State()
    editing_question = State()
    waiting_edit_text = State()
    waiting_edit_options = State()
    waiting_edit_correct = State()
    importing_csv = State()
    waiting_delete_id = State()
    waiting_ban_user_id = State()
    waiting_ban_reason = State()
    waiting_report_reason = State()
    waiting_edit_id = State()
    waiting_unban_user_id = State()


BOT_TOKEN = "8537444288:AAF0YhdjR8eoZDtvTsYX6BBACJFDWgNe1Ys"
ADMIN_IDS = [7782143104]  # Admin ID larni bu yerga qo'shing
# ================== BOT SETUP ==================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# ================== KEYBOARDS ==================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Test boshlash"), KeyboardButton(text="🏆 Reyting")],
            [KeyboardButton(text="📊 Natijalarim"), KeyboardButton(text="🎁 Kunlik bonus")],
            [KeyboardButton(text="ℹ️ Ma'lumot")]
        ],
        resize_keyboard=True
    )

def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Savol qo'shish", callback_data="admin_add_question")],
        [InlineKeyboardButton(text="📋 Savollarni ko'rish", callback_data="admin_view_questions")],
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="🗑 Savolni o'chirish", callback_data="admin_delete_question")],
        [InlineKeyboardButton(text="✏️ Savolni tahrirlash", callback_data="admin_edit_question")],
        [InlineKeyboardButton(text="📥 CSV import", callback_data="admin_import_csv")],
        [InlineKeyboardButton(text="🚫 Ban foydalanuvchi", callback_data="admin_ban_user")],
        [InlineKeyboardButton(text="✅ Unban foydalanuvchi", callback_data="admin_unban_user")],
        [InlineKeyboardButton(text="📋 Shikoyatlar", callback_data="admin_view_reports")]
    ])

def get_level_keyboard():
    levels = [level.value for level in EnglishLevel]
    keyboard = []
    for i in range(0, len(levels), 2):
        row = [InlineKeyboardButton(text=levels[i], callback_data=f"start_quiz_{levels[i]}")]
        if i + 1 < len(levels):
            row.append(InlineKeyboardButton(text=levels[i+1], callback_data=f"start_quiz_{levels[i+1]}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="🎯 To'liq test", callback_data="start_quiz_full")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_answer_keyboard(options, question_id, has_hint=False):
    keyboard = []
    for i, option in enumerate(options):
        keyboard.append([InlineKeyboardButton(text=option, callback_data=f"answer_{i}")])
    # Add hint and report buttons
    bottom_row = []
    if has_hint:
        bottom_row.append(InlineKeyboardButton(text="💡 Hint", callback_data=f"hint_{question_id}"))
    bottom_row.append(InlineKeyboardButton(text="🚩 Shikoyat", callback_data=f"report_{question_id}"))
    keyboard.append(bottom_row)
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# ================== HANDLERS ==================

# Start command
@router.message(CommandStart())
async def start_command(message: Message):
    if is_banned(message.from_user.id):
        await message.answer("❌ Siz ban qilingansiz.")
        return
    add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    text = "🇬🇧 English Level Quiz Bot\n\nSalom! Bu bot sizning Ingliz tili darajangizni aniqlash uchun.\n\nQuyidagi tugmalardan foydalaning:"
    await message.answer(text, reply_markup=get_main_keyboard())

# Main menu
@router.message(F.text == "📝 Test boshlash")
async def start_quiz_menu(message: Message):
    text = "Qaysi darajada test topshirmoqchisiz?\n\nYoki to'liq testni tanlang:"
    await message.answer(text, reply_markup=get_level_keyboard())

@router.message(F.text == "📊 Natijalarim")
async def show_results(message: Message):
    results = get_user_results(message.from_user.id)
    if not results:
        await message.answer("Sizda hali natijalar yo'q.")
        return

    text = "📊 Sizning oxirgi natijalaringiz:\n\n"
    for level, score, total, date in results:
        percentage = int((score / total) * 100)
        text += f"📅 {date}\n🎯 Daraja: {level}\n✅ {score}/{total} ({percentage}%)\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main")]])
    await message.answer(text, reply_markup=keyboard)

@router.message(F.text == "🏆 Reyting")
async def show_leaderboard(message: Message):
    leaderboard = get_leaderboard()
    if not leaderboard:
        await message.answer("Hali hech kim test topshirmagan.")
        return

    text = "🏆 TOP 10 Reyting:\n\n"
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    for i, (name, level, percentage) in enumerate(leaderboard, 1):
        medal = medals[i-1] if i <= len(medals) else f"{i}."
        text += f"{medal} {name} - {level} ({int(percentage)}%)\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main")]])
    await message.answer(text, reply_markup=keyboard)

@router.message(F.text == "🎁 Kunlik bonus")
async def claim_daily_bonus(message: Message):
    claimed = get_daily_bonus(message.from_user.id)
    if claimed:
        hints = get_user_hints(message.from_user.id)
        await message.answer(f"✅ Bugun bonus allaqachon olingan!\n💡 Sizda {hints} ta hint bor.")
    else:
        await message.answer("🎉 Kunlik bonus olindi! +1 Hint qo'shildi.")
        # Refresh keyboard or something
@router.message(F.text == "ℹ️ Ma'lumot")
async def show_info(message: Message):
    text = """🇬🇧 English Level Quiz Bot

🎯 Maqsad: Ingliz tili darajangizni aniqlash (A1-C1)

📚 Darajalar:
• A1 - Beginner
• A2 - Elementary  
• B1 - Intermediate
• B2 - Upper Intermediate
• C1 - Advanced

❓ Qanday ishlaydi:
1. Testni boshlang
2. Savollarga javob bering
3. Natijangizni ko'ring

👨‍💼 Admin: Savol qo'shish va tahrirlash"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main")]])
    await message.answer(text, reply_markup=keyboard)

# Quiz callbacks
@router.callback_query(F.data.startswith("start_quiz_"))
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    level = callback.data.replace("start_quiz_", "")
    if level == "full":
        questions = get_questions()
    else:
        questions = get_questions(level)

    if not questions:
        await callback.answer("Bu darajada savollar yo'q.", show_alert=True)
        return

    await state.update_data(
        questions=questions,
        current=0,
        score=0,
        level=level,
        lives=3,
        wrong_answers=[],
        start_time=datetime.now(),
        user_id=callback.from_user.id
    )
    await state.set_state(QuizStates.taking_quiz)

    await ask_question(callback.message, questions[0], state)

@router.callback_query(F.data.startswith("answer_"), QuizStates.taking_quiz)
async def handle_answer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    questions = data['questions']
    current = data['current']
    score = data['score']
    lives = data['lives']
    wrong_answers = data['wrong_answers']

    answer_idx = int(callback.data.replace("answer_", ""))
    correct = questions[current][3]  # correct_answer

    if answer_idx == correct:
        score += 1
    else:
        lives -= 1
        wrong_answers.append(questions[current])  # store the wrong question

    current += 1
    await state.update_data(current=current, score=score, lives=lives, wrong_answers=wrong_answers)

    if lives <= 0:
        await finish_quiz(callback, state, score, len(questions), early_end=True)
    elif current >= len(questions):
        await finish_quiz(callback, state, score, len(questions))
    else:
        await ask_question(callback.message, questions[current], state)

async def ask_question(message: Message, question, state):
    q_id, q_text, options_json, correct, level = question
    options = json.loads(options_json)
    data = await state.get_data()
    current = data['current']
    total_q = len(data['questions'])
    lives = data['lives']
    has_hint = get_user_hints(data['user_id']) > 0

    progress = f"{'█' * (current+1)}{'░' * (total_q - current - 1)}"
    keyboard = get_answer_keyboard(options, q_id, has_hint)
    text = f"❓ {q_text}\n\n📊 Progress: {current+1}/{total_q}\n{progress}\n❤️ Lives: {lives}\n\nDaraja: {level}"

    await message.edit_text(text, reply_markup=keyboard)

async def finish_quiz(callback: CallbackQuery, state: FSMContext, score, total, early_end=False):
    data = await state.get_data()
    level = data.get('level', 'Full')
    wrong_answers = data.get('wrong_answers', [])
    start_time = data.get('start_time')
    time_taken = int((datetime.now() - start_time).total_seconds()) if start_time else 0

    # Determine level based on score
    percentage = (score / total) * 100
    if percentage >= 90:
        determined_level = "C1"
    elif percentage >= 80:
        determined_level = "B2"
    elif percentage >= 70:
        determined_level = "B1"
    elif percentage >= 60:
        determined_level = "A2"
    else:
        determined_level = "A1"

    save_result(callback.from_user.id, determined_level, score, total, wrong_answers, time_taken)

    text = f"""🎉 Test tugadi!

📊 Natija: {score}/{total} ({int(percentage)}%)
🎯 Aniqlangan daraja: {determined_level}
⏱️ Vaqt: {time_taken} soniya
❤️ Qolgan hayotlar: {data.get('lives', 0)}

🇬🇧 Sizning Ingliz tili darajangiz: {determined_level}"""

    if wrong_answers:
        text += "\n\n❌ Xato javoblar:\n"
        for q in wrong_answers[:5]:  # show first 5
            options = json.loads(q[2])
            correct_opt = options[q[3]]
            text += f"• {q[1][:30]}... → {correct_opt}\n"

    # Certificate
    if PDF_AVAILABLE and percentage >= 60:
        pdf_buffer = generate_certificate(callback.from_user.id, determined_level, score, total, datetime.now().strftime("%Y-%m-%d"))
        if pdf_buffer:
            await callback.message.answer_document(
                BufferedInputFile(pdf_buffer.getvalue(), filename="certificate.pdf"),
                caption="📄 Sertifikatingiz tayyor!"
            )

    # Retake button
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔁 Qayta test", callback_data=f"start_quiz_{level}")],
        [InlineKeyboardButton(text="⬅️ Asosiy menyu", callback_data="back_to_main")]
    ])

    await callback.message.edit_text(text, reply_markup=keyboard)
    await state.clear()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    text = "🇬🇧 English Level Quiz Bot\n\nSalom! Bu bot sizning Ingliz tili darajangizni aniqlash uchun.\n\nQuyidagi tugmalardan foydalaning:"
    await callback.message.answer(text, reply_markup=get_main_keyboard())
    await callback.answer()

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.edit_text("👨‍💼 Admin panel:", reply_markup=get_admin_keyboard())

@router.callback_query(F.data.startswith("hint_"))
async def use_hint_callback(callback: CallbackQuery):
    question_id = int(callback.data.replace("hint_", ""))
    user_id = callback.from_user.id
    if get_user_hints(user_id) > 0:
        use_hint(user_id)
        await callback.answer("💡 Hint ishlatildi! To'g'ri javob ko'rsatildi.", show_alert=True)
        # Optionally, edit the message to show the correct answer or remove options
    else:
        await callback.answer("Hint yo'q!", show_alert=True)

@router.callback_query(F.data.startswith("report_"))
async def report_question_callback(callback: CallbackQuery, state: FSMContext):
    question_id = int(callback.data.replace("report_", ""))
    await state.update_data(report_question_id=question_id)
    await callback.message.edit_text("Shikoyat sababini yozing:")
    await state.set_state(AdminStates.waiting_report_reason)

@router.message(AdminStates.waiting_report_reason)
async def enter_report_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    question_id = data['report_question_id']
    reason = message.text
    report_question(question_id, message.from_user.id, reason)
    await message.answer("Shikoyat yuborildi!")
    await state.clear()

# Admin handlers
@router.message(Command("admin"))
async def admin_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Siz admin emassiz.")
        return

    await message.answer("👨‍💼 Admin panel:", reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_add_question")
async def admin_add_question(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return

    levels = [level.value for level in EnglishLevel]
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=level, callback_data=f"add_q_level_{level}")] for level in levels
    ] + [[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])

    await callback.message.edit_text("Qaysi daraja uchun savol qo'shmoqchisiz?", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_level)

@router.callback_query(F.data.startswith("add_q_level_"), AdminStates.waiting_level)
async def admin_select_level(callback: CallbackQuery, state: FSMContext):
    level = callback.data.replace("add_q_level_", "")
    await state.update_data(level=level)

    await callback.message.edit_text("Savolni yozing (masalan: What is your name?):")
    await state.set_state(AdminStates.waiting_question)

@router.message(AdminStates.waiting_question)
async def admin_enter_question(message: Message, state: FSMContext):
    await state.update_data(question=message.text)
    await message.answer("Variantlarni vergul bilan ajratib yozing (masalan: Apple, Banana, Orange, Grape):")
    await state.set_state(AdminStates.waiting_options)

@router.message(AdminStates.waiting_options)
async def admin_enter_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(',')]
    if len(options) < 2:
        await message.answer("Kamida 2 ta variant bo'lishi kerak!")
        return

    await state.update_data(options=options)
    numbered_options = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
    await message.answer(f"Variantlar:\n{numbered_options}\n\nTo'g'ri javob raqamini yozing (1-{len(options)}):")
    await state.set_state(AdminStates.waiting_correct)

@router.message(AdminStates.waiting_correct)
async def admin_enter_correct(message: Message, state: FSMContext):
    try:
        correct = int(message.text) - 1
        data = await state.get_data()
        options = data['options']

        if 0 <= correct < len(options):
            add_question(data['level'], data['question'], options, correct)
            await message.answer("✅ Savol muvaffaqiyatli qo'shildi!")
            await state.clear()
        else:
            await message.answer(f"To'g'ri raqam 1-{len(options)} orasida bo'lishi kerak!")
    except ValueError:
        await message.answer("Raqam yozing!")

@router.callback_query(F.data == "admin_view_questions")
async def admin_view_questions(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    questions = get_questions()
    if not questions:
        await callback.message.edit_text("Savollar yo'q.")
        return

    text = "📋 Barcha savollar:\n\n"
    for q_id, q_text, options_json, correct, level in questions[:20]:  # Limit to 20
        options = json.loads(options_json)
        text += f"🎯 {level}: {q_text[:50]}...\n✅ {options[correct]}\n\n"

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return

    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    users_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM questions")
    questions_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM results")
    results_count = c.fetchone()[0]
    conn.close()

    text = f"""📊 Statistika:

👥 Foydalanuvchilar: {users_count}
❓ Savollar: {questions_count}
📈 Natijalar: {results_count}"""

    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_delete_question")
async def admin_delete_question(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text("O'chiriladigan savol ID sini yozing:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_delete_id)

@router.message(AdminStates.waiting_delete_id)
async def delete_question_id(message: Message, state: FSMContext):
    try:
        q_id = int(message.text)
        delete_question(q_id)
        await message.answer("Savol o'chirildi!")
    except ValueError:
        await message.answer("Noto'g'ri ID")
    await state.clear()

@router.message(AdminStates.waiting_edit_id)
async def edit_question_id(message: Message, state: FSMContext):
    try:
        q_id = int(message.text)
        conn = sqlite3.connect('english_quiz.db')
        c = conn.cursor()
        c.execute("SELECT question_text, options, correct_answer FROM questions WHERE id = ?", (q_id,))
        question = c.fetchone()
        conn.close()
        if not question:
            await message.answer("Bunday savol topilmadi!")
            await state.clear()
            return
        q_text, options_json, correct = question
        options = json.loads(options_json)
        await state.update_data(edit_q_id=q_id, current_options=options, current_correct=correct)
        numbered_options = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
        text = f"Joriy savol:\n{q_text}\n\nVariantlar:\n{numbered_options}\n\nTo'g'ri javob: {correct+1}\n\nYangi savol matnini yozing:"
        await message.answer(text)
        await state.set_state(AdminStates.waiting_edit_text)
    except ValueError:
        await message.answer("Noto'g'ri ID")

@router.message(AdminStates.waiting_edit_text)
async def edit_question_text(message: Message, state: FSMContext):
    await state.update_data(edit_q_text=message.text)
    await message.answer("Yangi variantlarni vergul bilan ajratib yozing:")
    await state.set_state(AdminStates.waiting_edit_options)

@router.message(AdminStates.waiting_edit_options)
async def edit_question_options(message: Message, state: FSMContext):
    options = [opt.strip() for opt in message.text.split(',')]
    if len(options) < 2:
        await message.answer("Kamida 2 ta variant bo'lishi kerak!")
        return
    await state.update_data(edit_options=options)
    numbered_options = "\n".join(f"{i+1}. {opt}" for i, opt in enumerate(options))
    await message.answer(f"Yangi variantlar:\n{numbered_options}\n\nTo'g'ri javob raqamini yozing (1-{len(options)}):")
    await state.set_state(AdminStates.waiting_edit_correct)

@router.message(AdminStates.waiting_edit_correct)
async def edit_question_correct(message: Message, state: FSMContext):
    try:
        correct = int(message.text) - 1
        data = await state.get_data()
        options = data['edit_options']
        if 0 <= correct < len(options):
            update_question(data['edit_q_id'], data['edit_q_text'], options, correct)
            await message.answer("✅ Savol muvaffaqiyatli tahrirlandi!")
            await state.clear()
        else:
            await message.answer(f"To'g'ri raqam 1-{len(options)} orasida bo'lishi kerak!")
    except ValueError:
        await message.answer("Raqam yozing!")

@router.callback_query(F.data == "admin_edit_question")
async def admin_edit_question(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text("Tahrirlanadigan savol ID sini yozing:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_edit_id)

@router.callback_query(F.data == "admin_import_csv")
async def admin_import_csv(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text("CSV kontentini yuboring (format: level,question,option1,option2,option3,option4,correct):", reply_markup=keyboard)
    await state.set_state(AdminStates.importing_csv)

@router.message(AdminStates.importing_csv)
async def import_csv_content(message: Message, state: FSMContext):
    csv_content = message.text
    try:
        import_questions_from_csv(csv_content)
        await message.answer("CSV import muvaffaqiyatli!")
    except Exception as e:
        await message.answer(f"Xatolik: {str(e)}")
    await state.clear()

@router.callback_query(F.data == "admin_ban_user")
async def admin_ban_user(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text("Ban qilinadigan foydalanuvchi username yoki ID sini yozing:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_ban_user_id)

@router.callback_query(F.data == "admin_unban_user")
async def admin_unban_user(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text("Unban qilinadigan foydalanuvchi username yoki ID sini yozing:", reply_markup=keyboard)
    await state.set_state(AdminStates.waiting_unban_user_id)

@router.message(AdminStates.waiting_ban_user_id)
async def ban_user_id(message: Message, state: FSMContext):
    input_text = message.text.strip()
    if not input_text:
        await message.answer("Username yoki ID bo'sh bo'lishi mumkin emas!")
        return

    user_id = None
    # Try to parse as ID first
    try:
        user_id = int(input_text)
    except ValueError:
        # Not a number, treat as username
        username = input_text
        conn = sqlite3.connect('english_quiz.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user:
            user_id = user[0]
        else:
            await message.answer("Bunday username topilmadi!")
            return

    # If we have user_id from parsing or query
    if user_id:
        await state.update_data(ban_user_id=user_id)
        await message.answer("Ban sababini yozing:")
        await state.set_state(AdminStates.waiting_ban_reason)
    else:
        await message.answer("Foydalanuvchi topilmadi!")

@router.message(AdminStates.waiting_ban_reason)
async def ban_user_reason(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data['ban_user_id']
    reason = message.text
    ban_user(user_id, reason)
    await message.answer("Foydalanuvchi ban qilindi!")
    await state.clear()

@router.message(AdminStates.waiting_unban_user_id)
async def unban_user_id(message: Message, state: FSMContext):
    input_text = message.text.strip()
    if not input_text:
        await message.answer("Username yoki ID bo'sh bo'lishi mumkin emas!")
        return

    user_id = None
    # Try to parse as ID first
    try:
        user_id = int(input_text)
    except ValueError:
        # Not a number, treat as username
        username = input_text
        conn = sqlite3.connect('english_quiz.db')
        c = conn.cursor()
        c.execute("SELECT user_id FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user:
            user_id = user[0]
        else:
            await message.answer("Bunday username topilmadi!")
            return

    # If we have user_id from parsing or query
    if user_id:
        unban_user(user_id)
        await message.answer("Foydalanuvchi unban qilindi!")
        await state.clear()
    else:
        await message.answer("Foydalanuvchi topilmadi!")

@router.callback_query(F.data == "admin_view_reports")
async def admin_view_reports(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    conn = sqlite3.connect('english_quiz.db')
    c = conn.cursor()
    c.execute("SELECT q.question_text, r.reason, u.full_name FROM question_reports r JOIN questions q ON r.question_id = q.id JOIN users u ON r.user_id = u.user_id")
    reports = c.fetchall()
    conn.close()
    if not reports:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
        await callback.message.edit_text("Shikoyatlar yo'q.", reply_markup=keyboard)
        return
    text = "📋 Shikoyatlar:\n\n"
    for q_text, reason, name in reports[:10]:
        text += f"❓ {q_text[:30]}...\n👤 {name}\n📝 {reason}\n\n"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_admin")]])
    await callback.message.edit_text(text, reply_markup=keyboard)

# ================== MAIN ==================
async def main():
    init_db()
    dp.include_router(router)
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())