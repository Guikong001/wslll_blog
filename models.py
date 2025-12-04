from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class SiteSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_name = db.Column(db.String(100), default="My Blog")
    about_content = db.Column(db.Text, nullable=True)
    about_content_en = db.Column(db.Text, nullable=True)
    social_links = db.Column(db.Text, default="[]") # JSON string
    logo_filename = db.Column(db.String(200), nullable=True)
    deepseek_api_key = db.Column(db.String(200), nullable=True)
    notification_content = db.Column(db.Text, nullable=True) # Global Notification Content
    theme = db.Column(db.String(20), default='dark') # 'dark' or 'white'

    def get_social_links(self):
        try:
            return json.loads(self.social_links)
        except:
            return []

class OTP(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), index=True)
    code = db.Column(db.String(10))
    timestamp = db.Column(db.Float)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    posts = db.relationship('Post', backref='category', lazy=True)

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    title_en = db.Column(db.String(200), nullable=True) # English Title
    content = db.Column(db.Text, nullable=False) # Markdown content (Chinese/Original)
    content_en = db.Column(db.Text, nullable=True) # Markdown content (English Translation)
    summary_zh = db.Column(db.Text, nullable=True) # AI Summary (Chinese)
    summary_en = db.Column(db.Text, nullable=True) # AI Summary (English)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    custom_author = db.Column(db.String(100), nullable=True) # Manually set author name
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)

class Photo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(100), nullable=False)
    title = db.Column(db.String(100))
    title_en = db.Column(db.String(100)) # English Title
    description = db.Column(db.String(200))
    description_en = db.Column(db.String(200)) # English Description
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
