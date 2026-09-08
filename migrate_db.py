import sqlite3

def migrate():
    try:
        conn = sqlite3.connect('learning_platform.db')
        cursor = conn.cursor()
        cursor.execute("ALTER TABLE quiz_result ADD COLUMN details_json TEXT")
        conn.commit()
        print("Migration successful: Added details_json to quiz_result")
        conn.close()
    except Exception as e:
        print(f"Migration failed (maybe column exists): {e}")

if __name__ == "__main__":
    migrate()
