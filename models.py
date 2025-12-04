from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class SiteSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blog_name = db.Column(db.String(100), default="Wslll Blog")
    logo_filename = db.Column(db.String(100), nullable=True)
    about_content = db.Column(db.Text, default="# About Me\n\nHi, I'm a photographer and developer.")
    about_content_en = db.Column(db.Text, nullable=True) # English Translation
    social_links = db.Column(db.Text, default='[{"icon": "fab fa-github", "url": "#"}, {"icon": "fab fa-twitter", "url": "#"}, {"icon": "fas fa-envelope", "url": "#"}]')
    deepseek_api_key = db.Column(db.String(200), nullable=True)
    notification_content = db.Column(db.Text, nullable=True) # Global Notification Content

    def get_social_links(self):
        try:
            return json.loads(self.social_links)
        except:
            return []

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
