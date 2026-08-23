import sqlite3

conn = sqlite3.connect('madrasa.db')
cursor = conn.cursor()

# Create indexes for high-speed query performance (6,000+ students)
cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_class ON students(current_class)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_name ON students(student_name)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_form ON students(admission_form_no)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_cnic ON students(student_cnic)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_students_roll ON students(class_roll_no)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_date ON attendance(date)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_attendance_student ON attendance(student_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_results_student ON exam_results(student_id)')
cursor.execute('CREATE INDEX IF NOT EXISTS idx_exam_results_exam ON exam_results(exam_id)')

conn.commit()
conn.close()
print("High-performance database indexes created for 6,000+ students scale!")