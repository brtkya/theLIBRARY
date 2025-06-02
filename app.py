from flask import Flask, redirect, url_for, session
from config import Config
from models import init_db
from routes.auth import auth_bp
from routes.books import books_bp
from routes.borrow import borrow_bp

app = Flask(__name__)
app.config.from_object(Config)

app.register_blueprint(auth_bp)
app.register_blueprint(books_bp)
app.register_blueprint(borrow_bp)

@app.route('/')
def index():
    if 'email' in session:
        return redirect(url_for('books.home'))
    return redirect(url_for('auth.login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
