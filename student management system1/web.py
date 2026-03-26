from flask import Flask, render_template, request, redirect, url_for, session, flash
from sms_app.db import Database
from sms_app.security import hash_password, verify_password
from sms_app.reports import build_student_report, export_report_to_pdf, mark_to_grade
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key')

primary_path = "students.db"
fallback_path = "students_web.db"

db = Database(primary_path)
try:
    db.migrate()
except Exception as e:
    # If DB is locked, fall back to a separate database so the web app can still run.
    if "locked" in str(e).lower():
        try:
            db.close()
        except Exception:
            pass
        db = Database(fallback_path)
        db.migrate()
    else:
        raise


@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        try:
            user = db.authenticate(username, password)
        except Exception as e:
            app.logger.exception("Login error")
            flash('Internal error during login')
            return render_template('login.html')

        if user:
            session['username'] = user.username
            session['role'] = user.role
            return redirect(url_for('dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        if password != confirm:
            flash('Passwords do not match')
            return redirect(url_for('register'))
        try:
            db.create_user(username, password, 'staff')
            flash('Account created successfully, please log in')
            return redirect(url_for('login'))
        except Exception as e:
            flash(str(e))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    stats = db.get_dashboard_stats()
    return render_template('dashboard.html', stats=stats, user=session)

@app.route('/students')
def students():
    if 'username' not in session:
        return redirect(url_for('login'))
    students_list = db.list_students()
    classes = db.list_classes()
    return render_template('students.html', students=students_list, classes=classes)

@app.route('/students/add', methods=['GET', 'POST'])
def add_student():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        sid = request.form['student_id']
        name = request.form['name']
        program = request.form.get('program', '')
        class_id = request.form.get('class_id')
        try:
            db.add_student(sid, name, program, int(class_id) if class_id else None)
            flash('Student added successfully')
            return redirect(url_for('students'))
        except Exception as e:
            flash(str(e))
    classes = db.list_classes()
    return render_template('student_form.html', classes=classes, action='Add')

@app.route('/students/edit/<sid>', methods=['GET', 'POST'])
def edit_student(sid):
    if 'username' not in session:
        return redirect(url_for('login'))
    student = db.get_student(sid)
    if not student:
        flash('Student not found')
        return redirect(url_for('students'))
    if request.method == 'POST':
        name = request.form['name']
        program = request.form.get('program', '')
        class_id = request.form.get('class_id')
        try:
            db.update_student(sid, name=name, program=program, class_id=int(class_id) if class_id else None)
            flash('Student updated successfully')
            return redirect(url_for('students'))
        except Exception as e:
            flash(str(e))
    classes = db.list_classes()
    return render_template('student_form.html', student=student, classes=classes, action='Edit')

@app.route('/students/delete/<sid>')
def delete_student(sid):
    if 'username' not in session:
        return redirect(url_for('login'))
    try:
        db.delete_student(sid)
        flash('Student deleted successfully')
    except Exception as e:
        flash(str(e))
    return redirect(url_for('students'))

@app.route('/marks')
def marks():
    if 'username' not in session:
        return redirect(url_for('login'))
    marks_list = db.list_marks()
    students = db.list_students()
    subjects = db.list_subjects()
    return render_template('marks.html', marks=marks_list, students=students, subjects=subjects)

@app.route('/marks/add', methods=['POST'])
def add_mark():
    if 'username' not in session:
        return redirect(url_for('login'))
    student_id = request.form['student_id']
    subject_id = int(request.form['subject_id'])
    term = request.form['term']
    mark = int(request.form['mark'])
    try:
        db.set_mark(student_id, subject_id, term, mark)
        flash('Mark added successfully')
    except Exception as e:
        flash(str(e))
    return redirect(url_for('marks'))

@app.route('/reports')
def reports():
    if 'username' not in session:
        return redirect(url_for('login'))
    students = db.list_students()
    return render_template('reports.html', students=students)

@app.route('/reports/generate/<sid>')
def generate_report(sid):
    if 'username' not in session:
        return redirect(url_for('login'))
    student = db.get_student(sid)
    if not student:
        flash('Student not found')
        return redirect(url_for('reports'))
    marks = db.get_student_marks(sid)
    report_data = build_student_report(
        student_id=student['student_id'],
        name=student['name'],
        program=student['program'] or '',
        class_name=student['class_name'],
        marks=[(m['subject'], m['term'], m['mark']) for m in marks]
    )
    export_report_to_pdf(report_data, f"report_{sid}.pdf")
    flash('Report generated successfully')
    return redirect(url_for('reports'))

@app.route('/classes')
def classes():
    if 'username' not in session:
        return redirect(url_for('login'))
    classes_list = db.list_classes()
    return render_template('classes.html', classes=classes_list)

@app.route('/classes/add', methods=['GET', 'POST'])
def add_class():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        try:
            db.upsert_class(name)
            flash('Class added successfully')
            return redirect(url_for('classes'))
        except Exception as e:
            flash(str(e))
    return render_template('class_form.html')

@app.route('/subjects')
def subjects():
    if 'username' not in session:
        return redirect(url_for('login'))
    subjects_list = db.list_subjects()
    return render_template('subjects.html', subjects=subjects_list)

@app.route('/subjects/add', methods=['GET', 'POST'])
def add_subject():
    if 'username' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        try:
            db.upsert_subject(name)
            flash('Subject added successfully')
            return redirect(url_for('subjects'))
        except Exception as e:
            flash(str(e))
    return render_template('subject_form.html')

@app.route('/users')
def users():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    users_list = db.list_users()
    return render_template('users.html', users=users_list)

@app.route('/users/add', methods=['GET', 'POST'])
def add_user():
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        try:
            db.create_user(username, password, role)
            flash('User added successfully')
            return redirect(url_for('users'))
        except Exception as e:
            flash(str(e))
    return render_template('user_form.html', action='Add')

@app.route('/users/delete/<int:uid>')
def delete_user(uid):
    if 'username' not in session or session.get('role') != 'admin':
        return redirect(url_for('dashboard'))
    try:
        db.delete_user(uid)
        flash('User deleted successfully')
    except Exception as e:
        flash(str(e))
    return redirect(url_for('users'))

if __name__ == '__main__':
    app.run(debug=True)