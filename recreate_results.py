import sqlite3

conn = sqlite3.connect('english_quiz.db')
c = conn.cursor()

# Drop the existing results table
c.execute("DROP TABLE IF EXISTS results")

# Recreate with correct schema
c.execute('''CREATE TABLE results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    level TEXT,
    score INTEGER,
    total_questions INTEGER,
    wrong_answers TEXT,
    time_taken INTEGER,
    date TEXT,
    FOREIGN KEY (user_id) REFERENCES users (user_id)
)''')

conn.commit()
conn.close()
print("Results table recreated with correct schema.")