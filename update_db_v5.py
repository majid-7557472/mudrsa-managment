import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS site_settings (
    id INTEGER PRIMARY KEY,
    institution_name TEXT DEFAULT 'الجامعۃ الاشرفیہ لاہور',
    helpline_number TEXT DEFAULT '0300-0000000'
)
''')

existing = cursor.execute('SELECT * FROM site_settings WHERE id = 1').fetchone()
if not existing:
    cursor.execute(
        'INSERT INTO site_settings (id, institution_name, helpline_number) VALUES (1, ?, ?)',
        ('الجامعۃ الاشرفیہ لاہور', '0300-0000000')
    )
    conn.commit()
    print("✅ ادارے کی سیٹنگز کا ٹیبل بن گیا۔")
else:
    print("سیٹنگز پہلے سے موجود ہیں۔")

conn.close()