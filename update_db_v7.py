import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

# 1. Create notifications_log table
cursor.execute('''
CREATE TABLE IF NOT EXISTS notifications_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    message TEXT NOT NULL,
    target_class TEXT,
    total_recipients INTEGER DEFAULT 0,
    channel TEXT DEFAULT 'WhatsApp / SMS',
    sent_by TEXT DEFAULT 'مہتمم',
    sent_at TEXT NOT NULL
)
''')

# 2. Add SMS / WhatsApp Gateway fields to site_settings if not exist
site_cols = [c[1] for c in cursor.execute('PRAGMA table_info(site_settings)').fetchall()]
if 'sms_api_url' not in site_cols:
    cursor.execute('ALTER TABLE site_settings ADD COLUMN sms_api_url TEXT DEFAULT ""')
if 'sms_api_key' not in site_cols:
    cursor.execute('ALTER TABLE site_settings ADD COLUMN sms_api_key TEXT DEFAULT ""')
if 'whatsapp_gateway_url' not in site_cols:
    cursor.execute('ALTER TABLE site_settings ADD COLUMN whatsapp_gateway_url TEXT DEFAULT ""')

conn.commit()
conn.close()
print("Migration v7 completed: notifications_log and gateway settings ready.")