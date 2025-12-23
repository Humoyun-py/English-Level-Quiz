import sqlite3

# Connect to the database
conn = sqlite3.connect('english_quiz.db')
c = conn.cursor()

# Check if the table exists
c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='results'")
table_exists = c.fetchone()

if table_exists:
    # Check if the column exists
    c.execute("PRAGMA table_info(results)")
    columns = [col[1] for col in c.fetchall()]
    
    if 'wrong_answers' not in columns:
        # Add the missing column
        c.execute("ALTER TABLE results ADD COLUMN wrong_answers TEXT")
        print("Added wrong_answers column to results table")
    else:
        print("wrong_answers column already exists")
else:
    print("results table does not exist")

conn.commit()
conn.close()