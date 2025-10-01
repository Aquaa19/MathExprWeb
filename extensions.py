# MathExprWeb/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# Create extension objects
db = SQLAlchemy()
login_manager = LoginManager()