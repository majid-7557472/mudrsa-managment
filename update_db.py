import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

# کسٹم خانے (Custom Fields Definition)
cursor.execute('''
CREATE TABLE IF NOT EXISTS custom_fields (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL,       -- طالب علم (student) یا امتحان (exam)
    field_label TEXT NOT NULL,   -- خانے کا نام (مثلاً: وظیفہ کی رقم)
    field_type TEXT DEFAULT 'text'
)
''')

# کسٹم خانوں میں محفوظ شدہ ڈیٹا (Custom Field Values)
cursor.execute('''
CREATE TABLE IF NOT EXISTS custom_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    field_id INTEGER NOT NULL,
    record_id INTEGER NOT NULL,   -- طالب علم کی آئی ڈی یا متعلقہ ریکارڈ آئی ڈی
    field_value TEXT,
    FOREIGN KEY (field_id) REFERENCES custom_fields (id) ON DELETE CASCADE
)
''')

conn.commit()
conn.close()
print("ڈیٹا بیس میں کسٹم فیلڈز کا سسٹم کامیابی سے فعال ہو گیا ہے!")

