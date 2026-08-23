import sqlite3
import json

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

# 1. Create exam_datesheets table
cursor.execute('''
CREATE TABLE IF NOT EXISTS exam_datesheets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    institution_name TEXT DEFAULT 'الجامعۃ الاشرفیہ لاہور',
    academic_year TEXT DEFAULT '1447-1448ھ / 2026ء',
    exam_timing TEXT DEFAULT '08:00 إلى 11:00',
    days_data TEXT NOT NULL, -- JSON array of [{day, hijri, gregorian}]
    classes_data TEXT NOT NULL, -- JSON array of [{section, class_name, papers: [{subject, copies}]}]
    footer_note TEXT DEFAULT 'جس خانے میں ❶ لکھا ہے وہ پرچہ ایک ہی جوابی شیٹ پر حل کیا جائے اور جس خانے میں ❷ لکھا ہے وہ پرچہ دو جوابی شیٹوں پر حل کیا جائے۔',
    created_at TEXT NOT NULL
)
''')

# Seed the default authentic Ashrafia Date Sheet from the user's photo
days_sample = [
    {"day": "السبت", "hijri": "15 ربیع الاول", "gregorian": "29 اگست"},
    {"day": "الأحد", "hijri": "16 ربیع الاول", "gregorian": "30 اگست"},
    {"day": "الإثنين", "hijri": "17 ربیع الاول", "gregorian": "31 اگست"},
    {"day": "الثلاثاء", "hijri": "18 ربیع الاول", "gregorian": "01 ستمبر"},
    {"day": "الأربعاء", "hijri": "19 ربیع الاول", "gregorian": "02 ستمبر"}
]

classes_sample = [
    {
        "section": "العالیة",
        "class_name": "السنة الثانية (دورہ حدیث)",
        "papers": [
            {"subject": "شرح معاني الآثار مع الموطا للامام مالک", "copies": 2},
            {"subject": "الصحیح للبخاري کامل", "copies": 1},
            {"subject": "الصحیح لمسلم کامل مع حفظ حدیث", "copies": 1},
            {"subject": "السنن لأبي داود کامل", "copies": 1},
            {"subject": "الجامع للترمذي کامل", "copies": 1}
        ]
    },
    {
        "section": "العالیة",
        "class_name": "السنة الأولى (سابعہ)",
        "papers": [
            {"subject": "التبيان في علوم القرآن مع تفسير البيضاوي", "copies": 1},
            {"subject": "تقابل اديان مع اصول افتاء مع الهداية ج3", "copies": 2},
            {"subject": "مشکوٰۃ المصابیح (کامل) مع حفظ حدیث", "copies": 1},
            {"subject": "شرح نخبة الفکر مع تیسیر المصطلح الحديث", "copies": 1},
            {"subject": "الهداية ج4", "copies": 1}
        ]
    },
    {
        "section": "العالیة",
        "class_name": "السنة الثانية (سادسہ)",
        "papers": [
            {"subject": "الفوز الکبیر مع الجلالین کامل", "copies": 1},
            {"subject": "الهيئة الصغریٰ مع شرح العقائد", "copies": 1},
            {"subject": "التوضیح مع الهدایة ج2", "copies": 2},
            {"subject": "السراجي مع کتاب الآثار مع حفظ حدیث", "copies": 1},
            {"subject": "دیوان الحماسة مع متن الکافي", "copies": 1}
        ]
    },
    {
        "section": "العالیة",
        "class_name": "السنة الأولى (خامسہ)",
        "papers": [
            {"subject": "ترجمة القرآن مع آثار السنن مع حفظ حدیث", "copies": 1},
            {"subject": "الانتباهات المفيدة مع شرح عقيدة الطحاوية و معین الفلسفة", "copies": 1},
            {"subject": "الحسامي مع نور الأنوار", "copies": 1},
            {"subject": "دیوان المتنبي مع المعلقات السبع / مختصر المعاني", "copies": 2},
            {"subject": "الهداية ج1", "copies": 1}
        ]
    },
    {
        "section": "الثانوية الخاصة",
        "class_name": "السنة الثانية (رابعہ)",
        "papers": [
            {"subject": "ترجمة القرآن مع ریاض الصالحین مع حفظ حدیث و معلم الإنشاء", "copies": 1},
            {"subject": "نور الأنوار مع المقامات", "copies": 2},
            {"subject": "کنز الدقائق کامل", "copies": 1},
            {"subject": "شرح الجامي", "copies": 1},
            {"subject": "دروس البلاغة مع القطبي", "copies": 1}
        ]
    },
    {
        "section": "الثانوية الخاصة",
        "class_name": "السنة الأولى (ثالثہ)",
        "papers": [
            {"subject": "ترجمة القرآن مع ریاض الصالحین مع حفظ حدیث", "copies": 1},
            {"subject": "أصول الشاشي مع مبادي الاصول", "copies": 1},
            {"subject": "مختصر القدوري (کامل)", "copies": 1},
            {"subject": "نفحة العرب مع معلم الانشاء", "copies": 1},
            {"subject": "کافية مع شرح التهذیب مع متن عقيدة الطحاوية", "copies": 2}
        ]
    },
    {
        "section": "الثانوية العامة",
        "class_name": "السنة الثانية (ثانیہ)",
        "papers": [
            {"subject": "جزء عم مع فوائد مکیة", "copies": 1},
            {"subject": "علم الصیغة مع خاصیات ابواب", "copies": 1},
            {"subject": "زاد الطالبین مع حفظ حدیث و القراءة الراشدة و معلم الانشاء", "copies": 1},
            {"subject": "هدایة النحو مع التمارین مع تیسیر المنطق مع المرقاة", "copies": 2},
            {"subject": "مختصر القدوري", "copies": 1}
        ]
    },
    {
        "section": "الثانوية العامة",
        "class_name": "السنة الأولى (اولیٰ)",
        "papers": [
            {"subject": "جمال القرآن مع تعلیم الاسلام", "copies": 1},
            {"subject": "الصرف مع صفوة المصادر مع الانکلیزیة", "copies": 2},
            {"subject": "النجوم مع الحوار", "copies": 1},
            {"subject": "تسهیل النحو مع کریما / تیسیر المبتدي", "copies": 2},
            {"subject": "الطریقة العصریة مع عربی کا معلم ج1، 2", "copies": 1}
        ]
    },
    {
        "section": "التجويد",
        "class_name": "التجوید للعلماء",
        "papers": [
            {"subject": "جمال القرآن", "copies": 1},
            {"subject": "تفهیم الوقوف", "copies": 1},
            {"subject": "معلم التجوید", "copies": 1},
            {"subject": "الاختبار الشفوي", "copies": 0},
            {"subject": "--", "copies": 0}
        ]
    },
    {
        "section": "التجويد",
        "class_name": "التجوید للحفاظ",
        "papers": [
            {"subject": "جمال القرآن", "copies": 1},
            {"subject": "خلاصة التجوید", "copies": 1},
            {"subject": "سیرة الرسول ﷺ مع تعلیم الاسلام", "copies": 1},
            {"subject": "الاختبار الشفوي", "copies": 0},
            {"subject": "--", "copies": 0}
        ]
    },
    {
        "section": "تخصص في الإفتاء",
        "class_name": "السنة الثانية",
        "papers": [
            {"subject": "الاشباه والنظائر", "copies": 0},
            {"subject": "الدر المختار ج3", "copies": 0},
            {"subject": "تمرین افتاء", "copies": 0},
            {"subject": "امداد الاحکام جلد 1، 2", "copies": 0},
            {"subject": "--", "copies": 0}
        ]
    },
    {
        "section": "المعهد",
        "class_name": "الدبلوم",
        "papers": [
            {"subject": "التجوید", "copies": 1},
            {"subject": "اللغة العربية (س)", "copies": 1},
            {"subject": "الحاسوب", "copies": 1},
            {"subject": "اللغة الانجليزية", "copies": 1},
            {"subject": "اللغة العربية (م) مع الاختبار الشفوي", "copies": 1}
        ]
    }
]

# Check if table already has rows, otherwise seed
count = cursor.execute('SELECT COUNT(*) FROM exam_datesheets').fetchone()[0]
if count == 0:
    cursor.execute('''
        INSERT INTO exam_datesheets (title, institution_name, academic_year, exam_timing, days_data, classes_data, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        'جدول الاختبارات الخماسية لجميع المراحل الدراسية',
        'الجامعۃ الاشرفیہ لاہور',
        '1447-1448ھ / 2026ء',
        '08:00 إلى 11:00',
        json.dumps(days_sample, ensure_ascii=False),
        json.dumps(classes_sample, ensure_ascii=False),
        '2026-08-23'
    ))

conn.commit()
conn.close()
print("Migration v8 completed: exam_datesheets table created and seeded successfully!")