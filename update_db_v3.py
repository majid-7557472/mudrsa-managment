import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE students ADD COLUMN class_roll_no TEXT")
    conn.commit()
    print("رول نمبر (class_roll_no) کا کالم کامیابی سے شامل ہو گیا ہے!")
except sqlite3.OperationalError:
    print("رول نمبر کا کالم پہلے سے موجود ہے۔")

conn.close()