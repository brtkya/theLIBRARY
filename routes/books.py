from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import get_db_connection, comments_collection
import datetime

books_bp = Blueprint('books', __name__)

@books_bp.route('/home', methods=['GET', 'POST'])
def home():
    if 'email' not in session:
        return redirect(url_for('auth.login'))
    search_query = request.args.get('search', '').strip()
    conn = get_db_connection()
    if search_query:
        books = conn.execute('SELECT * FROM books WHERE Title LIKE ?', (f'%{search_query}%',)).fetchall()
    else:
        books = conn.execute('SELECT * FROM books').fetchall()
    conn.close()
    return render_template('home.html', email=session['email'], user_role=session['role'], books=books, search_query=search_query)

@books_bp.route('/add_book', methods=['GET', 'POST'])
def add_book():
    if 'email' not in session or session.get('role') != 'librarian':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        genre = request.form.get('genre', '').strip()
        isbn = request.form.get('isbn', '').strip()
        copies = request.form.get('copies_available', '0').strip()
        publisher = request.form.get('publisher', '').strip()
        edition = request.form.get('edition', '').strip()
        summary = request.form.get('summary', '').strip()
        try:
            copies = int(copies)
        except ValueError:
            copies = 0
        conn = get_db_connection()
        try:
            conn.execute('''
                INSERT INTO books (Title, Author, Genre, ISBN, Copies_Available, Publisher, Edition, Summary)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (title, author, genre, isbn, copies, publisher, edition, summary))
            conn.commit()
            flash('Book added successfully!', 'success')
            return render_template('add_book.html')
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
            return render_template('add_book.html')
        finally:
            conn.close()
    return render_template('add_book.html')

@books_bp.route('/book/<int:book_id>')
def book_detail(book_id):
    if 'email' not in session:
        flash("Please log in first.", "warning")
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE Book_ID = ?', (book_id,)).fetchone()
    conn.close()
    if book is None:
        flash("Book not found.", "danger")
        return redirect(url_for('books.home'))
    publisher = book['Publisher'] if book['Publisher'] else ''
    edition = book['Edition'] if book['Edition'] else ''
    summary = book['Summary'] if book['Summary'] else ''
    comments = list(comments_collection.find({'book_id': book_id}))
    return render_template('book_detail.html', book=book, user_role=session.get('role'), comments=comments, publisher=publisher, edition=edition, summary=summary)

@books_bp.route('/book/<int:book_id>/comment', methods=['POST'])
def add_book_comment(book_id):
    if 'email' not in session or session.get('role') != 'student':
        flash('You must be logged in as a student to comment.', 'danger')
        return redirect(url_for('auth.login'))
    comment = request.form.get('comment', '').strip()
    rating = request.form.get('rating', '').strip()
    if not comment or not rating:
        flash('Please provide both a comment and a rating.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValueError
    except ValueError:
        flash('Rating must be an integer between 1 and 5.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    conn = get_db_connection()
    student = conn.execute('SELECT Name, Student_ID FROM students WHERE Email = ?', (session['email'],)).fetchone()
    if not student:
        conn.close()
        flash('Student not found.', 'danger')
        return redirect(url_for('books.book_detail', book_id=book_id))
    borrowed = conn.execute('''SELECT * FROM borrowing WHERE Book_ID = ? AND Student_ID = ?''', (book_id, student['Student_ID'])).fetchone()
    conn.close()
    if not borrowed:
        flash('You can only comment or rate books you have borrowed.', 'warning')
        return redirect(url_for('books.book_detail', book_id=book_id))
    student_name = student['Name']
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    existing = comments_collection.find_one({'book_id': book_id, 'student_email': session['email']})
    comment_doc = {
        'book_id': book_id,
        'student_email': session['email'],
        'student_name': student_name,
        'comment': comment,
        'rating': rating,
        'date': now_str
    }
    if existing:
        comments_collection.update_one(
            {'_id': existing['_id']},
            {'$set': comment_doc}
        )
        flash('Your previous comment and rating have been updated!', 'success')
    else:
        comments_collection.insert_one(comment_doc)
        flash('Your comment and rating have been submitted!', 'success')
    return redirect(url_for('books.book_detail', book_id=book_id))

@books_bp.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
def edit_book(book_id):
    if 'email' not in session or session.get('role') != 'librarian':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    book = conn.execute('SELECT * FROM books WHERE Book_ID = ?', (book_id,)).fetchone()
    if not book:
        conn.close()
        flash('Book not found.', 'danger')
        return redirect(url_for('books.home'))
    if request.method == 'POST':
        title = request.form['title'].strip()
        author = request.form['author'].strip()
        genre = request.form.get('genre', '').strip()
        isbn = request.form.get('isbn', '').strip()
        copies = request.form.get('copies_available', '0').strip()
        publisher = request.form.get('publisher', '').strip()
        edition = request.form.get('edition', '').strip()
        summary = request.form.get('summary', '').strip()
        try:
            copies = int(copies)
        except ValueError:
            copies = 0
        try:
            conn.execute('''UPDATE books SET Title=?, Author=?, Genre=?, ISBN=?, Copies_Available=?, Publisher=?, Edition=?, Summary=? WHERE Book_ID=?''',
                (title, author, genre, isbn, copies, publisher, edition, summary, book_id))
            conn.commit()
            flash('Book updated successfully!', 'success')
            return redirect(url_for('books.book_detail', book_id=book_id))
        except Exception as e:
            conn.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
        finally:
            conn.close()
    else:
        conn.close()
    return render_template('edit_book.html', book=book)

@books_bp.route('/delete_book/<int:book_id>', methods=['POST'])
def delete_book(book_id):
    if 'email' not in session or session.get('role') != 'librarian':
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM books WHERE Book_ID = ?', (book_id,))
        conn.commit()
        flash('Book deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('books.home'))
