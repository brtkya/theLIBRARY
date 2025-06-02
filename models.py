import sqlite3
from pymongo import MongoClient
from config import Config

DATABASE = Config.DATABASE

mongo_client = MongoClient(Config.MONGO_URI)
mongo_db = mongo_client['library_management']
comments_collection = mongo_db['book_comments']

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        Student_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Email TEXT UNIQUE NOT NULL,
        Major TEXT
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS librarians (
        Librarian_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT NOT NULL,
        Email TEXT UNIQUE NOT NULL
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS books (
        Book_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Title TEXT NOT NULL,
        Author TEXT NOT NULL,
        Genre TEXT,
        ISBN TEXT UNIQUE,
        Copies_Available INTEGER NOT NULL,
        Publisher TEXT,
        Edition TEXT,
        Summary TEXT
    )
    ''')

    c.execute('''
    CREATE TABLE IF NOT EXISTS borrowing (
        Borrow_ID INTEGER PRIMARY KEY AUTOINCREMENT,
        Book_ID INTEGER NOT NULL,
        Student_ID INTEGER NOT NULL,
        Borrow_Date TEXT NOT NULL,
        Return_Date TEXT,
        Status TEXT NOT NULL,
        FOREIGN KEY (Book_ID) REFERENCES books(Book_ID),
        FOREIGN KEY (Student_ID) REFERENCES students(Student_ID)
    )
    ''')

    conn.commit()
    conn.close()
    print("Database and tables ensured.")
