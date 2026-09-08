import sqlite3
import os

db_path = 'learning_platform.db'
print(f"Checking DB at: {os.path.abspath(db_path)}")

if not os.path.exists(db_path):
    print("Database file NOT found.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(quiz_result)")
        columns = cursor.fetchall()
        print("Columns in quiz_result:")
        for col in columns:
            print(col)
    except Exception as e:
        print(f"Error reading table: {e}")
    conn.close()
