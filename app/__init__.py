from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os

# Initialize Flask app
app = Flask(__name__)

# Enable 'do' extension in Jinja2
app.jinja_env.add_extension('jinja2.ext.do')

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'timetable.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your-secret-key'

# Create uploads folder
upload_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)
app.config['UPLOAD_FOLDER'] = upload_folder

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Import routes after initializing app to avoid circular imports
from app import routes 