import sqlite3

def create_madrasa_database():
    conn = sqlite3.connect('madrasa.db')
    cursor = conn.cursor()

    # 1. طلبہ کا بنیادی ٹیبل (Students Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admission_form_no TEXT UNIQUE,
        student_name TEXT NOT NULL,
        father_name TEXT NOT NULL,
        student_cnic TEXT,
        father_cnic TEXT,
        guardian_name TEXT,
        guardian_relation TEXT,
        father_profession TEXT,
        dob TEXT,
        caste TEXT,
        blood_group TEXT,
        marital_status TEXT,
        temp_address TEXT,
        perm_address TEXT,
        student_phone TEXT,
        guardian_phone TEXT,
        residence_status TEXT,
        aid_status TEXT,
        admission_type TEXT,
        current_class TEXT NOT NULL,
        admission_status TEXT DEFAULT 'زیر تعلیم',
        admission_date TEXT
    )
    ''')

    # 2. سابقہ تعلیمی ریکارڈ (Previous Education Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS previous_education (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        level_name TEXT,
        year_passed TEXT,
        total_marks INTEGER,
        obtained_marks INTEGER,
        grade_division TEXT,
        board_madrasa TEXT,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    ''')

    # 3. امتحانات اور ڈیٹ شیٹ کا ٹیبل (Exams Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_name TEXT NOT NULL,
        academic_year TEXT NOT NULL
    )
    ''')

    # 4. نشست بندی اور رول نمبر سلپ (Seating Plan Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS seating_plan (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        student_id INTEGER,
        exam_roll_no TEXT,
        hall_room_no TEXT,
        seat_no TEXT,
        FOREIGN KEY (exam_id) REFERENCES exams (id),
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    ''')

    # 5. امتحانی نتائج کا ٹیبل (Exam Results Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS exam_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER,
        student_id INTEGER,
        subject_book_name TEXT NOT NULL,
        total_marks INTEGER DEFAULT 100,
        obtained_marks INTEGER,
        remarks TEXT,
        FOREIGN KEY (exam_id) REFERENCES exams (id),
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    ''')

    # 6. حاضری کا ٹیبل (Attendance Table)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER,
        date TEXT,
        status TEXT,
        FOREIGN KEY (student_id) REFERENCES students (id)
    )
    ''')

    conn.commit()
    conn.close()
    print("ڈیٹا بیس اور تمام ٹیبلز کامیابی کے ساتھ بن گئے ہیں!")

if __name__ == '__main__':
    create_madrasa_database()