from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_cors import CORS
from functools import wraps
import sqlite3
import json
import hashlib
import secrets
from datetime import datetime, date
import io

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
CORS(app)

# ================== DATABASE FUNCTIONS ==================
def get_db_connection():
    conn = sqlite3.connect('english_quiz.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_web_users_table():
    """Initialize web users table for web app authentication"""
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS web_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        email TEXT,
        is_admin INTEGER DEFAULT 0,
        created_date TEXT
    )''')
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, password_hash):
    """Verify password against hash"""
    return hash_password(password) == password_hash

# ================== AUTH DECORATORS ==================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        
        conn = get_db_connection()
        user = conn.execute('SELECT is_admin FROM web_users WHERE id = ?', 
                           (session['user_id'],)).fetchone()
        conn.close()
        
        if not user or not user['is_admin']:
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# ================== ROUTES - PAGES ==================
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/quiz')
@login_required
def quiz_page():
    return render_template('quiz.html')

@app.route('/results')
@login_required
def results_page():
    return render_template('results.html')

@app.route('/leaderboard')
def leaderboard_page():
    return render_template('leaderboard.html')

@app.route('/admin')
@admin_required
def admin_page():
    return render_template('admin.html')

# ================== API - AUTH ==================
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    full_name = data.get('full_name')
    email = data.get('email')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    try:
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute('''INSERT INTO web_users (username, password_hash, full_name, email, created_date)
                     VALUES (?, ?, ?, ?, datetime('now'))''',
                  (username, password_hash, full_name, email))
        user_id = c.lastrowid
        conn.commit()
        
        # Also add to users table for results tracking
        c.execute('''INSERT OR IGNORE INTO users (user_id, username, full_name, joined_date)
                     VALUES (?, ?, ?, datetime('now'))''',
                  (user_id + 10000, username, full_name))  # Offset to avoid collision with Telegram IDs
        conn.commit()
        
        session['user_id'] = user_id
        session['username'] = username
        session['full_name'] = full_name
        
        return jsonify({
            'success': True,
            'user': {
                'id': user_id,
                'username': username,
                'full_name': full_name
            }
        })
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        conn.close()

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM web_users WHERE username = ?', (username,)).fetchone()
    conn.close()
    
    if not user or not verify_password(password, user['password_hash']):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['full_name'] = user['full_name']
    session['is_admin'] = user['is_admin']
    
    return jsonify({
        'success': True,
        'user': {
            'id': user['id'],
            'username': user['username'],
            'full_name': user['full_name'],
            'is_admin': user['is_admin']
        }
    })

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/session', methods=['GET'])
def check_session():
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session['username'],
                'full_name': session.get('full_name'),
                'is_admin': session.get('is_admin', 0)
            }
        })
    return jsonify({'authenticated': False})

# ================== API - QUIZ ==================
@app.route('/api/quiz/levels', methods=['GET'])
def get_levels():
    conn = get_db_connection()
    levels = conn.execute('SELECT * FROM english_levels').fetchall()
    conn.close()
    
    return jsonify([dict(level) for level in levels])

@app.route('/api/quiz/start', methods=['POST'])
@login_required
def start_quiz():
    data = request.json
    level = data.get('level')
    
    conn = get_db_connection()
    if level and level != 'full':
        questions = conn.execute('''
            SELECT q.id, q.question_text, q.options, q.correct_answer, l.level
            FROM questions q
            JOIN english_levels l ON q.level_id = l.id
            WHERE l.level = ?
            ORDER BY RANDOM()
        ''', (level,)).fetchall()
    else:
        questions = conn.execute('''
            SELECT q.id, q.question_text, q.options, q.correct_answer, l.level
            FROM questions q
            JOIN english_levels l ON q.level_id = l.id
            ORDER BY RANDOM()
        ''').fetchall()
    conn.close()
    
    # Store quiz in session
    quiz_data = []
    for q in questions:
        quiz_data.append({
            'id': q['id'],
            'question': q['question_text'],
            'options': json.loads(q['options']),
            'correct': q['correct_answer'],
            'level': q['level']
        })
    
    session['current_quiz'] = {
        'questions': quiz_data,
        'current': 0,
        'score': 0,
        'wrong_answers': [],
        'start_time': datetime.now().isoformat(),
        'level': level
    }
    
    return jsonify({
        'success': True,
        'total_questions': len(quiz_data),
        'question': {
            'id': quiz_data[0]['id'],
            'text': quiz_data[0]['question'],
            'options': quiz_data[0]['options'],
            'level': quiz_data[0]['level'],
            'number': 1
        }
    })

@app.route('/api/quiz/answer', methods=['POST'])
@login_required
def submit_answer():
    data = request.json
    answer = data.get('answer')
    
    if 'current_quiz' not in session:
        return jsonify({'error': 'No active quiz'}), 400
    
    quiz = session['current_quiz']
    current_q = quiz['questions'][quiz['current']]
    
    is_correct = answer == current_q['correct']
    if is_correct:
        quiz['score'] += 1
    else:
        quiz['wrong_answers'].append(current_q['id'])
    
    quiz['current'] += 1
    session['current_quiz'] = quiz
    
    # Check if quiz is finished
    if quiz['current'] >= len(quiz['questions']):
        # Calculate result
        total = len(quiz['questions'])
        score = quiz['score']
        percentage = (score / total) * 100
        
        # Determine level
        if percentage >= 90:
            determined_level = 'C1'
        elif percentage >= 80:
            determined_level = 'B2'
        elif percentage >= 70:
            determined_level = 'B1'
        elif percentage >= 60:
            determined_level = 'A2'
        else:
            determined_level = 'A1'
        
        # Save result
        start_time = datetime.fromisoformat(quiz['start_time'])
        time_taken = int((datetime.now() - start_time).total_seconds())
        
        conn = get_db_connection()
        # Use offset user_id for web users
        user_db_id = session['user_id'] + 10000
        conn.execute('''INSERT INTO results 
                        (user_id, level, score, total_questions, wrong_answers, time_taken, date)
                        VALUES (?, ?, ?, ?, ?, ?, datetime('now'))''',
                     (user_db_id, determined_level, score, total, 
                      json.dumps(quiz['wrong_answers']), time_taken))
        conn.commit()
        conn.close()
        
        return jsonify({
            'finished': True,
            'is_correct': is_correct,
            'result': {
                'score': score,
                'total': total,
                'percentage': percentage,
                'level': determined_level,
                'time_taken': time_taken
            }
        })
    
    # Next question
    next_q = quiz['questions'][quiz['current']]
    return jsonify({
        'finished': False,
        'is_correct': is_correct,
        'question': {
            'id': next_q['id'],
            'text': next_q['question'],
            'options': next_q['options'],
            'level': next_q['level'],
            'number': quiz['current'] + 1,
            'total': len(quiz['questions']),
            'score': quiz['score']
        }
    })

# ================== API - USER ==================
@app.route('/api/user/results', methods=['GET'])
@login_required
def get_user_results():
    user_db_id = session['user_id'] + 10000
    conn = get_db_connection()
    results = conn.execute('''
        SELECT level, score, total_questions, date, time_taken
        FROM results
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT 10
    ''', (user_db_id,)).fetchall()
    conn.close()
    
    return jsonify([{
        'level': r['level'],
        'score': r['score'],
        'total': r['total_questions'],
        'percentage': round((r['score'] / r['total_questions']) * 100, 2),
        'date': r['date'],
        'time_taken': r['time_taken']
    } for r in results])

@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    conn = get_db_connection()
    leaderboard = conn.execute('''
        SELECT u.full_name, u.username, r.level, 
               (r.score * 100.0 / r.total_questions) as percentage,
               r.date
        FROM results r
        JOIN users u ON r.user_id = u.user_id
        ORDER BY percentage DESC, r.date DESC
        LIMIT 20
    ''').fetchall()
    conn.close()
    
    return jsonify([{
        'name': r['full_name'] or r['username'],
        'level': r['level'],
        'percentage': round(r['percentage'], 2),
        'date': r['date']
    } for r in leaderboard])

# ================== API - ADMIN ==================
@app.route('/api/admin/stats', methods=['GET'])
@admin_required
def get_admin_stats():
    conn = get_db_connection()
    stats = {
        'users': conn.execute('SELECT COUNT(*) as count FROM users').fetchone()['count'],
        'web_users': conn.execute('SELECT COUNT(*) as count FROM web_users').fetchone()['count'],
        'questions': conn.execute('SELECT COUNT(*) as count FROM questions').fetchone()['count'],
        'results': conn.execute('SELECT COUNT(*) as count FROM results').fetchone()['count'],
        'reports': conn.execute('SELECT COUNT(*) as count FROM question_reports').fetchone()['count']
    }
    conn.close()
    return jsonify(stats)

@app.route('/api/admin/questions', methods=['GET'])
@admin_required
def get_all_questions():
    conn = get_db_connection()
    questions = conn.execute('''
        SELECT q.id, q.question_text, q.options, q.correct_answer, l.level
        FROM questions q
        JOIN english_levels l ON q.level_id = l.id
        ORDER BY l.id, q.id
    ''').fetchall()
    conn.close()
    
    return jsonify([{
        'id': q['id'],
        'question': q['question_text'],
        'options': json.loads(q['options']),
        'correct': q['correct_answer'],
        'level': q['level']
    } for q in questions])

@app.route('/api/admin/questions', methods=['POST'])
@admin_required
def add_question():
    data = request.json
    level = data.get('level')
    question = data.get('question')
    options = data.get('options')
    correct = data.get('correct')
    
    conn = get_db_connection()
    level_id = conn.execute('SELECT id FROM english_levels WHERE level = ?', 
                           (level,)).fetchone()['id']
    conn.execute('''INSERT INTO questions (level_id, question_text, options, correct_answer)
                    VALUES (?, ?, ?, ?)''',
                 (level_id, question, json.dumps(options), correct))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/questions/<int:question_id>', methods=['PUT'])
@admin_required
def update_question(question_id):
    data = request.json
    question = data.get('question')
    options = data.get('options')
    correct = data.get('correct')
    
    conn = get_db_connection()
    conn.execute('''UPDATE questions 
                    SET question_text = ?, options = ?, correct_answer = ?
                    WHERE id = ?''',
                 (question, json.dumps(options), correct, question_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/questions/<int:question_id>', methods=['DELETE'])
@admin_required
def delete_question(question_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM questions WHERE id = ?', (question_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/admin/reports', methods=['GET'])
@admin_required
def get_reports():
    conn = get_db_connection()
    reports = conn.execute('''
        SELECT r.id, r.reason, r.report_date, 
               q.question_text, u.full_name
        FROM question_reports r
        JOIN questions q ON r.question_id = q.id
        JOIN users u ON r.user_id = u.user_id
        ORDER BY r.report_date DESC
    ''').fetchall()
    conn.close()
    
    return jsonify([{
        'id': r['id'],
        'question': r['question_text'],
        'reason': r['reason'],
        'reported_by': r['full_name'],
        'date': r['report_date']
    } for r in reports])

# ================== MAIN ==================
if __name__ == '__main__':
    init_web_users_table()
    app.run(debug=True, port=5000)
