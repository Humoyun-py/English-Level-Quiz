import sqlite3

conn = sqlite3.connect('english_quiz.db')
c = conn.cursor()
c.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = c.fetchall()
print("Tables:", tables)

if ('results',) in tables:
    c.execute("PRAGMA table_info(results)")
    columns = c.fetchall()
    print("Columns in results:", [col[1] for col in columns])

conn.close()