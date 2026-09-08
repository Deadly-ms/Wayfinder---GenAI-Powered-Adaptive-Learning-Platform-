import sqlite3
import os

db_path = 'instance/learning_platform.db'
if not os.path.exists(db_path):
    print(f"DB not found at {db_path}")
else:
    print(f"DB found at {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("Tables:", tables)
    
    if ('chat_message',) in tables:
        print("chat_message table exists.")
    else:
        print("ERROR: chat_message table MISSING.")
    conn.close()
