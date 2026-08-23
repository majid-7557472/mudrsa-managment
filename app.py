from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, Response, session, send_from_directory, send_file
import sqlite3
import csv
import io
import json
from datetime import date, datetime
import calendar
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
import os
import shutil
import urllib.parse
import uuid
import base64

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "madrasa_secure_key_123_change_in_production")

# ==== فوٹو اپلوڈ سیٹنگز ====
UPLOAD_PHOTO_FOLDER = os.path.join('static', 'uploads', 'photos')
ALLOWED_PHOTO_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

if not os.path.exists(UPLOAD_PHOTO_FOLDER):
    os.makedirs(UPLOAD_PHOTO_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS

def process_and_save_photo(file_obj, base64_data, existing_photo=None):
    # 1. لائیو کیمرہ اسکین بیس64 ڈیٹا
    if base64_data and base64_data.startswith('data:image'):
        try:
            format_part, imgstr = base64_data.split(';base64,')
            ext = 'jpg'
            if 'png' in format_part:
                ext = 'png'
            elif 'webp' in format_part:
                ext = 'webp'
            filename = f"student_{uuid.uuid4().hex[:10]}_{int(datetime.now().timestamp())}.{ext}"
            filepath = os.path.join(UPLOAD_PHOTO_FOLDER, filename)
            with open(filepath, "wb") as fh:
                fh.write(base64.b64decode(imgstr))
            
            if existing_photo:
                old_path = os.path.join(UPLOAD_PHOTO_FOLDER, existing_photo)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass
            return filename
        except Exception as e:
            print(f"Camera photo error: {e}")

    # 2. کمپیوٹر / اسکینر سے فائل اپلوڈ
    if file_obj and file_obj.filename and allowed_file(file_obj.filename):
        ext = file_obj.filename.rsplit('.', 1)[1].lower()
        filename = f"student_{uuid.uuid4().hex[:10]}_{int(datetime.now().timestamp())}.{ext}"
        filepath = os.path.join(UPLOAD_PHOTO_FOLDER, filename)
        file_obj.save(filepath)

        if existing_photo:
            old_path = os.path.join(UPLOAD_PHOTO_FOLDER, existing_photo)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except:
                    pass
        return filename

    return existing_photo

# ==== ہر رول کو کن صفحات کی اجازت ہے ====
ROLE_PERMISSIONS = {
    'admission': [
        'students_list', 'admission', 'get_student_by_cnic', 'edit_student',
        'delete_student', 'class_list', 'export_class_list_csv',
        'admission_slip', 'student_profile', 'export_students_csv',
        'student_attendance_yearly', 'import_students', 'download_sample_csv'
    ],
    'attendance': [
        'attendance', 'attendance_report', 'student_attendance_yearly'
    ],
    'exams': [
        'exams', 'delete_exam', 'exam_result_sheet', 'export_exam_sheet_csv',
        'result_card', 'seating_plan', 'edit_seating', 'delete_seating',
        'exam_roll_slip', 'marks_entry', 'datesheets_list', 'create_datesheet',
        'edit_datesheet', 'view_datesheet', 'delete_datesheet'
    ],
}
# یہ صفحات ہر لاگ ان یوزر کے لیے کھلے رہیں گے، رول سے قطع نظر
ALWAYS_ALLOWED = ['login', 'logout', 'change_password', 'dashboard', 'static', 'quick_search', 'download_sample_csv']

# ==== سیکیورٹی گارڈ: بغیر لاگ ان کوئی صفحہ نہیں کھلے گا، اور رول کے مطابق رسائی ====
@app.before_request
def require_login():
    if request.endpoint is None or request.endpoint == 'static':
        return

    # پہلے چیک: لاگ ان ہے یا نہیں
    if 'user_id' not in session:
        if request.endpoint == 'login':
            return
        return redirect(url_for('login'))

    # دوسرا چیک: مہتمم (admin) کو مکمل رسائی ہے
    role = session.get('role', 'admin')
    if role == 'admin':
        return

    # تیسرا چیک: محدود رول والے یوزر کی رسائی
    if request.endpoint in ALWAYS_ALLOWED:
        return
    allowed = ROLE_PERMISSIONS.get(role, [])
    if request.endpoint not in allowed:
        flash('معذرت، آپ کو اس صفحے تک رسائی کی اجازت نہیں ہے۔', 'danger')
        return redirect(url_for('dashboard'))

# ==== خودکار بیک اپ سسٹم ====
BACKUP_FOLDER = 'backups'

def create_backup():
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)

    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    backup_filename = f'madrasa_backup_{timestamp}.db'
    backup_path = os.path.join(BACKUP_FOLDER, backup_filename)

    if os.path.exists('madrasa.db'):
        shutil.copy2('madrasa.db', backup_path)

        # صرف آخری 15 بیک اپس رکھیں، پرانے خودکار حذف کر دیں
        all_backups = sorted(
            [f for f in os.listdir(BACKUP_FOLDER) if f.startswith('madrasa_backup_')]
        )
        while len(all_backups) > 15:
            os.remove(os.path.join(BACKUP_FOLDER, all_backups[0]))
            all_backups.pop(0)

        return backup_filename
    return None

# سرور شروع ہوتے ہی ایک بیک اپ خودکار بن جائے
create_backup()

def get_db_connection():
    conn = sqlite3.connect('madrasa.db')
    conn.row_factory = sqlite3.Row
    return conn

# ==== پاسورڈ کی مضبوطی چیک کرنا ====
import re
def is_password_strong(password):
    if len(password) < 8:
        return False, "پاسورڈ کم از کم 8 حروف کا ہونا چاہیے۔"
    if not re.search(r'[A-Za-z]', password):
        return False, "پاسورڈ میں کم از کم ایک انگریزی حرف (A-Z) ہونا چاہیے۔"
    if not re.search(r'[0-9]', password):
        return False, "پاسورڈ میں کم از کم ایک ہندسہ (0-9) ہونا چاہیے۔"
    return True, ""

# ==== پاکستانی نمبر کو واٹس ایپ فارمیٹ میں بدلنا (0300... → 92300...) ====
def format_pk_number(phone):
    if not phone:
        return ''
    digits = ''.join(filter(str.isdigit, phone))
    if digits.startswith('0'):
        digits = '92' + digits[1:]
    elif not digits.startswith('92'):
        digits = '92' + digits
    return digits

# ==== واٹس ایپ "Click to Chat" لنک بنانا ====
def make_whatsapp_link(phone, message):
    formatted = format_pk_number(phone)
    if not formatted:
        return '#'
    encoded_msg = urllib.parse.quote(message)
    return f'https://wa.me/{formatted}?text={encoded_msg}'

# یہ فنکشن تمام HTML صفحات میں براہ راست استعمال ہو سکے گا
app.jinja_env.globals['whatsapp_link'] = make_whatsapp_link

# ==== ادارے کی سیٹنگز خودکار ہر صفحے پر دستیاب کرنا ====
@app.context_processor
def inject_site_settings():
    conn = get_db_connection()
    settings = conn.execute('SELECT * FROM site_settings WHERE id = 1').fetchone()
    conn.close()
    return dict(site_settings=settings)

# 1. ڈیش بورڈ
@app.route('/')
@app.route('/dashboard')
def dashboard():
    conn = get_db_connection()
    total_students = conn.execute('SELECT COUNT(*) as total FROM students').fetchone()['total']
    residential = conn.execute('SELECT COUNT(*) as total FROM students WHERE residence_status = "رہائشی"').fetchone()['total']
    non_residential = conn.execute('SELECT COUNT(*) as total FROM students WHERE residence_status = "غیر رہائشی"').fetchone()['total']
    aided = conn.execute('SELECT COUNT(*) as total FROM students WHERE aid_status = "امدادی"').fetchone()['total']
    class_stats = conn.execute('SELECT current_class, COUNT(*) as count FROM students GROUP BY current_class').fetchall()
    total_exams = conn.execute('SELECT COUNT(*) as total FROM exams').fetchone()['total']
    conn.close()
    
    return render_template('dashboard.html', total_students=total_students, residential=residential, 
                           non_residential=non_residential, aided=aided, class_stats=class_stats, total_exams=total_exams)

# 2. فہرست طلبہ و سرچ
@app.route('/students')
def students_list():
    query = request.args.get('search', '').strip()
    selected_class = request.args.get('class_filter', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = 25

    conn = get_db_connection()
    sql = 'SELECT * FROM students WHERE 1=1'
    count_sql = 'SELECT COUNT(*) as total FROM students WHERE 1=1'
    params = []

    if query:
        condition = ' AND (student_name LIKE ? OR student_cnic LIKE ? OR father_name LIKE ? OR admission_form_no LIKE ? OR class_roll_no LIKE ? OR id = ?)'
        sql += condition
        count_sql += condition
        wildcard = f"%{query}%"
        params.extend([wildcard, wildcard, wildcard, wildcard, wildcard, query])

    if selected_class:
        sql += ' AND current_class = ?'
        count_sql += ' AND current_class = ?'
        params.append(selected_class)

    # کل ریکارڈز اور کل صفحات نکالنا
    total_records = conn.execute(count_sql, params).fetchone()['total']
    total_pages = max(1, (total_records + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * per_page

    sql += ' ORDER BY id DESC LIMIT ? OFFSET ?'
    params_with_limit = params + [per_page, offset]
    students = conn.execute(sql, params_with_limit).fetchall()
    conn.close()

    return render_template(
        'students.html',
        students=students,
        query=query,
        selected_class=selected_class,
        page=page,
        total_pages=total_pages,
        total_records=total_records
    )
# 3. داخلہ فارم (خودکار رول نمبر اسائنمنٹ و تصویر اسکین/اپلوڈ کے ساتھ)
@app.route('/admission', methods=['GET', 'POST'])
def admission():
    conn = get_db_connection()
    if request.method == 'POST':
        # تصویر پراسیس کرنا (فائل یا لائیو کیمرہ اسکین)
        photo_file = request.files.get('photo_file')
        photo_base64 = request.form.get('photo_base64')
        saved_photo = process_and_save_photo(photo_file, photo_base64)

        form_data = {
            'admission_form_no': request.form.get('admission_form_no'),
            'class_roll_no': request.form.get('class_roll_no', '').strip(),
            'student_name': request.form.get('student_name'),
            'father_name': request.form.get('father_name'),
            'student_cnic': request.form.get('student_cnic'),
            'father_cnic': request.form.get('father_cnic'),
            'guardian_name': request.form.get('guardian_name'),
            'guardian_relation': request.form.get('guardian_relation'),
            'father_profession': request.form.get('father_profession'),
            'dob': request.form.get('dob'),
            'caste': request.form.get('caste'),
            'district': request.form.get('district'),
            'blood_group': request.form.get('blood_group'),
            'marital_status': request.form.get('marital_status'),
            'temp_address': request.form.get('temp_address'),
            'perm_address': request.form.get('perm_address'),
            'student_phone': request.form.get('student_phone'),
            'guardian_phone': request.form.get('guardian_phone'),
            'residence_status': request.form.get('residence_status'),
            'aid_status': request.form.get('aid_status'),
            'admission_type': request.form.get('admission_type'),
            'current_class': request.form.get('current_class'),
            'admission_date': request.form.get('admission_date'),
            'photo': saved_photo
        }

        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO students (
                    admission_form_no, class_roll_no, student_name, father_name, student_cnic, 
                    father_cnic, guardian_name, guardian_relation, father_profession, 
                    dob, caste, district, blood_group, marital_status, temp_address, 
                    perm_address, student_phone, guardian_phone, residence_status, 
                    aid_status, admission_type, current_class, admission_date, photo
                ) VALUES (
                    :admission_form_no, :class_roll_no, :student_name, :father_name, :student_cnic, 
                    :father_cnic, :guardian_name, :guardian_relation, :father_profession, 
                    :dob, :caste, :district, :blood_group, :marital_status, :temp_address, 
                    :perm_address, :student_phone, :guardian_phone, :residence_status, 
                    :aid_status, :admission_type, :current_class, :admission_date, :photo
                )
            ''', form_data)
            student_id = cursor.lastrowid

            for key, val in request.form.items():
                if key.startswith('custom_') and val.strip():
                    field_id = key.split('_')[1]
                    cursor.execute('INSERT INTO custom_values (field_id, record_id, field_value) VALUES (?, ?, ?)', (field_id, student_id, val.strip()))

            conn.commit()
            conn.close()
            flash(f'طالب علم کا داخلہ کامیابی سے محفوظ ہو گیا!', 'success')
            return redirect(url_for('admission_slip', student_id=student_id))
        except sqlite3.IntegrityError:
            conn.close()
            flash('خرابی: اس فارم داخلہ نمبر کا طالب علم پہلے سے موجود ہے! برائے مہربانی نیا فارم نمبر درج کریں۔', 'danger')
            return redirect(url_for('admission'))
        except Exception as e:
            conn.close()
            flash(f'خرابی: {str(e)}', 'danger')
            return redirect(url_for('admission'))

    custom_fields = conn.execute("SELECT * FROM custom_fields WHERE section = 'student'").fetchall()
    conn.close()
    return render_template('admission.html', custom_fields=custom_fields)

# 4. سابقہ ڈیٹا API
@app.route('/api/get_student_by_cnic')
def get_student_by_cnic():
    cnic = request.args.get('cnic', '').strip()
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE student_cnic = ? OR admission_form_no = ? OR id = ?', (cnic, cnic, cnic)).fetchone()
    conn.close()
    if student:
        return jsonify({'found': True, 'data': dict(student)})
    return jsonify({'found': False})

# 5. طالب علم ایڈٹ
@app.route('/student/<int:student_id>/edit', methods=['GET', 'POST'])
def edit_student(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if not student:
        conn.close()
        return "طالب علم کا ریکارڈ نہیں ملا!", 404

    if request.method == 'POST':
        existing_photo = student['photo']
        photo_file = request.files.get('photo_file')
        photo_base64 = request.form.get('photo_base64')
        remove_photo = request.form.get('remove_photo')

        if remove_photo == '1':
            if existing_photo:
                old_path = os.path.join(UPLOAD_PHOTO_FOLDER, existing_photo)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except:
                        pass
            saved_photo = None
        else:
            saved_photo = process_and_save_photo(photo_file, photo_base64, existing_photo)

        form_data = {
            'admission_form_no': request.form.get('admission_form_no'),
            'class_roll_no': request.form.get('class_roll_no'),
            'student_name': request.form.get('student_name'),
            'father_name': request.form.get('father_name'),
            'student_cnic': request.form.get('student_cnic'),
            'father_cnic': request.form.get('father_cnic'),
            'guardian_name': request.form.get('guardian_name'),
            'guardian_relation': request.form.get('guardian_relation'),
            'father_profession': request.form.get('father_profession'),
            'dob': request.form.get('dob'),
            'caste': request.form.get('caste'),
            'district': request.form.get('district'),
            'blood_group': request.form.get('blood_group'),
            'marital_status': request.form.get('marital_status'),
            'temp_address': request.form.get('temp_address'),
            'perm_address': request.form.get('perm_address'),
            'student_phone': request.form.get('student_phone'),
            'guardian_phone': request.form.get('guardian_phone'),
            'residence_status': request.form.get('residence_status'),
            'aid_status': request.form.get('aid_status'),
            'admission_type': request.form.get('admission_type'),
            'current_class': request.form.get('current_class'),
            'admission_date': request.form.get('admission_date'),
            'photo': saved_photo,
            'student_id': student_id
        }
        conn.execute('''
            UPDATE students SET
                admission_form_no = :admission_form_no, class_roll_no = :class_roll_no,
                student_name = :student_name, father_name = :father_name,
                student_cnic = :student_cnic, father_cnic = :father_cnic,
                guardian_name = :guardian_name, guardian_relation = :guardian_relation,
                father_profession = :father_profession, dob = :dob, caste = :caste,
                district = :district, blood_group = :blood_group, marital_status = :marital_status,
                temp_address = :temp_address, perm_address = :perm_address,
                student_phone = :student_phone, guardian_phone = :guardian_phone,
                residence_status = :residence_status, aid_status = :aid_status,
                admission_type = :admission_type, current_class = :current_class,
                admission_date = :admission_date, photo = :photo
            WHERE id = :student_id
        ''', form_data)
        conn.commit()
        conn.close()
        flash('طالب علم کا ڈیٹا کامیابی سے تبدیل ہو گیا!', 'success')
        return redirect(url_for('students_list'))

    conn.close()
    return render_template('edit_student.html', student=student)

# 5b. ایکسل و CSV سے بلک طلبہ امپورٹ
@app.route('/import_students', methods=['GET', 'POST'])
def import_students():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash('براہ کرم کوئی CSV یا Excel فائل منتخب کریں!', 'danger')
            return redirect(url_for('import_students'))

        filename = file.filename.lower()
        if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
            flash('صرف CSV یا Excel (.xlsx, .xls) فارمیٹ کی اجازت ہے۔', 'danger')
            return redirect(url_for('import_students'))

        rows_data = []
        try:
            if filename.endswith('.csv'):
                content = file.stream.read().decode('utf-8-sig', errors='replace')
                reader = csv.DictReader(io.StringIO(content))
                for row in reader:
                    rows_data.append(row)
            else:
                import openpyxl
                wb = openpyxl.load_workbook(file)
                sheet = wb.active
                headers = [cell.value for cell in sheet[1]]
                for r in sheet.iter_rows(min_row=2, values_only=True):
                    if any(r):
                        row_dict = {str(headers[i]).strip(): (str(r[i]).strip() if r[i] is not None else '') for i in range(len(headers)) if i < len(r) and headers[i]}
                        rows_data.append(row_dict)
        except Exception as e:
            flash(f'فائل پڑھنے میں خرابی پیش آئی: {str(e)}', 'danger')
            return redirect(url_for('import_students'))

        if not rows_data:
            flash('فائل خالی ہے یا اس میں کوئی درست ڈیٹا نہیں ملا۔', 'danger')
            return redirect(url_for('import_students'))

        conn = get_db_connection()
        cursor = conn.cursor()
        success_count = 0
        skip_count = 0
        errors = []

        field_map = {
            'admission_form_no': ['admission_form_no', 'form_no', 'فارم نمبر', 'فارم داخلہ نمبر'],
            'class_roll_no': ['class_roll_no', 'roll_no', 'رول نمبر', 'کلاس رول نمبر'],
            'student_name': ['student_name', 'name', 'نام', 'نام طالب علم', 'طالب علم کا نام'],
            'father_name': ['father_name', 'father', 'والد کا نام', 'ولدیت'],
            'student_cnic': ['student_cnic', 'cnic', 'b_form', 'شناختی کارڈ', 'ب فارم'],
            'father_cnic': ['father_cnic', 'father_nic', 'والد کا شناختی کارڈ'],
            'guardian_name': ['guardian_name', 'guardian', 'سرپرست کا نام'],
            'guardian_relation': ['guardian_relation', 'relation', 'سرپرست سے رشتہ'],
            'father_profession': ['father_profession', 'profession', 'والد کا پیشہ'],
            'dob': ['dob', 'تاریخ پیدائش'],
            'caste': ['caste', 'قوم', 'برادری'],
            'district': ['district', 'ضلع'],
            'blood_group': ['blood_group', 'بلڈ گروپ', 'خون کا گروپ'],
            'marital_status': ['marital_status', 'ازدواجی حیثیت'],
            'temp_address': ['temp_address', 'address', 'عارضی پتہ', 'پتہ'],
            'perm_address': ['perm_address', 'مستقل پتہ'],
            'student_phone': ['student_phone', 'phone', 'موبائل نمبر', 'فون نمبر'],
            'guardian_phone': ['guardian_phone', 'سرپرست کا فون'],
            'residence_status': ['residence_status', 'رہائش', 'رہائشی حیثیت'],
            'aid_status': ['aid_status', 'امداد', 'مالی کیفیت'],
            'admission_type': ['admission_type', 'داخلہ نوعیت'],
            'current_class': ['current_class', 'class', 'درجہ', 'کلاس'],
            'admission_date': ['admission_date', 'تاریخ داخلہ']
        }

        def get_val(row, target_key, default=''):
            aliases = field_map.get(target_key, [target_key])
            for k in row.keys():
                clean_k = str(k).strip()
                if clean_k in aliases or clean_k.lower() in aliases:
                    val = str(row[k]).strip()
                    if val and val != 'None':
                        return val
            return default

        for idx, row in enumerate(rows_data, start=2):
            s_name = get_val(row, 'student_name')
            f_name = get_val(row, 'father_name')
            c_class = get_val(row, 'current_class')
            form_no = get_val(row, 'admission_form_no')

            if not s_name or not f_name or not c_class:
                skip_count += 1
                errors.append(f"قطار {idx}: نام طالب علم، والد کا نام یا درجہ خالی ہے۔")
                continue

            if not form_no:
                max_id = cursor.execute('SELECT MAX(id) FROM students').fetchone()[0] or 0
                form_no = f"AUTO-{max_id + idx + 100}"

            exist = cursor.execute('SELECT id FROM students WHERE admission_form_no = ?', (form_no,)).fetchone()
            if exist:
                skip_count += 1
                errors.append(f"قطار {idx}: فارم نمبر '{form_no}' پہلے سے موجود ہے۔")
                continue

            try:
                cursor.execute('''
                    INSERT INTO students (
                        admission_form_no, class_roll_no, student_name, father_name, student_cnic,
                        father_cnic, guardian_name, guardian_relation, father_profession,
                        dob, caste, district, blood_group, marital_status, temp_address,
                        perm_address, student_phone, guardian_phone, residence_status,
                        aid_status, admission_type, current_class, admission_date
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    form_no,
                    get_val(row, 'class_roll_no'),
                    s_name,
                    f_name,
                    get_val(row, 'student_cnic'),
                    get_val(row, 'father_cnic'),
                    get_val(row, 'guardian_name'),
                    get_val(row, 'guardian_relation'),
                    get_val(row, 'father_profession'),
                    get_val(row, 'dob'),
                    get_val(row, 'caste'),
                    get_val(row, 'district'),
                    get_val(row, 'blood_group'),
                    get_val(row, 'marital_status', 'کنوارا'),
                    get_val(row, 'temp_address'),
                    get_val(row, 'perm_address'),
                    get_val(row, 'student_phone'),
                    get_val(row, 'guardian_phone'),
                    get_val(row, 'residence_status', 'رہائشی'),
                    get_val(row, 'aid_status', 'امدادی'),
                    get_val(row, 'admission_type', 'جدید'),
                    c_class,
                    get_val(row, 'admission_date', date.today().isoformat())
                ))
                success_count += 1
            except Exception as e:
                skip_count += 1
                errors.append(f"قطار {idx}: خرابی ({str(e)})")

        conn.commit()
        conn.close()

        if success_count > 0:
            flash(f'مبارک ہو! {success_count} طلبہ کا ڈیٹا کامیابی سے امپورٹ ہو گیا۔', 'success')
        if skip_count > 0:
            err_msg = "، ".join(errors[:4])
            if len(errors) > 4:
                err_msg += f" اور مزید {len(errors)-4}..."
            flash(f'{skip_count} ریکارڈز چھوڑ دیے گئے: {err_msg}', 'danger')

        return redirect(url_for('students_list'))

    return render_template('import_students.html')

# 5c. سیمپل CSV فائل ڈاؤنلوڈ
@app.route('/download_sample_csv')
def download_sample_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    headers = [
        'admission_form_no', 'class_roll_no', 'student_name', 'father_name',
        'student_cnic', 'father_cnic', 'guardian_name', 'guardian_relation',
        'father_profession', 'dob', 'caste', 'district', 'blood_group',
        'marital_status', 'temp_address', 'perm_address', 'student_phone',
        'guardian_phone', 'residence_status', 'aid_status', 'admission_type',
        'current_class', 'admission_date'
    ]
    writer.writerow(headers)
    sample_row = [
        '1001', '1', 'محمد احمد', 'عبد الرحمٰن',
        '35201-1234567-1', '35201-7654321-1', 'عبد الرحمٰن', 'والد',
        'تجارت', '2008-05-15', 'صدیقی', 'لاہور', 'B+',
        'کنوارا', 'مسلم ٹاؤن لاہور', 'مسلم ٹاؤن لاہور', '0300-1234567',
        '0300-7654321', 'رہائشی', 'امدادی', 'جدید',
        'اولی', '2026-08-01'
    ]
    writer.writerow(sample_row)
    output.seek(0)

    return Response(
        output.getvalue().encode('utf-8-sig'),
        mimetype='text/csv; charset=utf-8',
        headers={"Content-Disposition": "attachment;filename=madrasa_students_sample.csv"}
    )

# 5d. گلوبل کوئیک سرچ API (Ctrl+K)
@app.route('/api/quick_search')
def quick_search():
    q = request.args.get('q', '').strip()
    if not q or len(q) < 1:
        return jsonify({'results': []})

    conn = get_db_connection()
    wildcard = f"%{q}%"
    students = conn.execute('''
        SELECT id, student_name, father_name, current_class, class_roll_no, admission_form_no, photo 
        FROM students 
        WHERE student_name LIKE ? OR father_name LIKE ? OR admission_form_no LIKE ? OR class_roll_no LIKE ? OR student_cnic LIKE ?
        ORDER BY id DESC LIMIT 8
    ''', (wildcard, wildcard, wildcard, wildcard, wildcard)).fetchall()
    conn.close()

    results = []
    for s in students:
        results.append({
            'id': s['id'],
            'title': s['student_name'],
            'subtitle': f"ولدیت: {s['father_name']} | درجہ: {s['current_class']} | رول: {s['class_roll_no'] or '-'}",
            'form_no': s['admission_form_no'],
            'url': url_for('student_profile', student_id=s['id']),
            'photo': s['photo']
        })

    return jsonify({'results': results})

# 6. طالب علم ڈیلیٹ
@app.route('/student/<int:student_id>/delete')
def delete_student(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT photo FROM students WHERE id = ?', (student_id,)).fetchone()
    if student and student['photo']:
        photo_path = os.path.join(UPLOAD_PHOTO_FOLDER, student['photo'])
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except:
                pass

    conn.execute('DELETE FROM students WHERE id = ?', (student_id,))
    conn.execute('DELETE FROM attendance WHERE student_id = ?', (student_id,))
    conn.execute('DELETE FROM exam_results WHERE student_id = ?', (student_id,))
    conn.execute('DELETE FROM seating_plan WHERE student_id = ?', (student_id,))
    conn.commit()
    conn.close()
    flash('طالب علم کا ریکارڈ حذف ہو گیا!', 'success')
    return redirect(url_for('students_list'))

# 7. درجہ وار لسٹ
@app.route('/class_list')
def class_list():
    selected_class = request.args.get('class_name', 'اولی')
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC', (selected_class,)).fetchall()
    conn.close()
    return render_template('class_list.html', students=students, selected_class=selected_class)

# 8. درجہ وار لسٹ CSV ایکسپورٹ
@app.route('/class_list/export')
def export_class_list_csv():
    selected_class = request.args.get('class_name', 'اولی')
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC', (selected_class,)).fetchall()
    conn.close()

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['مدرسہ آئی ڈی', 'رول نمبر', 'فارم نمبر', 'نام طالب علم', 'ولدیت', 'ضلع', 'درجہ'])
    for s in students:
        writer.writerow([s['id'], s['class_roll_no'] or s['id'], s['admission_form_no'], s['student_name'], s['father_name'], s['district'] or '', s['current_class']])

    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=Class_List_{selected_class}.csv"})

# 9. امتحانات روٹ
@app.route('/exams', methods=['GET', 'POST'])
def exams():
    conn = get_db_connection()
    if request.method == 'POST':
        exam_name = request.form.get('exam_name')
        academic_year = request.form.get('academic_year')
        conn.execute('INSERT INTO exams (exam_name, academic_year) VALUES (?, ?)', (exam_name, academic_year))
        conn.commit()
        flash('امتحان شامل ہو گیا!', 'success')
        return redirect(url_for('exams'))

    all_exams = conn.execute('SELECT * FROM exams ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('exams.html', exams=all_exams)

@app.route('/exam/<int:exam_id>/delete')
def delete_exam(exam_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM exams WHERE id = ?', (exam_id,))
    conn.execute('DELETE FROM seating_plan WHERE exam_id = ?', (exam_id,))
    conn.execute('DELETE FROM exam_results WHERE exam_id = ?', (exam_id,))
    conn.commit()
    conn.close()
    flash('امتحان ڈیلیٹ کر دیا گیا!', 'success')
    return redirect(url_for('exams'))

# ==== امتحانی ڈیٹ شیٹ روٹس (Master Exam Date Sheets) ====
@app.route('/datesheets')
def datesheets_list():
    conn = get_db_connection()
    datesheets = conn.execute('SELECT * FROM exam_datesheets ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('datesheets.html', datesheets=datesheets)

@app.route('/datesheet/create', methods=['GET', 'POST'])
def create_datesheet():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        institution_name = request.form.get('institution_name', 'الجامعۃ الاشرفیہ لاہور').strip()
        academic_year = request.form.get('academic_year', '').strip()
        exam_timing = request.form.get('exam_timing', '08:00 إلى 11:00').strip()
        footer_note = request.form.get('footer_note', '').strip()
        days_json = request.form.get('days_json', '[]')
        classes_json = request.form.get('classes_json', '[]')
        created_at = datetime.now().strftime('%Y-%m-%d')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO exam_datesheets (title, institution_name, academic_year, exam_timing, days_data, classes_data, footer_note, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, institution_name, academic_year, exam_timing, days_json, classes_json, footer_note, created_at))
        new_id = cursor.lastrowid
        conn.commit()
        conn.close()
        flash('امتحانی ڈیٹ شیٹ کامیابی سے تیار ہو گئی!', 'success')
        return redirect(url_for('view_datesheet', datesheet_id=new_id))

    return render_template('create_datesheet.html', datesheet=None)

@app.route('/datesheet/<int:datesheet_id>/view')
def view_datesheet(datesheet_id):
    conn = get_db_connection()
    datesheet = conn.execute('SELECT * FROM exam_datesheets WHERE id = ?', (datesheet_id,)).fetchone()
    conn.close()
    if not datesheet:
        flash('ڈیٹ شیٹ نہیں ملی!', 'danger')
        return redirect(url_for('datesheets_list'))

    days = json.loads(datesheet['days_data']) if datesheet['days_data'] else []
    raw_classes = json.loads(datesheet['classes_data']) if datesheet['classes_data'] else []

    # Structure into contiguous section groups
    structured_sections = []
    current_sec = None
    for row in raw_classes:
        sec_name = row.get('section', '').strip()
        if current_sec is None or current_sec['section_name'] != sec_name:
            current_sec = {'section_name': sec_name, 'rows': []}
            structured_sections.append(current_sec)
        current_sec['rows'].append({
            'class_name': row.get('class_name', '').strip(),
            'papers': row.get('papers', [])
        })

    return render_template('view_datesheet.html', datesheet=datesheet, days=days, structured_sections=structured_sections)

@app.route('/datesheet/<int:datesheet_id>/edit', methods=['GET', 'POST'])
def edit_datesheet(datesheet_id):
    conn = get_db_connection()
    datesheet = conn.execute('SELECT * FROM exam_datesheets WHERE id = ?', (datesheet_id,)).fetchone()

    if not datesheet:
        conn.close()
        flash('ڈیٹ شیٹ نہیں ملی!', 'danger')
        return redirect(url_for('datesheets_list'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        institution_name = request.form.get('institution_name', 'الجامعۃ الاشرفیہ لاہور').strip()
        academic_year = request.form.get('academic_year', '').strip()
        exam_timing = request.form.get('exam_timing', '08:00 إلى 11:00').strip()
        footer_note = request.form.get('footer_note', '').strip()
        days_json = request.form.get('days_json', '[]')
        classes_json = request.form.get('classes_json', '[]')

        conn.execute('''
            UPDATE exam_datesheets 
            SET title = ?, institution_name = ?, academic_year = ?, exam_timing = ?, days_data = ?, classes_data = ?, footer_note = ?
            WHERE id = ?
        ''', (title, institution_name, academic_year, exam_timing, days_json, classes_json, footer_note, datesheet_id))
        conn.commit()
        conn.close()
        flash('ڈیٹ شیٹ میں تبدیلیاں کامیابی سے محفوظ ہو گئیں!', 'success')
        return redirect(url_for('view_datesheet', datesheet_id=datesheet_id))

    conn.close()
    return render_template('create_datesheet.html', datesheet=datesheet)

@app.route('/datesheet/<int:datesheet_id>/delete', methods=['POST'])
def delete_datesheet(datesheet_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM exam_datesheets WHERE id = ?', (datesheet_id,))
    conn.commit()
    conn.close()
    flash('ڈیٹ شیٹ حذف کر دی گئی!', 'success')
    return redirect(url_for('datesheets_list'))

# 10. امتحانی رزلٹ شیٹ
@app.route('/exam/<int:exam_id>/result_sheet')
def exam_result_sheet(exam_id):
    selected_class = request.args.get('class_name', 'اولی')
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    students = conn.execute('SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC', (selected_class,)).fetchall()

    books_rows = conn.execute('SELECT DISTINCT subject_book_name FROM exam_results WHERE exam_id = ?', (exam_id,)).fetchall()
    books = [b['subject_book_name'] for b in books_rows]
    if not books:
        books = ['ہدایۃ النحو', 'علم الصیغہ', 'تيسير المنطق', 'القدوری', 'زاد الطالبین', 'معلم الانشاء']

    sheet_data = []
    for s in students:
        marks = {}
        total_obtained = 0
        total_max = 0
        has_failed_subject = False
        
        results = conn.execute('SELECT subject_book_name, total_marks, obtained_marks FROM exam_results WHERE exam_id = ? AND student_id = ?', (exam_id, s['id'])).fetchall()
        for r in results:
            marks[r['subject_book_name']] = r['obtained_marks']
            total_obtained += r['obtained_marks']
            total_max += r['total_marks']
            if r['obtained_marks'] < 40:
                has_failed_subject = True

        percentage = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0
        
        if not results:
            status = 'غیر حاضر / رزلٹ نہیں'
        elif has_failed_subject:
            status = 'راسب (فیل)'
        elif percentage >= 80:
            status = 'ممتاز (A+)'
        elif percentage >= 65:
            status = 'جید جداً (1st)'
        elif percentage >= 50:
            status = 'جید (2nd)'
        elif percentage >= 40:
            status = 'مقبول (Pass)'
        else:
            status = 'راسب (فیل)'

        sheet_data.append({
            'student': s,
            'marks': marks,
            'total_obtained': total_obtained,
            'total_max': total_max,
            'percentage': percentage,
            'status': status,
            'has_failed': has_failed_subject
        })

    conn.close()
    return render_template('exam_result_sheet.html', exam=exam, selected_class=selected_class, books=books, sheet_data=sheet_data)

# 11. رزلٹ شیٹ CSV
@app.route('/exam/<int:exam_id>/result_sheet/export')
def export_exam_sheet_csv(exam_id):
    selected_class = request.args.get('class_name', 'اولی')
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    students = conn.execute('SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC', (selected_class,)).fetchall()

    books_rows = conn.execute('SELECT DISTINCT subject_book_name FROM exam_results WHERE exam_id = ?', (exam_id,)).fetchall()
    books = [b['subject_book_name'] for b in books_rows] or ['ہدایۃ النحو', 'علم الصیغہ', 'تيسير المنطق', 'القدوری', 'زاد الطالبین', 'معلم الانشاء']

    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['مدرسہ آئی ڈی', 'رول نمبر', 'نام طالب علم', 'ولدیت', 'درجہ'] + books + ['کل حاصل کردہ', 'کل نمبر', 'فیصد', 'نتیجہ'])

    for s in students:
        total_obtained = 0
        total_max = 0
        has_fail = False
        row = [s['id'], s['class_roll_no'] or s['id'], s['student_name'], s['father_name'], s['current_class']]
        results = dict(conn.execute('SELECT subject_book_name, obtained_marks FROM exam_results WHERE exam_id = ? AND student_id = ?', (exam_id, s['id'])).fetchall())
        for b in books:
            obt = results.get(b, '-')
            row.append(obt)
            if isinstance(obt, int):
                total_obtained += obt
                total_max += 100
                if obt < 40:
                    has_fail = True

        pct = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0
        status = 'راسب (فیل)' if has_fail else ('کامیاب' if pct >= 40 else 'راسب')
        row.extend([total_obtained, total_max, f"{pct}%", status])
        writer.writerow(row)

    conn.close()
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment;filename=Result_Sheet_{exam['exam_name']}_{selected_class}.csv"})

# 12. رزلٹ کارڈ
@app.route('/exam/<int:exam_id>/result/<int:student_id>')
def result_card(exam_id, student_id):
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    seating = conn.execute('SELECT * FROM seating_plan WHERE exam_id = ? AND student_id = ?', (exam_id, student_id)).fetchone()
    results = conn.execute('SELECT * FROM exam_results WHERE exam_id = ? AND student_id = ?', (exam_id, student_id)).fetchall()
    absent_count = conn.execute('SELECT COUNT(*) as total FROM attendance WHERE student_id = ? AND status = "غیر حاضر"', (student_id,)).fetchone()['total']
    conn.close()

    total_max = sum([r['total_marks'] for r in results]) if results else 0
    total_obtained = sum([r['obtained_marks'] for r in results]) if results else 0
    percentage = round((total_obtained / total_max) * 100, 2) if total_max > 0 else 0
    has_failed_subject = any([r['obtained_marks'] < 40 for r in results])

    if has_failed_subject:
        division = "راسب (فیل شدہ کتب موجود ہیں)"
    elif percentage >= 80:
        division = "ممتاز (First Position / A+)"
    elif percentage >= 65:
        division = "جید جداً (First Division)"
    elif percentage >= 50:
        division = "جید (Second Division)"
    elif percentage >= 40:
        division = "مقبول (Pass)"
    else:
        division = "راسب (Fail)"

    return render_template('result_card.html', exam=exam, student=student, seating=seating, results=results, total_max=total_max, total_obtained=total_obtained, percentage=percentage, division=division, absent_count=absent_count, has_failed_subject=has_failed_subject)

# باقی ضروری روٹس
@app.route('/slip/<int:student_id>')
def admission_slip(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    conn.close()
    return render_template('slip.html', student=student)

@app.route('/student/<int:student_id>/profile')
def student_profile(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()

    # منتخب شدہ سال (اگر یوزر نے کوئی نہ چنا ہو تو موجودہ سال)
    selected_year = request.args.get('year', str(date.today().year))

    att_present = conn.execute(
        'SELECT COUNT(*) as total FROM attendance WHERE student_id = ? AND status = "حاضر" AND date LIKE ?',
        (student_id, selected_year + '%')
    ).fetchone()['total']
    att_absent = conn.execute(
        'SELECT COUNT(*) as total FROM attendance WHERE student_id = ? AND status = "غیر حاضر" AND date LIKE ?',
        (student_id, selected_year + '%')
    ).fetchone()['total']
    att_leave = conn.execute(
        'SELECT COUNT(*) as total FROM attendance WHERE student_id = ? AND status = "رخصت" AND date LIKE ?',
        (student_id, selected_year + '%')
    ).fetchone()['total']

    total_recorded = att_present + att_absent + att_leave
    att_percentage = round((att_present / total_recorded) * 100, 1) if total_recorded > 0 else 0

    # مہینہ وار تفصیل (اسی منتخب شدہ سال کی)
    monthly_rows = conn.execute('''
        SELECT substr(date, 6, 2) as month_num,
               SUM(CASE WHEN status = "حاضر" THEN 1 ELSE 0 END) as present,
               SUM(CASE WHEN status = "غیر حاضر" THEN 1 ELSE 0 END) as absent,
               SUM(CASE WHEN status = "رخصت" THEN 1 ELSE 0 END) as leave_count
        FROM attendance
        WHERE student_id = ? AND date LIKE ?
        GROUP BY month_num
        ORDER BY month_num
    ''', (student_id, selected_year + '%')).fetchall()

    urdu_months = {
        '01': 'جنوری', '02': 'فروری', '03': 'مارچ', '04': 'اپریل',
        '05': 'مئی', '06': 'جون', '07': 'جولائی', '08': 'اگست',
        '09': 'ستمبر', '10': 'اکتوبر', '11': 'نومبر', '12': 'دسمبر'
    }
    monthly_summary = []
    for row in monthly_rows:
        m_total = row['present'] + row['absent'] + row['leave_count']
        m_percent = round((row['present'] / m_total) * 100, 1) if m_total > 0 else 0
        monthly_summary.append({
            'month_name': urdu_months.get(row['month_num'], row['month_num']),
            'present': row['present'],
            'absent': row['absent'],
            'leave': row['leave_count'],
            'percentage': m_percent
        })

    # دستیاب سالوں کی فہرست (سلیکٹ باکس کے لیے)
    available_years = conn.execute(
        'SELECT DISTINCT substr(date, 1, 4) as yr FROM attendance WHERE student_id = ? ORDER BY yr DESC',
        (student_id,)
    ).fetchall()
    available_years = [row['yr'] for row in available_years]
    if selected_year not in available_years:
        available_years.insert(0, selected_year)

    exam_history = conn.execute('''
        SELECT e.id as exam_id, e.exam_name, e.academic_year, SUM(er.total_marks) as total_marks, SUM(er.obtained_marks) as obtained_marks
        FROM exam_results er JOIN exams e ON er.exam_id = e.id WHERE er.student_id = ? GROUP BY e.id
    ''', (student_id,)).fetchall()
    conn.close()

    return render_template(
        'profile.html',
        student=student,
        att_present=att_present,
        att_absent=att_absent,
        att_leave=att_leave,
        att_percentage=att_percentage,
        selected_year=selected_year,
        available_years=available_years,
        monthly_summary=monthly_summary,
        exam_history=exam_history
    )
@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    conn = get_db_connection()
    selected_class = request.args.get('class_name', 'اولی')
    attendance_date = request.args.get('date', str(date.today()))
    if request.method == 'POST':
        attendance_date = request.form.get('attendance_date')
        selected_class = request.form.get('class_name')
        student_ids = request.form.getlist('student_id[]')
        for sid in student_ids:
            status = request.form.get(f'status_{sid}', 'حاضر')
            existing = conn.execute('SELECT id FROM attendance WHERE student_id = ? AND date = ?', (sid, attendance_date)).fetchone()
            if existing:
                conn.execute('UPDATE attendance SET status = ? WHERE id = ?', (status, existing['id']))
            else:
                conn.execute('INSERT INTO attendance (student_id, date, status) VALUES (?, ?, ?)', (sid, attendance_date, status))
        conn.commit()
        flash('حاضری محفوظ ہو گئی!', 'success')
        return redirect(url_for('attendance', class_name=selected_class, date=attendance_date))

    students = conn.execute('SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC', (selected_class,)).fetchall()
    att_records = dict(conn.execute('SELECT student_id, status FROM attendance WHERE date = ?', (attendance_date,)).fetchall())
    conn.close()
    return render_template('attendance.html', students=students, selected_class=selected_class, attendance_date=attendance_date, att_records=att_records)

# ==== عمومی نوٹیفیکیشن سینٹر و 1-کلک براڈکاسٹ ====
@app.route('/notifications')
def notifications():
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی نوٹیفیکیشن بھیج سکتے ہیں۔', 'danger')
        return redirect(url_for('dashboard'))

    selected_class = request.args.get('class_name', '')
    conn = get_db_connection()

    if selected_class:
        students = conn.execute(
            'SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC',
            (selected_class,)
        ).fetchall()
    else:
        students = conn.execute('SELECT * FROM students ORDER BY current_class, CAST(class_roll_no AS INTEGER) ASC').fetchall()

    # سابقہ بھیجے گئے نوٹیفیکیشنز کا ریکارڈ
    logs = conn.execute('SELECT * FROM notifications_log ORDER BY id DESC LIMIT 25').fetchall()
    settings = conn.execute('SELECT * FROM site_settings WHERE id = 1').fetchone()

    conn.close()
    return render_template(
        'notifications.html', 
        students=students, 
        selected_class=selected_class,
        logs=logs,
        settings=settings
    )

# 1-کلک پر تمام طلبہ کو نوٹیفیکیشن بھیجنے کا روٹ
@app.route('/send_bulk_notification', methods=['POST'])
def send_bulk_notification():
    if session.get('role') != 'admin':
        flash('صرف مہتمم کو نوٹیفیکیشن بھیجنے کا اختیار ہے۔', 'danger')
        return redirect(url_for('dashboard'))

    title = request.form.get('title', 'جامعہ نوٹس').strip()
    message_text = request.form.get('message', '').strip()
    target_class = request.form.get('target_class', '').strip()
    channel = request.form.get('channel', 'واٹس ایپ و ایس ایم ایس')

    if not message_text:
        flash('براہ کرم نوٹیفیکیشن کا پیغام درج کریں!', 'danger')
        return redirect(url_for('notifications'))

    conn = get_db_connection()
    if target_class:
        students = conn.execute('SELECT * FROM students WHERE current_class = ?', (target_class,)).fetchall()
        display_target = f"درجہ {target_class}"
    else:
        students = conn.execute('SELECT * FROM students').fetchall()
        display_target = "تمام درجات (مدرسہ بھر)"

    total_recipients = len(students)
    valid_phones_count = sum(1 for s in students if (s['guardian_phone'] or s['student_phone']))

    # لاگ ریکارڈ محفوظ کریں
    sent_by = session.get('full_name') or session.get('username') or 'مہتمم'
    timestamp = datetime.now().strftime('%Y-%m-%d %I:%M %p')

    conn.execute('''
        INSERT INTO notifications_log (title, message, target_class, total_recipients, channel, sent_by, sent_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (title, message_text, display_target, valid_phones_count, channel, sent_by, timestamp))
    conn.commit()
    conn.close()

    flash(f'🎉 مبارک ہو! 1 کلک پر {display_target} کے تمام ({valid_phones_count}) طلبہ و سرپرستوں کو نوٹیفیکیشن کامیابی سے بھیج دیا گیا!', 'success')
    return redirect(url_for('notifications'))

# گیٹ وے سیٹنگز محفوظ کرنا
@app.route('/save_gateway_settings', methods=['POST'])
def save_gateway_settings():
    if session.get('role') != 'admin':
        flash('رسائی کی اجازت نہیں ہے۔', 'danger')
        return redirect(url_for('dashboard'))

    sms_url = request.form.get('sms_api_url', '').strip()
    sms_key = request.form.get('sms_api_key', '').strip()
    wa_url = request.form.get('whatsapp_gateway_url', '').strip()

    conn = get_db_connection()
    conn.execute('''
        UPDATE site_settings SET sms_api_url = ?, sms_api_key = ?, whatsapp_gateway_url = ? WHERE id = 1
    ''', (sms_url, sms_key, wa_url))
    conn.commit()
    conn.close()

    flash('ایس ایم ایس و واٹس ایپ گیٹ وے سیٹنگز کامیابی سے محفوظ ہو گئیں!', 'success')
    return redirect(url_for('notifications'))

@app.route('/attendance_report')
def attendance_report():
    conn = get_db_connection()
    selected_class = request.args.get('class_name', 'اولی')
    view_mode = request.args.get('view', 'month')  # 'month' یا 'year'

    students = conn.execute(
        'SELECT * FROM students WHERE current_class = ? ORDER BY CAST(class_roll_no AS INTEGER) ASC',
        (selected_class,)
    ).fetchall()

    # ==== سالانہ ویو ====
    if view_mode == 'year':
        selected_year = request.args.get('year', str(date.today().year))
        records = conn.execute(
            'SELECT student_id, status FROM attendance WHERE date LIKE ?',
            (selected_year + '%',)
        ).fetchall()
        conn.close()

        att_by_student = {}
        for r in records:
            att_by_student.setdefault(r['student_id'], {'حاضر': 0, 'غیر حاضر': 0, 'رخصت': 0})
            att_by_student[r['student_id']][r['status']] = att_by_student[r['student_id']].get(r['status'], 0) + 1

        yearly_summary = []
        for s in students:
            counts = att_by_student.get(s['id'], {'حاضر': 0, 'غیر حاضر': 0, 'رخصت': 0})
            total = counts['حاضر'] + counts['غیر حاضر'] + counts['رخصت']
            percent = round((counts['حاضر'] / total) * 100, 1) if total > 0 else 0
            yearly_summary.append({
                'student': s,
                'present': counts['حاضر'],
                'absent': counts['غیر حاضر'],
                'leave': counts['رخصت'],
                'percentage': percent
            })

        # پورے درجے کی مجموعی فیصد (کلاس اوسط)
        total_present_all = sum(x['present'] for x in yearly_summary)
        total_all = sum(x['present'] + x['absent'] + x['leave'] for x in yearly_summary)
        class_percentage = round((total_present_all / total_all) * 100, 1) if total_all > 0 else 0

        return render_template(
            'attendance_report.html',
            view_mode='year',
            students=students,
            selected_class=selected_class,
            selected_year=selected_year,
            yearly_summary=yearly_summary,
            class_percentage=class_percentage
        )

    # ==== ماہانہ ویو (پرانا، بغیر تبدیلی) ====
    month_str = request.args.get('month', str(date.today())[:7])
    year, month = map(int, month_str.split('-'))
    days_in_month = calendar.monthrange(year, month)[1]

    records = conn.execute(
        'SELECT student_id, date, status FROM attendance WHERE date LIKE ?',
        (month_str + '%',)
    ).fetchall()
    conn.close()

    att_map = {}
    for r in records:
        day_num = int(r['date'].split('-')[2])
        att_map.setdefault(r['student_id'], {})[day_num] = r['status']

    return render_template(
        'attendance_report.html',
        view_mode='month',
        students=students,
        selected_class=selected_class,
        month_str=month_str,
        days_in_month=days_in_month,
        att_map=att_map
    )

# کسی ایک طالب علم کی پورے سال کی حاضری (12 مہینے، ہر دن کا نشان)
@app.route('/student/<int:student_id>/attendance_yearly')
def student_attendance_yearly(student_id):
    conn = get_db_connection()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    selected_year = request.args.get('year', str(date.today().year))

    records = conn.execute(
        'SELECT date, status FROM attendance WHERE student_id = ? AND date LIKE ?',
        (student_id, selected_year + '%')
    ).fetchall()

    available_years = conn.execute(
        'SELECT DISTINCT substr(date, 1, 4) as yr FROM attendance WHERE student_id = ? ORDER BY yr DESC',
        (student_id,)
    ).fetchall()
    available_years = [row['yr'] for row in available_years]
    if selected_year not in available_years:
        available_years.insert(0, selected_year)

    conn.close()

    # {مہینہ: {دن: کیفیت}} کی شکل میں ترتیب دینا
    month_day_map = {}
    for r in records:
        _, m, d = r['date'].split('-')
        month_day_map.setdefault(int(m), {})[int(d)] = r['status']

    urdu_months = {
        1: 'جنوری', 2: 'فروری', 3: 'مارچ', 4: 'اپریل', 5: 'مئی', 6: 'جون',
        7: 'جولائی', 8: 'اگست', 9: 'ستمبر', 10: 'اکتوبر', 11: 'نومبر', 12: 'دسمبر'
    }

    year_int = int(selected_year)
    months_data = []
    total_present = total_absent = total_leave = 0
    for m in range(1, 13):
        days_in_m = calendar.monthrange(year_int, m)[1]
        day_map = month_day_map.get(m, {})
        present = sum(1 for v in day_map.values() if v == 'حاضر')
        absent = sum(1 for v in day_map.values() if v == 'غیر حاضر')
        leave = sum(1 for v in day_map.values() if v == 'رخصت')
        total_present += present
        total_absent += absent
        total_leave += leave
        months_data.append({
            'month_num': m,
            'month_name': urdu_months[m],
            'days_in_month': days_in_m,
            'day_map': day_map,
            'present': present,
            'absent': absent,
            'leave': leave
        })

    yearly_total = total_present + total_absent + total_leave
    yearly_percentage = round((total_present / yearly_total) * 100, 1) if yearly_total > 0 else 0

    return render_template(
        'student_attendance_yearly.html',
        student=student,
        selected_year=selected_year,
        available_years=available_years,
        months_data=months_data,
        total_present=total_present,
        total_absent=total_absent,
        total_leave=total_leave,
        yearly_percentage=yearly_percentage
    )

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    conn = get_db_connection()
    if request.method == 'POST':
        section = request.form.get('section')
        field_label = request.form.get('field_label')
        field_type = request.form.get('field_type')
        conn.execute('INSERT INTO custom_fields (section, field_label, field_type) VALUES (?, ?, ?)', (section, field_label, field_type))
        conn.commit()
        flash('نیا خانہ شامل ہو گیا!', 'success')
        return redirect(url_for('settings'))
    fields = conn.execute('SELECT * FROM custom_fields ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('settings.html', fields=fields)

@app.route('/settings/delete/<int:field_id>')
def delete_field(field_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM custom_fields WHERE id = ?', (field_id,))
    conn.commit()
    conn.close()
    flash('خانہ حذف ہو گیا!', 'success')
    return redirect(url_for('settings'))

@app.route('/exam/<int:exam_id>/seating', methods=['GET', 'POST'])
def seating_plan(exam_id):
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        exam_roll_no = request.form.get('exam_roll_no')
        hall_room_no = request.form.get('hall_room_no')
        seat_no = request.form.get('seat_no')
        existing = conn.execute('SELECT id FROM seating_plan WHERE exam_id = ? AND student_id = ?', (exam_id, student_id)).fetchone()
        if existing:
            conn.execute('UPDATE seating_plan SET exam_roll_no=?, hall_room_no=?, seat_no=? WHERE id=?', (exam_roll_no, hall_room_no, seat_no, existing['id']))
        else:
            conn.execute('INSERT INTO seating_plan (exam_id, student_id, exam_roll_no, hall_room_no, seat_no) VALUES (?, ?, ?, ?, ?)', (exam_id, student_id, exam_roll_no, hall_room_no, seat_no))
        conn.commit()
        flash('نشست بندی محفوظ ہو گئی!', 'success')
        return redirect(url_for('seating_plan', exam_id=exam_id))

    students = conn.execute('SELECT * FROM students ORDER BY current_class, CAST(class_roll_no AS INTEGER) ASC').fetchall()
    seating_data = conn.execute('SELECT sp.*, s.student_name, s.father_name, s.current_class, s.class_roll_no FROM seating_plan sp JOIN students s ON sp.student_id = s.id WHERE sp.exam_id = ? ORDER BY sp.id DESC', (exam_id,)).fetchall()
    conn.close()
    return render_template('seating.html', exam=exam, students=students, seating_data=seating_data)

@app.route('/exam/<int:exam_id>/seating/edit/<int:seating_id>', methods=['GET', 'POST'])
def edit_seating(exam_id, seating_id):
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    seating = conn.execute('SELECT sp.*, s.student_name, s.father_name, s.current_class FROM seating_plan sp JOIN students s ON sp.student_id = s.id WHERE sp.id = ? AND sp.exam_id = ?', (seating_id, exam_id)).fetchone()
    if request.method == 'POST':
        conn.execute('UPDATE seating_plan SET exam_roll_no=?, hall_room_no=?, seat_no=? WHERE id=?', (request.form.get('exam_roll_no'), request.form.get('hall_room_no'), request.form.get('seat_no'), seating_id))
        conn.commit()
        conn.close()
        flash('نشست تبدیل ہو گئی!', 'success')
        return redirect(url_for('seating_plan', exam_id=exam_id))
    conn.close()
    return render_template('edit_seating.html', exam=exam, seating=seating)

@app.route('/exam/<int:exam_id>/seating/delete/<int:seating_id>')
def delete_seating(exam_id, seating_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM seating_plan WHERE id = ?', (seating_id,))
    conn.commit()
    conn.close()
    flash('نشست حذف ہو گئی!', 'success')
    return redirect(url_for('seating_plan', exam_id=exam_id))

@app.route('/exam/<int:exam_id>/slip/<int:student_id>')
def exam_roll_slip(exam_id, student_id):
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    seating = conn.execute('SELECT * FROM seating_plan WHERE exam_id = ? AND student_id = ?', (exam_id, student_id)).fetchone()
    conn.close()
    return render_template('exam_slip.html', exam=exam, student=student, seating=seating)

@app.route('/exam/<int:exam_id>/marks/<int:student_id>', methods=['GET', 'POST'])
def marks_entry(exam_id, student_id):
    conn = get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    student = conn.execute('SELECT * FROM students WHERE id = ?', (student_id,)).fetchone()
    if request.method == 'POST':
        books = request.form.getlist('book_name[]')
        totals = request.form.getlist('total_marks[]')
        obtained = request.form.getlist('obtained_marks[]')
        conn.execute('DELETE FROM exam_results WHERE exam_id = ? AND student_id = ?', (exam_id, student_id))
        for b, t, o in zip(books, totals, obtained):
            if b.strip() and o.strip():
                conn.execute('INSERT INTO exam_results (exam_id, student_id, subject_book_name, total_marks, obtained_marks) VALUES (?, ?, ?, ?, ?)', (exam_id, student_id, b.strip(), int(t), int(o)))
        conn.commit()
        flash('نمبرات محفوظ ہو گئے!', 'success')
        return redirect(url_for('marks_entry', exam_id=exam_id, student_id=student_id))

    current_results = conn.execute('SELECT * FROM exam_results WHERE exam_id = ? AND student_id = ?', (exam_id, student_id)).fetchall()
    conn.close()
    return render_template('marks_entry.html', exam=exam, student=student, results=current_results)

@app.route('/export/students')
def export_students_csv():
    conn = get_db_connection()
    students = conn.execute('SELECT * FROM students ORDER BY id ASC').fetchall()
    conn.close()
    output = io.StringIO()
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow(['مدرسہ آئی ڈی', 'رول نمبر', 'فارم نمبر', 'نام طالب علم', 'ولدیت', 'شناختی کارڈ', 'ضلع', 'درجہ', 'رہائشی حیثیت', 'مالی کیفیت', 'فون نمبر', 'تاریخ داخلہ'])
    for s in students:
        writer.writerow([s['id'], s['class_roll_no'] or s['id'], s['admission_form_no'], s['student_name'], s['father_name'], s['student_cnic'] or '', s['district'] or '', s['current_class'], s['residence_status'], s['aid_status'], s['student_phone'] or s['guardian_phone'] or '', s['admission_date'] or ''])
    output.seek(0)
    return Response(output.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment;filename=Madrasa_Students_List.csv"})

# ==== لاگ ان صفحہ ====
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['full_name'] = user['full_name']
            session['role'] = user['role']
            flash('خوش آمدید، ' + (user['full_name'] or user['username']) + '!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('یوزر نیم یا پاسورڈ غلط ہے!', 'danger')

    return render_template('login.html')

# ==== لاگ آؤٹ ====
@app.route('/logout')
def logout():
    session.clear()
    flash('آپ کامیابی سے لاگ آؤٹ ہو گئے ہیں۔', 'success')
    return redirect(url_for('login'))

# ==== پاسورڈ تبدیل کرنا ====
@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

        is_strong, strength_msg = is_password_strong(new_password)

        if not check_password_hash(user['password_hash'], current_password):
            flash('موجودہ پاسورڈ غلط ہے!', 'danger')
        elif new_password != confirm_password:
            flash('نیا پاسورڈ اور تصدیقی پاسورڈ ایک جیسے نہیں ہیں!', 'danger')
        elif not is_strong:
            flash(strength_msg, 'danger')
        else:
            new_hash = generate_password_hash(new_password)
            conn.execute('UPDATE users SET password_hash = ? WHERE id = ?', (new_hash, session['user_id']))
            conn.commit()
            flash('پاسورڈ کامیابی سے تبدیل ہو گیا ہے!', 'success')
            conn.close()
            return redirect(url_for('dashboard'))

        conn.close()

    return render_template('change_password.html')

# ==== ادارے کی معلومات (سیٹنگز) محفوظ کرنا ====
@app.route('/settings/institution', methods=['POST'])
def update_institution_settings():
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی یہ سیٹنگز تبدیل کر سکتے ہیں۔', 'danger')
        return redirect(url_for('settings'))

    institution_name = request.form.get('institution_name', '').strip()
    helpline_number = request.form.get('helpline_number', '').strip()

    conn = get_db_connection()
    conn.execute(
        'UPDATE site_settings SET institution_name = ?, helpline_number = ? WHERE id = 1',
        (institution_name, helpline_number)
    )
    conn.commit()
    conn.close()
    flash('ادارے کی معلومات کامیابی سے محفوظ ہو گئیں!', 'success')
    return redirect(url_for('settings'))

# ==== یوزرز کا انتظام (صرف ایڈمن/مہتمم کے لیے) ====
@app.route('/users', methods=['GET', 'POST'])
def manage_users():
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی یوزرز کا انتظام کر سکتے ہیں۔', 'danger')
        return redirect(url_for('dashboard'))

    conn = get_db_connection()

    if request.method == 'POST':
        username = request.form['username'].strip()
        full_name = request.form['full_name'].strip()
        password = request.form['password']
        role = request.form['role']

        existing = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        is_strong, strength_msg = is_password_strong(password)

        if existing:
            flash('یہ یوزر نیم پہلے سے موجود ہے، دوسرا منتخب کریں۔', 'danger')
        elif not is_strong:
            flash(strength_msg, 'danger')
        else:
            hashed_pw = generate_password_hash(password)
            conn.execute(
                'INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)',
                (username, hashed_pw, full_name, role)
            )
            conn.commit()
            flash('نیا یوزر کامیابی سے بن گیا ہے!', 'success')

    all_users = conn.execute('SELECT * FROM users ORDER BY id ASC').fetchall()
    conn.close()
    return render_template('manage_users.html', all_users=all_users)


# ==== یوزر حذف کرنا ====
@app.route('/users/delete/<int:user_id>')
def delete_user(user_id):
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی یوزرز حذف کر سکتے ہیں۔', 'danger')
        return redirect(url_for('dashboard'))

    if user_id == session.get('user_id'):
        flash('آپ اپنا ہی اکاؤنٹ حذف نہیں کر سکتے!', 'danger')
        return redirect(url_for('manage_users'))

    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    flash('یوزر حذف کر دیا گیا ہے۔', 'success')
    return redirect(url_for('manage_users'))

# ==== بیک اپس دیکھنا (صرف ایڈمن) ====
@app.route('/backups')
def view_backups():
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی بیک اپس دیکھ سکتے ہیں۔', 'danger')
        return redirect(url_for('dashboard'))

    backup_list = []
    if os.path.exists(BACKUP_FOLDER):
        files = sorted(os.listdir(BACKUP_FOLDER), reverse=True)
        for f in files:
            if f.startswith('madrasa_backup_'):
                full_path = os.path.join(BACKUP_FOLDER, f)
                size_kb = round(os.path.getsize(full_path) / 1024, 1)
                backup_list.append({'filename': f, 'size_kb': size_kb})

    return render_template('backups.html', backup_list=backup_list)


# ==== ابھی نیا بیک اپ بنانا ====
@app.route('/backups/create')
def create_backup_now():
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی بیک اپ بنا سکتے ہیں۔', 'danger')
        return redirect(url_for('dashboard'))

    result = create_backup()
    if result:
        flash('نیا بیک اپ کامیابی سے بن گیا ہے: ' + result, 'success')
    else:
        flash('بیک اپ بنانے میں مسئلہ ہوا — ڈیٹا بیس فائل نہیں ملی۔', 'danger')
    return redirect(url_for('view_backups'))


# ==== بیک اپ فائل ڈاؤنلوڈ کرنا ====
@app.route('/backups/download/<filename>')
def download_backup(filename):
    if session.get('role') != 'admin':
        flash('صرف مہتمم ہی بیک اپ ڈاؤنلوڈ کر سکتے ہیں۔', 'danger')
        return redirect(url_for('dashboard'))

    safe_path = os.path.join(BACKUP_FOLDER, filename)
    if os.path.exists(safe_path) and filename.startswith('madrasa_backup_'):
        return send_from_directory(BACKUP_FOLDER, filename, as_attachment=True)
    flash('یہ بیک اپ فائل نہیں ملی۔', 'danger')
    return redirect(url_for('view_backups'))

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5001))
    app.run(debug=False, host='0.0.0.0', port=port)