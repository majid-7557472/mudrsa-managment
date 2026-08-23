import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

# Check if 'photo' column exists in students table
columns = [col[1] for col in cursor.execute('PRAGMA table_info(students)').fetchall()]
if 'photo' not in columns:
    cursor.execute('ALTER TABLE students ADD COLUMN photo TEXT DEFAULT NULL')
    conn.commit()
    print("Database updated: photo column added to students table.")
else:
    print("photo column already exists.")

conn.close()