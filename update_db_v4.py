import sqlite3
from werkzeug.security import generate_password_hash

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

# یوزرز (لاگ ان) کا ٹیبل
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'admin'
)
''')
conn.commit()

# چیک کریں کہ ایڈمن یوزر پہلے سے موجود ہے یا نہیں
existing = cursor.execute('SELECT * FROM users WHERE username = ?', ('admin',)).fetchone()

if not existing:
    # ڈیفالٹ ایڈمن یوزر بنانا: username = admin, password = madrasa123
    hashed_pw = generate_password_hash('madrasa123')
    cursor.execute(
        'INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
        ('admin', hashed_pw, 'مہتمم / ایڈمن', 'admin')
    )
    conn.commit()
    print("✅ ڈیفالٹ ایڈمن یوزر بن گیا۔ Username: admin | Password: madrasa123")
else:
    print("ایڈمن یوزر پہلے سے موجود ہے، دوبارہ نہیں بنایا گیا۔")

conn.close()