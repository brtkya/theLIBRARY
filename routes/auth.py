from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        conn = get_db_connection()
        user = conn.execute(
            '''
            SELECT Student_ID AS ID, Name, Email, Major FROM students WHERE Email = ?
            UNION
            SELECT Librarian_ID AS ID, Name, Email, NULL AS Major FROM librarians WHERE Email = ?
            ''',
            (email, email)
        ).fetchone()
        conn.close()

        if user:
            session['email'] = user['Email']
            session['name'] = user['Name']
            session['role'] = 'student' if user['Major'] is not None else 'librarian'
            return redirect(url_for('books.home'))
        else:
            flash('Email not found. Please enter a valid email.', 'danger')

    return render_template('login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        role = request.form['role']
        major = request.form.get('major', '').strip()

        conn = get_db_connection()

        existing_user = conn.execute(
            'SELECT Email FROM students WHERE Email = ? UNION SELECT Email FROM librarians WHERE Email = ?',
            (email, email)
        ).fetchone()

        if existing_user:
            flash('This email is already registered.', 'danger')
            conn.close()
            return redirect(url_for('auth.register'))

        try:
            if role == 'student':
                if not major:
                    major = 'Unknown'
                conn.execute(
                    'INSERT INTO students (Name, Email, Major) VALUES (?, ?, ?)',
                    (name, email, major)
                )
            else:
                conn.execute(
                    'INSERT INTO librarians (Name, Email) VALUES (?, ?)',
                    (name, email)
                )
            conn.commit()
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            conn.close()
            return redirect(url_for('auth.register'))
        finally:
            conn.close()
        flash('Registration successful, you can now log in.', 'success')
        return render_template('register.html')

    return render_template('register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))
