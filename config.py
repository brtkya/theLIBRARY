import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your_secret_key')
    DATABASE = os.environ.get('DATABASE', 'library.db')
    MONGO_URI = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
