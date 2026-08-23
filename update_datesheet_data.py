import sqlite3
import json

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

classes_perfect = [
    {
        "section": "العالمية",
        "class_name": "السنة الثانية",
        "papers": [
            {"subject": "شرح معاني الآثار\nالمؤطا للامام مالک", "copies": 2},
            {"subject": "الصحيح للبخاري\nکامل", "copies": 1},
            {"subject": "الصحيح لمسلم کامل مع\nحفظ حديث", "copies": 1},
            {"subject": "السنن لأبي داود کامل", "copies": 1},
            {"subject": "الجامع للترمذي\nکامل", "copies": 1}
        ]
    },
    {
        "section": "العالمية",
        "class_name": "السنة الأولى",
        "papers": [
            {"subject": "التبيان في علوم القرآن\nمع تفسير البيضاوي", "copies": 1},
            {"subject": "تقابل اديان مع اصول افتاء\nمع الهداية ج 3", "copies": 2},
            {"subject": "مشکوة المصابيح (کامل)\nمع حفظ حديث", "copies": 1},
            {"subject": "شرح نخبة الفکر مع تيسير\nالمصطلح الحديث", "copies": 1},
            {"subject": "الهداية ج 4", "copies": 1}
        ]
    },
    {
        "section": "العالية",
        "class_name": "السنة الثانية",
        "papers": [
            {"subject": "الفوز الكبير مع الجلالين\nکامل", "copies": 1},
            {"subject": "الهيئة الصغرىٰ مع\nشرح العقائد", "copies": 1},
            {"subject": "التوضيح\nمع الهداية ج 2", "copies": 2},
            {"subject": "السراجي مع کتاب الآثار مع\nحفظ حديث", "copies": 1},
            {"subject": "ديوان الحماسة مع متن الکافي", "copies": 1}
        ]
    },
    {
        "section": "العالية",
        "class_name": "السنة الأولى",
        "papers": [
            {"subject": "ترجمة القرآن مع آثار السنن\nمع حفظ حديث", "copies": 1},
            {"subject": "الانتباهات المفيدة مع شرح\nعقيدة الطحاوية و معين\nالفلسفة", "copies": 1},
            {"subject": "الحسامي مع نور الأنوار", "copies": 1},
            {"subject": "ديوان المتنبي مع المعلقات\nالسبع / مختصر المعاني", "copies": 2},
            {"subject": "الهداية ج 1", "copies": 1}
        ]
    },
    {
        "section": "الثانوية الخاصة",
        "class_name": "السنة الثانية",
        "papers": [
            {"subject": "ترجمة القرآن مع\nرياض الصالحين مع\nحفظ حديث و معلم\nالإنشاء", "copies": 1},
            {"subject": "نور الأنوار\nالمقامات", "copies": 2},
            {"subject": "کنز الدقائق کامل", "copies": 1},
            {"subject": "شرح الجامي", "copies": 1},
            {"subject": "دروس البلاغة مع\nالقطبي", "copies": 1}
        ]
    },
    {
        "section": "الثانوية الخاصة",
        "class_name": "السنة الأولى",
        "papers": [
            {"subject": "ترجمة القرآن مع\nرياض الصالحين مع حفظ\nحديث", "copies": 1},
            {"subject": "أصول الشاشي مع مبادي\nالاصول", "copies": 1},
            {"subject": "مختصر القدوري (کامل)", "copies": 1},
            {"subject": "نفحة العرب مع معلم الانشاء", "copies": 1},
            {"subject": "کافية\nشرح التهذيب مع متن\nعقيدة الطحاوية", "copies": 2}
        ]
    },
    {
        "section": "الثانوية العامة",
        "class_name": "السنة الثانية",
        "papers": [
            {"subject": "جزء عم مع\nفوائد مکية", "copies": 1},
            {"subject": "علم الصيغة مع\nخاصيات ابواب", "copies": 1},
            {"subject": "زاد الطالبين مع حفظ\nحديث و القراءة الراشدة\nومعلم الانشاء", "copies": 1},
            {"subject": "هداية النحو مع التمارين\nتيسير المنطق مع المرقاة", "copies": 2},
            {"subject": "مختصر القدوري", "copies": 1}
        ]
    },
    {
        "section": "الثانوية العامة",
        "class_name": "السنة الأولى",
        "papers": [
            {"subject": "جمال القرآن مع تعليم\nالإسلام", "copies": 1},
            {"subject": "الصرف مع صفوة المصادر\nالإنکليزية", "copies": 2},
            {"subject": "النجوم مع الحوار", "copies": 1},
            {"subject": "تسهيل النحو\nکريما / تيسير المبتدي", "copies": 2},
            {"subject": "الطريقة العصرية مع\nعربي کا معلم ج1، 2", "copies": 1}
        ]
    },
    {
        "section": "التجويد",
        "class_name": "التجويدللعلماء",
        "papers": [
            {"subject": "جمال القرآن", "copies": 1},
            {"subject": "تفهيم الوقوف", "copies": 1},
            {"subject": "معلم التجويد", "copies": 1},
            {"subject": "الاختبار الشفوي", "copies": 0},
            {"subject": "--", "copies": 0}
        ]
    },
    {
        "section": "التجويد",
        "class_name": "التجويد\nللحفاظ",
        "papers": [
            {"subject": "جمال القرآن", "copies": 1},
            {"subject": "خلاصة التجويد", "copies": 1},
            {"subject": "سيرة الرسول ﷺ\nتعليم الاسلام", "copies": 1},
            {"subject": "الاختبار الشفوي", "copies": 0},
            {"subject": "--", "copies": 0}
        ]
    },
    {
        "section": "تخصص في الإفتاء",
        "class_name": "السنة الثانية",
        "papers": [
            {"subject": "الاشباه والنظائر", "copies": 0},
            {"subject": "الدر المختار ج 3", "copies": 0},
            {"subject": "تمرين افتاء", "copies": 0},
            {"subject": "امداد الاحکام جلد 1، 2", "copies": 0},
            {"subject": "--", "copies": 0}
        ]
    },
    {
        "section": "المعهد",
        "class_name": "الدبلوم",
        "papers": [
            {"subject": "التجويد", "copies": 1},
            {"subject": "اللغة العربية (س)", "copies": 1},
            {"subject": "الحاسوب", "copies": 1},
            {"subject": "اللغة الانجليزية", "copies": 1},
            {"subject": "اللغة العربية (م)\nالاختبار الشفوي", "copies": 1}
        ]
    }
]

days_sample = [
    {"day": "السبت", "hijri": "15 ربيع الاول", "gregorian": "29 اگست"},
    {"day": "الأحد", "hijri": "16 ربيع الاول", "gregorian": "30 اگست"},
    {"day": "الإثنين", "hijri": "17 ربيع الاول", "gregorian": "31 اگست"},
    {"day": "الثلاثاء", "hijri": "18 ربيع الاول", "gregorian": "01 ستمبر"},
    {"day": "الأربعاء", "hijri": "19 ربيع الاول", "gregorian": "02 ستمبر"}
]

cursor.execute('''
    UPDATE exam_datesheets 
    SET title = 'جدول الاختبارات الخماسية لجميع المراحل الدراسية للعام',
        academic_year = '1448هـ الموافق 2026م',
        institution_name = 'الجامعۃ الاشرفیہ لاہور',
        exam_timing = '11:00 إلى 08:00',
        days_data = ?,
        classes_data = ?
    WHERE id = 1
''', (json.dumps(days_sample, ensure_ascii=False), json.dumps(classes_perfect, ensure_ascii=False)))

conn.commit()
conn.close()
print("Date sheet updated: Top section is now 'العالمية' and second is 'العالية'!")