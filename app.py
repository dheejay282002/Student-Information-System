from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import os
from fpdf import FPDF
import pandas as pd

app = Flask(__name__)
app.secret_key = 'your_secret_key'

DB = 'sis.db'

# Ensure database is initialized
def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS admins (
        username TEXT PRIMARY KEY, 
        password TEXT
    );
    CREATE TABLE IF NOT EXISTS students (
        id TEXT PRIMARY KEY, 
        name TEXT, 
        age INTEGER, 
        year_level INTEGER, 
        section TEXT, 
        course TEXT
    );
    CREATE TABLE IF NOT EXISTS courses (
        course TEXT PRIMARY KEY, 
        sections TEXT
    );
    CREATE TABLE IF NOT EXISTS subjects (
        subject TEXT, 
        course TEXT, 
        section TEXT, 
        year INTEGER
    );
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY, 
        name TEXT, 
        age INTEGER, 
        role TEXT, 
        username TEXT, 
        password TEXT, 
        course TEXT, 
        section TEXT, 
        year INTEGER, 
        subjects TEXT
    );
    CREATE TABLE IF NOT EXISTS grades (
        student_id TEXT, 
        subject TEXT, 
        grade REAL
    );
    """)
    cursor.execute("INSERT OR IGNORE INTO admins VALUES (?, ?)", ("admin", "password123"))
    conn.commit()
    conn.close()

init_db()

# Utility function
def get_db():
    return sqlite3.connect(DB)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE username = ? AND password = ?", (username, password))
        if cursor.fetchone():
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials!')
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    return render_template('admin_dashboard.html')

@app.route('/admin/add_student', methods=['GET', 'POST'])
def add_student():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    if request.method == 'POST':
        student_id = request.form['id']
        name = request.form['name']
        age = request.form['age']
        year = request.form['year_level']
        section = request.form['section']
        course = request.form['course']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO students VALUES (?, ?, ?, ?, ?, ?)", (student_id, name, age, year, section, course))
        conn.commit()
        flash('Student added successfully!')
        return redirect(url_for('admin_dashboard'))
    return render_template('add_student.html')

@app.route('/admin/view_students')
def view_students():
    if 'admin' not in session:
        return redirect(url_for('admin_login'))
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()
    return render_template('view_students.html', students=students)

@app.route('/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        role = request.form['role']
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ? AND password = ? AND role = ?", (username, password, role))
        user = cursor.fetchone()
        if user:
            session['user'] = username
            session['role'] = role
            session['user_id'] = user[0]
            return redirect(url_for('user_dashboard'))
        flash('Invalid credentials!')
    return render_template('user_login.html')

@app.route('/dashboard')
def user_dashboard():
    if 'user' not in session:
        return redirect(url_for('user_login'))
    return render_template('user_dashboard.html', role=session['role'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.route('/grades')
def view_grades():
    if 'user_id' not in session:
        return redirect(url_for('user_login'))
    student_id = session['user_id']
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
    grades = cursor.fetchall()
    return render_template('grades.html', grades=grades)

@app.route('/export_students')
def export_students():
    conn = get_db()
    df = pd.read_sql_query("SELECT * FROM students", conn)
    file_path = 'students.xlsx'
    df.to_excel(file_path, index=False)
    return send_file(file_path, as_attachment=True)

@app.route('/export_grades_pdf')
def export_grades_pdf():
    student_id = session.get('user_id')
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, course, year FROM users WHERE id = ?", (student_id,))
    student = cursor.fetchone()

    if not student:
        flash('Student not found!')
        return redirect(url_for('user_dashboard'))

    name, course, year = student
    cursor.execute("SELECT subject, grade FROM grades WHERE student_id = ?", (student_id,))
    grades = cursor.fetchall()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Certificate of Grades", ln=True, align='C')
    pdf.cell(200, 10, txt=f"Student: {name}", ln=True)
    pdf.cell(200, 10, txt=f"Course: {course}, Year: {year}", ln=True)

    pdf.cell(90, 10, txt="Subject", border=1)
    pdf.cell(50, 10, txt="Grade", border=1, ln=True)
    for subject, grade in grades:
        pdf.cell(90, 10, txt=subject, border=1)
        pdf.cell(50, 10, txt=str(grade), border=1, ln=True)

    filename = f"{student_id}_grades.pdf"
    pdf.output(filename)
    return send_file(filename, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
