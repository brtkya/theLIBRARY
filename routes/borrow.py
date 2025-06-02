from flask import Blueprint, render_template, request, redirect, url_for, session, flash, Response
from models import get_db_connection
import datetime
import xml.etree.ElementTree as ET

borrow_bp = Blueprint('borrow', __name__)

@borrow_bp.route('/my_books')
def my_books():
    if 'email' not in session or session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    student = conn.execute('SELECT Student_ID FROM students WHERE Email = ?', (session['email'],)).fetchone()
    if not student:
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('books.home'))
    borrowed_books = conn.execute('''
        SELECT br.Borrow_ID, b.Book_ID as Book_ID, b.Title, b.Author, b.Genre, br.Borrow_Date, br.Return_Date, br.Status
        FROM borrowing br
        JOIN books b ON br.Book_ID = b.Book_ID
        WHERE br.Student_ID = ? AND (br.Status = 'borrowed' OR br.Status = 'overdue')
        ORDER BY datetime(br.Borrow_Date) DESC
    ''', (student['Student_ID'],)).fetchall()
    today = datetime.datetime.now().date()
    for book in borrowed_books:
        if book['Return_Date']:
            return_date = datetime.datetime.strptime(book['Return_Date'], '%Y-%m-%d').date()
            if book['Status'] == 'borrowed' and today > return_date:
                conn.execute('UPDATE borrowing SET Status = ? WHERE Borrow_ID = ?', ('overdue', book['Borrow_ID']))
    conn.commit()
    borrowed_books = conn.execute('''
        SELECT b.Book_ID as Book_ID, b.Title, b.Author, b.Genre, br.Borrow_Date, br.Return_Date, br.Status
        FROM borrowing br
        JOIN books b ON br.Book_ID = b.Book_ID
        WHERE br.Student_ID = ? AND (br.Status = 'borrowed' OR br.Status = 'overdue')
        ORDER BY datetime(br.Borrow_Date) DESC
    ''', (student['Student_ID'],)).fetchall()
    conn.close()
    return render_template('my_books.html', borrowed_books=borrowed_books)

@borrow_bp.route('/borrow_book/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    if 'email' not in session or session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    student = conn.execute('SELECT Student_ID FROM students WHERE Email = ?', (session['email'],)).fetchone()
    book = conn.execute('SELECT * FROM books WHERE Book_ID = ?', (book_id,)).fetchone()
    if not student or not book:
        conn.close()
        flash('Book or student not found.', 'danger')
        return redirect(url_for('books.home'))
    already_borrowed = conn.execute('''SELECT * FROM borrowing WHERE Book_ID = ? AND Student_ID = ? AND Status = 'borrowed' ''', (book_id, student['Student_ID'])).fetchone()
    if already_borrowed:
        conn.close()
        flash('You have already borrowed this book and not returned it yet.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    if book['Copies_Available'] <= 0:
        conn.close()
        flash('No copies available to borrow.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    borrow_date = datetime.datetime.now().strftime('%Y-%m-%d')
    return_date = request.form.get('return_date')
    if not return_date:
        conn.close()
        flash('Please select a return date before borrowing.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    try:
        conn.execute('''INSERT INTO borrowing (Book_ID, Student_ID, Borrow_Date, Return_Date, Status) VALUES (?, ?, ?, ?, ?)''', (book_id, student['Student_ID'], borrow_date, return_date, 'borrowed'))
        conn.execute('''UPDATE books SET Copies_Available = Copies_Available - 1 WHERE Book_ID = ?''', (book_id,))
        conn.commit()
        flash('Book borrowed successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('books.book_detail', book_id=book_id))

@borrow_bp.route('/return_book/<int:book_id>', methods=['POST'])
def return_book(book_id):
    if 'email' not in session or session.get('role') != 'student':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    student = conn.execute('SELECT Student_ID FROM students WHERE Email = ?', (session['email'],)).fetchone()
    if not student:
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('borrow.my_books'))
    borrowing = conn.execute('''SELECT * FROM borrowing WHERE Book_ID = ? AND Student_ID = ? AND (Status = 'borrowed' OR Status = 'overdue') ''', (book_id, student['Student_ID'])).fetchone()
    if not borrowing:
        conn.close()
        flash('No active borrowing record found for this book.', 'warning')
        return redirect(url_for('borrow.my_books'))
    try:
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        conn.execute('''UPDATE borrowing SET Status = 'returned', Return_Date = ? WHERE Borrow_ID = ?''', (today, borrowing['Borrow_ID']))
        conn.execute('''UPDATE books SET Copies_Available = Copies_Available + 1 WHERE Book_ID = ?''', (book_id,))
        conn.commit()
        flash('Book returned successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('borrow.my_books'))

@borrow_bp.route('/borrowings')
def borrowings():
    if 'email' not in session or session.get('role') != 'librarian':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    borrowed = conn.execute('''
        SELECT br.Borrow_ID, b.Title, b.Author, b.Genre, s.Name as Student_Name, s.Email as Student_Email, br.Borrow_Date, br.Return_Date
        FROM borrowing br
        JOIN books b ON br.Book_ID = b.Book_ID
        JOIN students s ON br.Student_ID = s.Student_ID
        WHERE br.Status = 'borrowed'
        ORDER BY datetime(br.Borrow_Date) DESC
    ''').fetchall()
    overdue = conn.execute('''
        SELECT br.Borrow_ID, b.Title, b.Author, b.Genre, s.Name as Student_Name, s.Email as Student_Email, br.Borrow_Date, br.Return_Date
        FROM borrowing br
        JOIN books b ON br.Book_ID = b.Book_ID
        JOIN students s ON br.Student_ID = s.Student_ID
        WHERE br.Status = 'overdue'
        ORDER BY datetime(br.Borrow_Date) DESC
    ''').fetchall()
    conn.close()
    return render_template('borrowings.html', borrowed=borrowed, overdue=overdue)

@borrow_bp.route('/export_borrowings_xml')
def export_borrowings_xml():
    if 'email' not in session or session.get('role') != 'librarian':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    borrowings = conn.execute('''
        SELECT br.Borrow_ID, b.Title, b.Author, b.Genre, s.Name as Student_Name, s.Email as Student_Email, br.Borrow_Date, br.Return_Date, br.Status
        FROM borrowing br
        JOIN books b ON br.Book_ID = b.Book_ID
        JOIN students s ON br.Student_ID = s.Student_ID
        ORDER BY datetime(br.Borrow_Date) DESC
    ''').fetchall()
    conn.close()
    root = ET.Element('Borrowings')
    for b in borrowings:
        record = ET.SubElement(root, 'Borrowing')
        for key in b.keys():
            child = ET.SubElement(record, key)
            child.text = str(b[key]) if b[key] is not None else ''
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')
    return Response(xml_str, mimetype='application/xml', headers={
        'Content-Disposition': 'attachment; filename=borrowings.xml'
    })

@borrow_bp.route('/export_overdue_xml')
def export_overdue_xml():
    if 'email' not in session or session.get('role') != 'librarian':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    overdue = conn.execute('''
        SELECT br.Borrow_ID, b.Title, b.Author, b.Genre, s.Name as Student_Name, s.Email as Student_Email, br.Borrow_Date, br.Return_Date, br.Status
        FROM borrowing br
        JOIN books b ON br.Book_ID = b.Book_ID
        JOIN students s on br.Student_ID = s.Student_ID
        WHERE br.Status = 'overdue'
        ORDER BY datetime(br.Borrow_Date) DESC
    ''').fetchall()
    conn.close()
    root = ET.Element('OverdueBorrowings')
    for b in overdue:
        record = ET.SubElement(root, 'Borrowing')
        for key in b.keys():
            child = ET.SubElement(record, key)
            child.text = str(b[key]) if b[key] is not None else ''
    xml_str = ET.tostring(root, encoding='utf-8', method='xml')
    return Response(xml_str, mimetype='application/xml', headers={
        'Content-Disposition': 'attachment; filename=overdue_borrowings.xml'
    })
