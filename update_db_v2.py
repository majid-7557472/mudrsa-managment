import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE students ADD COLUMN district TEXT")
    conn.commit()
    print("ضلع کا کالم کامیابی سے شامل ہو گیا ہے!")
except sqlite3.OperationalError:
    print("ضلع کا کالم پہلے سے موجود ہے۔")

conn.close()