from gevent import monkey
monkey.patch_all()

import os
import requests
import random
import string
import time
import json
import threading
import uuid
from datetime import timedelta, datetime
from flask import Flask, render_template, request, redirect, url_for, flash, abort, send_from_directory, jsonify, session, Response, stream_with_context
import jinja2
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Post, Category, Photo, SiteSetting, OTP
import markdown
from openai import OpenAI

app = Flask(__name__)

# Configure Jinja2 to look in default template directory
# We will rely on subdirectories 'code_black', 'simple_white', and 'templates_optional' for switching
app.jinja_loader = jinja2.ChoiceLoader([
    jinja2.FileSystemLoader(os.path.join(app.root_path, 'templates')),
    jinja2.PrefixLoader({
        'opt': jinja2.FileSystemLoader(os.path.join(app.root_path, 'templates_optional'))
    })
])
# change the secret key to a random string, you can use "openssl rand -hex 32"
#app.config['SECRET_KEY'] = 'your_secret_key_here'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_secret_key_here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static/uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max-limit
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=14) # 14 days login session

# Define template folder based on theme is handled dynamically, but Flask needs a default
# We will override render_template behavior or pass the correct folder
# Simpler approach: Override flask's template folder path per request or use a helper

def get_template_path(template_name):
    """
    Returns the correct template path based on current theme.
    Strategy:
    - Check session['theme'] first.
    - Fallback to SiteSetting.theme.
    - Default to 'code_black'.
    """
    theme = session.get('theme')
    
    if not theme:
        settings = SiteSetting.query.first()
        if settings and settings.theme:
            # Map old values if necessary, or assume they match folder names
            # Old values: 'dark', 'white'
            # New folder names: 'code_black', 'simple_white'
            if settings.theme == 'dark':
                theme = 'code_black'
            elif settings.theme == 'white':
                theme = 'simple_white'
            else:
                theme = settings.theme
        else:
            theme = 'code_black'
            
    # Ensure theme is one of the supported ones or optional
    # For now, we assume theme name matches folder name in templates/
    # If it starts with opt/, it's in templates_optional
    
    if theme == 'code_black':
        return f"code_black/{template_name}"
    elif theme == 'simple_white':
        return f"simple_white/{template_name}"
    else:
        # Assume future templates are passed as "opt/theme_name" or similar
        # But for now, let's just fallback to code_black if unknown
        return f"code_black/{template_name}"

@app.route('/toggle-theme')
def toggle_theme():
    current_theme = session.get('theme')
    # Check SiteSetting if session is empty
    if not current_theme:
        settings = SiteSetting.query.first()
        if settings and settings.theme == 'white':
            current_theme = 'simple_white'
        else:
            current_theme = 'code_black'
            
    if current_theme == 'simple_white':
        session['theme'] = 'code_black'
    else:
        session['theme'] = 'simple_white'
        
    return redirect(request.referrer or url_for('index'))

# # DeepSeek Configuration
# DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
# DEEPSEEK_API_KEY = 'use_your_own_key'

# DeepSeek Configuration
DEEPSEEK_BASE_URL = 'https://api.deepseek.com'
DEEPSEEK_API_KEY = 'use_your_own_key'

def get_deepseek_key(): 
    # Try database first
    with app.app_context():
        try:
            settings = SiteSetting.query.first()
            if settings and settings.deepseek_api_key:
                return settings.deepseek_api_key
        except:
            pass
    # Fallback to hardcoded (or env var)
    return DEEPSEEK_API_KEY

# # Configuration for SMS Login
# ALLOWED_PHONE = 'use_your_own_phone'
# Spug_SMS_Template_Code = 'use_your_own_Spug_template_code'
# OTP_STORE = {} # Format: {phone: {'code': '123456', 'timestamp': 1234567890}}

# Configuration for SMS Login
ALLOWED_PHONE = 'use_your_own_phone'
Spug_SMS_Template_Code = 'use_your_own_Spug_template_code'
# OTP_STORE = {} # Removed in favor of DB storage

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

import re

# ... (existing code)

@app.context_processor
def inject_site_settings():
    settings = SiteSetting.query.first()
    if not settings:
        settings = SiteSetting() # Default
    
    # Get current language from session, default to 'zh'
    current_lang = session.get('lang', 'zh')
    
    # Parse notifications
    notifications = []
    if settings.notification_content:
        # Extract content between <notice> tags
        matches = re.findall(r'<notice>(.*?)</notice>', settings.notification_content, re.DOTALL)
        if matches:
            for match in matches:
                notifications.append(markdown.markdown(match.strip()))
        elif settings.notification_content.strip():
            # Fallback: if no tags, treat entire content as one notice
            notifications.append(markdown.markdown(settings.notification_content.strip()))

    return dict(site_settings=settings, all_categories=Category.query.all(), current_lang=current_lang, global_notifications=notifications)

# Helper function to send SMS
def send_sms_code(phone, code):
    url = f'https://push.spug.cc/sms/{Spug_SMS_Template_Code}'
    body = {'code': code, 'to': phone}
    try:
        response = requests.post(url, json=body)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending SMS: {e}")
        return False

# Helper function to translate text using DeepSeek
def translate_text(text):
    if not text:
        return ""
    
    api_key = get_deepseek_key()
    client = OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL
    )
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": "You are a professional translator. Translate the following blog content from Chinese to English. Maintain all Markdown formatting, code blocks, and links exactly as they are. Do not add any conversational filler or explanations. Just output the translation."},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Translation Error: {e}")
        return text # Fallback to original if failed

# Helper function to generate summary
def generate_summary(text, lang='zh'):
    if not text:
        return ""
    
    api_key = get_deepseek_key()
    client = OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL
    )
    
    system_prompt = ""
    if lang == 'zh':
        system_prompt = "你是一个专业的文章摘要生成助手。请阅读以下文章内容，生成一个简短的中文摘要（100字以内）。摘要应精炼、吸引人。直接输出摘要内容，不要加任何前缀或解释。"
    else:
        system_prompt = "You are a professional article summary assistant. Please read the following article content and generate a short English summary (within 100 words). The summary should be concise and engaging. Output the summary directly without any prefix or explanation."

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text},
            ],
            stream=False
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Summary Generation Error ({lang}): {e}")
        return ""

def async_process_post(app, post_id):
    with app.app_context():
        post = Post.query.get(post_id)
        if not post:
            return
            
        print(f"Starting AI processing for post {post_id}...")
        
        # 1. Translate Title
        if not post.title_en:
            post.title_en = translate_text(post.title)
            
        # 2. Translate Content
        if not post.content_en:
            post.content_en = translate_text(post.content)
            
        # 3. Generate Summaries
        if not post.summary_zh:
            post.summary_zh = generate_summary(post.content, 'zh')
            
        if not post.summary_en:
            post.summary_en = generate_summary(post.content, 'en')
            
        db.session.commit()
        print(f"AI processing completed for post {post_id}.")

def async_process_photo(app, photo_id):
    with app.app_context():
        photo = Photo.query.get(photo_id)
        if not photo:
            return
        
        print(f"Starting AI processing for photo {photo_id}...")
        
        if photo.title and not photo.title_en:
            photo.title_en = translate_text(photo.title)
            
        if photo.description and not photo.description_en:
            photo.description_en = translate_text(photo.description)
            
        db.session.commit()
        print(f"AI processing completed for photo {photo_id}.")

def async_process_settings(app):
    with app.app_context():
        settings = SiteSetting.query.first()
        if not settings:
            return
            
        print("Starting AI processing for site settings...")
        
        if settings.about_content:
            # Always re-translate if content exists, or you could check if changed
            # For simplicity, we assume if this is called, we want to translate
            settings.about_content_en = translate_text(settings.about_content)
            
        db.session.commit()
        print("AI processing completed for site settings.")

# Routes
def get_blog_context():
    """
    Aggregates blog content for AI context.
    """
    context_parts = []
    
    # 1. Site Settings (Basic Info)
    settings = SiteSetting.query.first()
    if settings:
        context_parts.append(f"Blog Name: {settings.blog_name}")
        context_parts.append(f"About Content: {settings.about_content}")
    
    # 2. Posts (Limit to last 10 to avoid token limits, simplified)
    posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()
    if posts:
        context_parts.append("\nRecent Articles:")
        for post in posts:
            # Build absolute URL (assuming standard route)
            # Note: We can't use url_for easily outside request context without application context, 
            # but here we are inside a request usually.
            post_url = url_for('post', post_id=post.id, _external=True)
            summary = post.summary_zh if post.summary_zh else (post.content[:200] + "...")
            context_parts.append(f"- Title: {post.title}\n  URL: {post_url}\n  Summary: {summary}")
            
    return "\n\n".join(context_parts)

@app.route('/api/chat', methods=['POST'])
def chat_api():
    data = request.get_json()
    user_message = data.get('message')
    history = data.get('history', []) # List of {role, content}
    
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400
        
    api_key = get_deepseek_key()
    client = OpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL
    )
    
    # Construct system prompt with context
    site_context = get_blog_context()
    system_prompt = f"""You are a helpful AI assistant for this blog. 
    Your goal is to assist visitors by answering questions based on the blog's content.
    
    Here is the context of the blog:
    {site_context}
    
    IMPORTANT INSTRUCTIONS:
    1. If the user asks about specific articles, refer to them by title AND provide the URL.
    2. Format links in Markdown like this: [Article Title](URL).
    3. If the answer is not in the context, answer to the best of your general knowledge but mention that it's not explicitly in the blog.
    4. Be polite, concise, and helpful.
    """
    
    messages = [{"role": "system", "content": system_prompt}]
    
    # Append conversation history (limit to last 6 messages to save context)
    for msg in history[-6:]:
        messages.append(msg)
        
    messages.append({"role": "user", "content": user_message})
    
    def generate():
        try:
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                stream=True
            )
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            print(f"Chat API Error: {e}")
            yield f"Error: {str(e)}"

    return Response(stream_with_context(generate()), mimetype='text/plain')

@app.route('/set_lang/<lang>')
def set_lang(lang):
    if lang in ['zh', 'en']:
        session['lang'] = lang
    return redirect(request.referrer or url_for('index'))

@app.route('/')
def index():
    category_id = request.args.get('category', type=int)
    if category_id:
        posts = Post.query.filter_by(category_id=category_id).order_by(Post.created_at.desc()).all()
        active_category = Category.query.get(category_id)
    else:
        posts = Post.query.order_by(Post.created_at.desc()).all()
        active_category = None
    return render_template(get_template_path('index.html'), posts=posts, active_category=active_category)

@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Choose content based on language
    lang = session.get('lang', 'zh')
    if lang == 'en' and post.content_en:
        content_to_render = post.content_en
        post.display_title = post.title_en or post.title
    else:
        content_to_render = post.content
        post.display_title = post.title
        
    post.html_content = markdown.markdown(content_to_render, extensions=['fenced_code', 'codehilite'])
    return render_template(get_template_path('post.html'), post=post)

@app.route('/about')
def about():
    settings = SiteSetting.query.first()
    if not settings:
        content = "About content not initialized."
        social_links = []
    else:
        # Choose content based on language
        lang = session.get('lang', 'zh')
        if lang == 'en' and settings.about_content_en:
            content_to_render = settings.about_content_en
        else:
            content_to_render = settings.about_content
            
        content = markdown.markdown(content_to_render, extensions=['fenced_code', 'codehilite'])
        social_links = settings.get_social_links()
        
    return render_template(get_template_path('about.html'), content=content, social_links=social_links)

@app.route('/gallery')
def gallery():
    photos = Photo.query.order_by(Photo.created_at.desc()).all()
    return render_template(get_template_path('gallery.html'), photos=photos)

@app.route('/send-code', methods=['POST'])
def send_code():
    data = request.get_json()
    phone = data.get('phone')
    
    if not phone:
        return jsonify({'success': False, 'message': 'Phone number required'})
    
    if phone != ALLOWED_PHONE:
        return jsonify({'success': False, 'message': 'Unauthorized phone number'})
    
    # Generate 6-digit code
    code = ''.join(random.choices(string.digits, k=6))
    
    # Store code with timestamp in DB
    otp_entry = OTP.query.filter_by(phone=phone).first()
    if otp_entry:
        otp_entry.code = code
        otp_entry.timestamp = time.time()
    else:
        otp_entry = OTP(phone=phone, code=code, timestamp=time.time())
        db.session.add(otp_entry)
    
    db.session.commit()
    
    # Send SMS
    if send_sms_code(phone, code):
        return jsonify({'success': True, 'message': 'Code sent successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to send SMS'})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        phone = request.form.get('phone')
        code = request.form.get('code')
        
        if phone != ALLOWED_PHONE:
            flash('Unauthorized phone number.')
            return render_template(get_template_path('login.html'))
            
        otp_entry = OTP.query.filter_by(phone=phone).first()
        
        # Debug logging
        print(f"Login Attempt: Phone={phone}, Input Code={code}")
        if otp_entry:
            print(f"Stored Data for {phone}: Code={otp_entry.code}, Timestamp={otp_entry.timestamp}")
            print(f"Current Time: {time.time()}, Diff: {time.time() - otp_entry.timestamp}")
        else:
            print(f"Stored Data for {phone}: None")
        
        if not otp_entry:
            flash('No code requested or code expired.')
            return render_template(get_template_path('login.html'))
            
        # Check expiration (e.g., 5 minutes)
        if time.time() - otp_entry.timestamp > 300:
            db.session.delete(otp_entry)
            db.session.commit()
            flash('Code expired. Please request a new one.')
            return render_template(get_template_path('login.html'))
            
        if otp_entry.code == code:
            # Success! Log in the admin user
            # We assume the admin user is ID 1.
            user = User.query.get(1)
            if not user:
                # Should not happen if init_db ran, but safety net
                user = User(username='admin', password=generate_password_hash('random_pass'))
                db.session.add(user)
                db.session.commit()
            
            login_user(user, remember=True) # 14 days handled by PERMANENT_SESSION_LIFETIME
            db.session.delete(otp_entry) # Invalidate code
            db.session.commit()
            return redirect(url_for('index'))
        else:
            flash('Invalid verification code.')
            
    return render_template(get_template_path('login.html'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/create', methods=['GET', 'POST'])
@login_required
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        
        custom_author = request.form.get('custom_author')
        created_at_str = request.form.get('created_at')
        
        if created_at_str:
            try:
                created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()
        
        # Handle new category creation
        new_category_name = request.form.get('new_category')
        if new_category_name:
            existing_cat = Category.query.filter_by(name=new_category_name).first()
            if not existing_cat:
                new_cat = Category(name=new_category_name)
                db.session.add(new_cat)
                db.session.commit()
                category_id = new_cat.id
            else:
                category_id = existing_cat.id

        # Auto Translate
        # title_en = translate_text(title)
        # content_en = translate_text(content)
        
        # Auto Generate Summaries
        # summary_zh = generate_summary(content, 'zh')
        # summary_en = generate_summary(content, 'en')

        new_post = Post(
            title=title, 
            # title_en=title_en,
            content=content, 
            # content_en=content_en,
            # summary_zh=summary_zh,
            # summary_en=summary_en,
            author=current_user, 
            custom_author=custom_author,
            created_at=created_at,
            category_id=category_id if category_id else None
        )
        db.session.add(new_post)
        db.session.commit()
        
        # Start background task for AI processing
        threading.Thread(target=async_process_post, args=(app, new_post.id)).start()
        
        flash('Post published. AI translation and summary generation running in background.')
        return redirect(url_for('index'))
    
    categories = Category.query.all()
    return render_template(get_template_path('edit_post.html'), post=None, categories=categories)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.content = request.form.get('content')
        post.custom_author = request.form.get('custom_author')
        
        created_at_str = request.form.get('created_at')
        if created_at_str:
            try:
                post.created_at = datetime.strptime(created_at_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                pass # Keep original if invalid
        
        # Re-translate on edit (Simplification: always re-translate)
        # Clear existing AI content to trigger re-generation
        post.title_en = None
        post.content_en = None
        post.summary_zh = None
        post.summary_en = None
        
        # post.title_en = translate_text(post.title)
        # post.content_en = translate_text(post.content)
        
        # Re-generate summaries
        # post.summary_zh = generate_summary(post.content, 'zh')
        # post.summary_en = generate_summary(post.content, 'en')
        
        category_id = request.form.get('category_id')
        new_category_name = request.form.get('new_category')
        if new_category_name:
            existing_cat = Category.query.filter_by(name=new_category_name).first()
            if not existing_cat:
                new_cat = Category(name=new_category_name)
                db.session.add(new_cat)
                db.session.commit()
                category_id = new_cat.id
            else:
                category_id = existing_cat.id
        
        post.category_id = category_id if category_id else None
        db.session.commit()
        
        # Start background task for AI processing
        threading.Thread(target=async_process_post, args=(app, post.id)).start()
        
        flash('Post updated. AI translation and summary generation running in background.')
        return redirect(url_for('post', post_id=post.id))
        
    categories = Category.query.all()
    return render_template(get_template_path('edit_post.html'), post=post, categories=categories)

@app.route('/delete/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    site_settings = SiteSetting.query.first()
    if not site_settings:
        site_settings = SiteSetting(blog_name="Wslll Blog")
        db.session.add(site_settings)
        db.session.commit()
        
    if request.method == 'POST':
        site_settings.blog_name = request.form.get('blog_name')
        site_settings.about_content = request.form.get('about_content')
        site_settings.notification_content = request.form.get('notification_content')
        
        # Update DeepSeek API Key
        new_key = request.form.get('deepseek_api_key')
        if new_key:
            site_settings.deepseek_api_key = new_key
            
        # Update Theme
        theme = request.form.get('theme')
        if theme:
            site_settings.theme = theme
        
        # Auto Translate About Content
        # site_settings.about_content_en = translate_text(site_settings.about_content)
        
        # Process Social Links
        social_links = []
        icons = request.form.getlist('social_icon[]')
        urls = request.form.getlist('social_url[]')
        
        for icon, url in zip(icons, urls):
            if icon.strip() and url.strip():
                social_links.append({"icon": icon.strip(), "url": url.strip()})
        
        site_settings.social_links = json.dumps(social_links)
        
        if 'logo' in request.files:
            file = request.files['logo']
            if file and file.filename:
                filename = secure_filename(file.filename)
                logo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'logo')
                if not os.path.exists(logo_path):
                    os.makedirs(logo_path)
                file.save(os.path.join(logo_path, filename))
                site_settings.logo_filename = filename
        
        db.session.commit()

        # Start background task for AI processing (About Content Translation)
        threading.Thread(target=async_process_settings, args=(app,)).start()

        flash('Settings updated. AI translation for About Me is running in background.')
        return redirect(url_for('settings'))
    return render_template(get_template_path('settings.html'), settings=site_settings)

@app.route('/gallery/upload', methods=['POST'])
@login_required
def upload_photo():
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename:
            # Generate unique filename using UUID
            ext = os.path.splitext(file.filename)[1]
            filename = f"{uuid.uuid4().hex}{ext}"
            
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], 'photos')
            if not os.path.exists(save_path):
                os.makedirs(save_path)
            file.save(os.path.join(save_path, filename))
            
            title = request.form.get('title')
            description = request.form.get('description')
            
            # Auto Translate
            # title_en = translate_text(title)
            # description_en = translate_text(description)

            new_photo = Photo(
                filename=filename,
                title=title,
                # title_en=title_en,
                description=description,
                # description_en=description_en
            )
            db.session.add(new_photo)
            db.session.commit()

            # Start background task for AI processing
            threading.Thread(target=async_process_photo, args=(app, new_photo.id)).start()

            flash('Photo uploaded successfully. AI translation running in background.')
    return redirect(url_for('gallery'))

@app.route('/gallery/delete/<int:photo_id>', methods=['POST'])
@login_required
def delete_photo(photo_id):
    photo = Photo.query.get_or_404(photo_id)
    # Optionally remove file from disk
    try:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], 'photos', photo.filename))
    except:
        pass
    db.session.delete(photo)
    db.session.commit()
    return redirect(url_for('gallery'))

# Init DB command
def init_db():
    with app.app_context():
        db.create_all()
        # We still create a default admin user for the ID=1 reference
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', password=generate_password_hash('admin123'))
            db.session.add(admin)
            print("Created default admin user.")
        
        if not SiteSetting.query.first():
            settings = SiteSetting(blog_name="Wslll Blog")
            db.session.add(settings)
            print("Initialized site settings.")
            
        if not Category.query.first():
            default_cat = Category(name="Tech")
            db.session.add(default_cat)
            print("Initialized default category.")
            
        db.session.commit()

if __name__ == '__main__':
    if not os.path.exists('blog.db'):
        init_db()
    app.run(debug=True, host='0.0.0.0', port=15013)
