import sqlite3
import markdown
import bleach
import os
import requests
import tempfile
import secrets
from datetime import date, datetime
from functools import wraps
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from flask import Flask, render_template, request, url_for, flash, redirect, session, send_from_directory
from werkzeug.exceptions import abort
from markupsafe import Markup
from dotenv import load_dotenv
from PIL import Image
from PIL.ExifTags import TAGS
import math
import json
import yaml
from datetime import datetime, timezone, timedelta
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from pillow_heif import register_heif_opener
from mastodon import Mastodon


# load environment variables
load_dotenv()


# load configs
def load_config():
    try:
        with open('config.yaml', 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print("config.yaml not found, using defaults")
        return {}


app = Flask(__name__)
config = load_config()


# csrf protection
csrf = CSRFProtect(app)


# heif/heic support
register_heif_opener()
HEIC_SUPPORTED = True


# rate limiting
# add a redis url to env vars if you want to use it for rate limiting storage
storage_uri = os.getenv('REDIS_URL', 'memory://')
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=[],
    storage_uri=storage_uri
)


# application settings - ensure numeric values are integers
def get_int_config(key, default):
    """get config value as integer, handling string values from YAML"""
    value = config.get(key, default)
    if value is None:
        return default
    
    # if it's already an integer, return it
    if isinstance(value, int):
        return value
    
    # if it's a string, try to convert it
    if isinstance(value, str):
        try:
            # handle expressions like "16 * 1024 * 1024"
            if '*' in value or '+' in value or '-' in value:
                # only evaluate simple arithmetic expressions for safety
                if all(c in '0123456789 +-*()' for c in value):
                    return int(eval(value))
            else:
                return int(value)
        except (ValueError, SyntaxError):
            print(f"Warning: Could not parse config value '{key}': {value}, using default: {default}")
            return default
    
    return default

# more configs
UPLOAD_FOLDER = config.get('upload_folder', 'uploads')
OPTIMIZED_FOLDER = config.get('optimized_folder', 'uploads/optimized')
ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'gif', 'webp','heic', 'heif']
MAX_CONTENT_LENGTH = get_int_config('max_content_length', 300 * 1024 * 1024)
POSTS_PER_PAGE = get_int_config('posts_per_page', 15)
OPTIMIZED_WIDTH = get_int_config('optimized_width', 1200)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH


# create upload directories if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OPTIMIZED_FOLDER, exist_ok=True)


# journal info variables for templates
@app.context_processor
def inject_blog_config():
    return {
        'journal_title': config.get('journal_title', 'my journal'),
        'journal_description': config.get('journal_description', ''),
    }


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_random_filename(original_filename, post_date):
    """
    generate a random filename with date prefix and preserve extension
    convert HEIC/HEIF to JPG since they'll be converted to JPEG
    """
    # get file extension from original filename
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = '.jpg'  # default extension if none found
    
    # convert HEIC/HEIF to JPG extension since we save as JPEG
    if ext.lower() in ['.heic', '.heif']:
        ext = '.jpg'
    
    # generate date prefix from post_date
    if isinstance(post_date, str):
        date_str = post_date.replace('-', '')
    else:
        date_str = post_date.strftime('%Y%m%d')
    
    # generate random string (8 characters should be sufficient)
    random_string = secrets.token_urlsafe(8).replace('-', '').replace('_', '')[:8]
    
    return f"{date_str}_{random_string}{ext.lower()}"


def strip_image_metadata(image_path, output_path):
    """
    strip metadata from image and save to output path
    converts HEIC/HEIF to JPEG for web compatibility
    """
    try:
        with Image.open(image_path) as img:
            # convert to RGB for consistency and web compatibility
            # this handles HEIC, PNG with transparency, etc.
            if img.mode in ('RGBA', 'LA', 'P'):
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # save as JPEG without any EXIF data (works for all input formats)
            img.save(output_path, 'JPEG', quality=95, optimize=True, exif=b"")
            return True
    except Exception as e:
        print(f"error stripping metadata from image: {e}")
        return False


def optimize_image(input_path, output_path, max_width=OPTIMIZED_WIDTH):
    """
    optimize image by resizing it to max_width while maintaining aspect ratio
    and strip all metadata. handles all formats including HEIC/HEIF.
    """
    try:
        with Image.open(input_path) as img:
            # convert to RGB if necessary (for JPEGs)
            if img.mode in ('RGBA', 'LA', 'P'):
                # convert palette or transparency to RGB
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # create white background for transparent images
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'RGBA':
                    background.paste(img, mask=img.split()[-1])
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            
            # calculate new dimensions
            width, height = img.size
            if width > max_width:
                ratio = max_width / width
                new_height = int(height * ratio)
                img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
            # save optimized image without any EXIF data
            img.save(output_path, 'JPEG', quality=85, optimize=True, exif=b"")
            return True
    except Exception as e:
        print(f"error optimizing image: {e}")
        return False


def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn


def get_post_by_date(post_date):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE post_date = ?',
                        (post_date,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


def get_post_by_id(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    conn.close()
    if post is None:
        abort(404)
    return post


def get_post_images(post_id):
    """get all images for a post, ordered by sort_order"""
    conn = get_db_connection()
    images = conn.execute(
        'SELECT * FROM post_images WHERE post_id = ? ORDER BY sort_order, id',
        (post_id,)
    ).fetchall()
    conn.close()
    return images


def process_uploaded_images(request, post_date):
    """process multiple uploaded images and return list of processed filenames and alt texts"""
    processed_images = []
    
    for i in range(1, 6):  # handle up to 5 images
        file_key = f'image_{i}'
        alt_key = f'alt_text_{i}'
        
        if file_key in request.files:
            file = request.files[file_key]
            alt_text = request.form.get(alt_key, '').strip() or None
            
            if file and file.filename and allowed_file(file.filename):
                # generate random filename with date prefix
                image_filename = generate_random_filename(file.filename, post_date)
                
                # save original image with metadata stripped
                original_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
                
                # save to temporary location first
                temp_path = os.path.join(tempfile.gettempdir(), f"temp_{image_filename}")
                file.save(temp_path)
                
                # strip metadata and save to final location
                if strip_image_metadata(temp_path, original_path):
                    # create optimized version
                    optimized_filename = f"opt_{image_filename}"
                    optimized_path = os.path.join(OPTIMIZED_FOLDER, optimized_filename)
                    
                    if optimize_image(temp_path, optimized_path):
                        print(f"created optimized image: {optimized_filename}")
                    else:
                        print("failed to create optimized image, using original")
                    
                    processed_images.append((image_filename, alt_text, i-1))  # sort_order = i-1
                    
                    # clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                else:
                    print("failed to strip metadata from original image")
                    # clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
    
    return processed_images


def login_required(f):
    """decorator to require login for certain routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            flash('please log in to access this page.')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def post_to_mastodon(post_date, title, post_url):
    """post to mastodon if configured"""
    try:
        mastodon_config = config.get('mastodon', {})
        instance_url = mastodon_config.get('instance_url')
        access_token = mastodon_config.get('access_token')
        privacy = mastodon_config.get('privacy', 'private')
        
        if not instance_url or not access_token:
            flash('mastodon not configured - skipping cross-post')
            return False
            
        # create mastodon client
        mastodon = Mastodon(
            access_token=access_token,
            api_base_url=instance_url
        )
        
        # format post content
        iso_date = datetime.strptime(post_date, '%Y-%m-%d').strftime('%Y-%m-%d')
        status_text = f"new journal entry...\n\n{iso_date} - {title}\n\nhttps://journal.palomakop.tv/post/{post_date}"
        
        # post to mastodon
        mastodon.status_post(
            status=status_text,
            visibility=privacy
        )
        
        flash('successfully cross-posted to mastodon!')
        return True
        
    except Exception as e:
        flash(f'error posting to mastodon: {str(e)}')
        return False


# configure markdown
md = markdown.Markdown(extensions=['fenced_code', 'tables', 'toc'])

# configure bleach settings for HTML sanitization
ALLOWED_TAGS = [
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'p', 'br', 'strong', 'em', 'b', 'i',
    'ul', 'ol', 'li',
    'blockquote',
    'code', 'pre',
    'a',
    'table', 'thead', 'tbody', 'tr', 'th', 'td',
    'div', 'span', 'img'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title'],
    'table': ['class'],
    'th': ['align'],
    'td': ['align'],
    'div': ['class'],
    'span': ['class'],
    'code': ['class'],
    'pre': ['class'],
    'img': ['src', 'alt', 'width', 'height', 'class']
}

ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

# add markdown filter to Jinja2
@app.template_filter('markdown')
def markdown_filter(text):
    if not text:
        return ''
    # convert markdown to HTML
    html = md.convert(text)
    # sanitize the HTML with bleach
    clean_html = bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True
    )
    return Markup(clean_html)


# add filter to strip HTML tags for RSS descriptions
@app.template_filter('striptags')
def striptags_filter(text):
    """remove HTML tags from text"""
    return bleach.clean(text, tags=[], strip=True)


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    """serve uploaded files"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER), filename)


@app.route('/uploads/optimized/<filename>')
def optimized_file(filename):
    """serve optimized files"""
    return send_from_directory(os.path.join(os.path.dirname(__file__), UPLOAD_FOLDER, 'optimized'), filename)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/favicon.ico')
def favicon():
    """serve favicon.ico from the root directory"""
    return send_from_directory(
        os.path.join(app.root_path, 'static'), 
        'favicon.ico', 
        mimetype='image/vnd.microsoft.icon'
    )


@app.route('/rss')
def rss_feed():
    """generate RSS feed with last 50 public posts"""
    conn = get_db_connection()
    posts = conn.execute(
        'SELECT * FROM posts WHERE is_private = 0 ORDER BY post_date DESC LIMIT 50'
    ).fetchall()
    
    # add images to each post
    posts_with_images = []
    for post in posts:
        post_dict = dict(post)
        post_dict['images'] = get_post_images(post['id'])
        posts_with_images.append(post_dict)
    
    conn.close()
    
    response = render_template('rss.xml', posts=posts_with_images, datetime=datetime)
    return app.response_class(response, mimetype='application/rss+xml')


@app.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    
    conn = get_db_connection()
    
    # count total posts based on login status
    if session.get('logged_in'):
        total = conn.execute('SELECT COUNT(*) FROM posts').fetchone()[0]
        posts_query = 'SELECT * FROM posts ORDER BY post_date DESC LIMIT ? OFFSET ?'
    else:
        total = conn.execute('SELECT COUNT(*) FROM posts WHERE is_private = 0').fetchone()[0]
        posts_query = 'SELECT * FROM posts WHERE is_private = 0 ORDER BY post_date DESC LIMIT ? OFFSET ?'
    
    # calculate pagination
    total_pages = math.ceil(total / POSTS_PER_PAGE)
    offset = (page - 1) * POSTS_PER_PAGE
    
    # get posts for current page
    posts = conn.execute(posts_query, (POSTS_PER_PAGE, offset)).fetchall()
    
    # add images to each post
    posts_with_images = []
    for post in posts:
        post_dict = dict(post)
        post_dict['images'] = get_post_images(post['id'])
        posts_with_images.append(post_dict)
    
    conn.close()
    
    # create pagination object
    pagination = {
        'page': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_num': page - 1 if page > 1 else None,
        'next_num': page + 1 if page < total_pages else None,
        'total': total
    }
    
    return render_template('index.html', posts=posts_with_images, pagination=pagination)


@app.route('/post/<post_date>')
def post(post_date):
    post = get_post_by_date(post_date)
    
    # check if post is private and user is not logged in
    if post['is_private'] and not session.get('logged_in'):
        abort(404)
    
    # get images for this post
    images = get_post_images(post['id'])
    
    return render_template('post.html', post=post, images=images)


@app.route('/login', methods=('GET', 'POST'))
@limiter.limit("5 per minute")
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        admin_password_hash = os.getenv('ADMIN_PASSWORD_HASH')
        
        if not admin_password_hash:
            flash('admin password not configured. please set ADMIN_PASSWORD_HASH environment variable.')
            return render_template('login.html')
        
        # check username first
        if username != 'admin':
            flash('invalid username or password.')
            return render_template('login.html')
        
        # check password - prefer hash over plain text
        password_valid = False
        if admin_password_hash:
            password_valid = check_password_hash(admin_password_hash, password)
        
        if password_valid:
            session['logged_in'] = True
            session['username'] = 'admin'
            flash('successfully logged in!')
            
            # redirect to next page if specified, otherwise to index
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            flash('invalid username or password.')
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('you have been logged out.')
    return redirect(url_for('index'))


@app.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        post_date = request.form.get('post_date', date.today().isoformat())
        is_private = 'is_private' in request.form
        
        if not title:
            flash('title is required!')
        else:
            conn = None
            try:
                conn = get_db_connection()
                
                # insert post and get the post ID
                cursor = conn.execute(
                    'INSERT INTO posts (title, content, post_date, is_private) VALUES (?, ?, ?, ?)',
                    (title, content, post_date, is_private)
                )
                post_id = cursor.lastrowid
                
                # process uploaded images
                processed_images = process_uploaded_images(request, post_date)
                
                # save each processed image
                for filename, alt_text, sort_order in processed_images:
                    conn.execute(
                        'INSERT INTO post_images (post_id, filename, alt_text, sort_order) VALUES (?, ?, ?, ?)',
                        (post_id, filename, alt_text, sort_order)
                    )
                
                conn.commit()
                flash('post created successfully!')
                
                # handle mastodon cross-posting
                if 'cross_post_mastodon' in request.form:
                    post_url = f"https://journal.palomakop.tv/post/{post_date}"
                    post_to_mastodon(post_date, title, post_url)
                
                return redirect(url_for('post', post_date=post_date))
                
            except sqlite3.IntegrityError:
                flash('a post already exists for this date. please choose a different date or edit the existing post.')
            except Exception as e:
                flash(f'error creating post: {str(e)}')
            finally:
                if conn:
                    conn.close()

    # default to today's date
    default_date = date.today().isoformat()
    return render_template('create.html', default_date=default_date)


@app.route('/edit/<post_date>', methods=('GET', 'POST'))
@login_required
def edit(post_date):
    post = get_post_by_date(post_date)
    existing_images = get_post_images(post['id'])

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        new_post_date = request.form.get('post_date', post['post_date'])
        is_private = 'is_private' in request.form
        
        if not title:
            flash('title is required!')
        else:
            conn = None
            try:
                conn = get_db_connection()
                
                # handle existing image updates and deletions
                for image in existing_images:
                    # check if image should be removed
                    if f'remove_image_{image["id"]}' in request.form:
                        # delete files
                        if image['filename']:
                            original_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
                            optimized_path = os.path.join(OPTIMIZED_FOLDER, f"opt_{image['filename']}")
                            
                            if os.path.exists(original_path):
                                os.remove(original_path)
                            if os.path.exists(optimized_path):
                                os.remove(optimized_path)
                        
                        # delete database record
                        conn.execute('DELETE FROM post_images WHERE id = ?', (image['id'],))
                    else:
                        # update alt text
                        new_alt_text = request.form.get(f'existing_alt_{image["id"]}', '').strip() or None
                        conn.execute(
                            'UPDATE post_images SET alt_text = ? WHERE id = ?',
                            (new_alt_text, image['id'])
                        )
                
                # process new uploaded images
                processed_images = process_uploaded_images(request, new_post_date)
                
                # save each new processed image
                for filename, alt_text, sort_order in processed_images:
                    # adjust sort_order to come after existing images
                    adjusted_sort_order = len(existing_images) + sort_order
                    conn.execute(
                        'INSERT INTO post_images (post_id, filename, alt_text, sort_order) VALUES (?, ?, ?, ?)',
                        (post['id'], filename, alt_text, adjusted_sort_order)
                    )
                
                # update post
                conn.execute(
                    'UPDATE posts SET title = ?, content = ?, post_date = ?, is_private = ? WHERE id = ?',
                    (title, content, new_post_date, is_private, post['id'])
                )
                
                conn.commit()
                flash('post updated successfully!')
                
                # handle mastodon cross-posting
                if 'cross_post_mastodon' in request.form:
                    post_url = f"https://journal.palomakop.tv/post/{new_post_date}"
                    post_to_mastodon(new_post_date, title, post_url)
                
                return redirect(url_for('post', post_date=new_post_date))
                
            except sqlite3.IntegrityError:
                flash('a post already exists for the new date. please choose a different date.')
            except Exception as e:
                flash(f'error updating post: {str(e)}')
            finally:
                if conn:
                    conn.close()

    return render_template('edit.html', post=post, existing_images=existing_images)


@app.route('/delete/<post_date>', methods=('POST',))
@login_required
def delete(post_date):
    post = get_post_by_date(post_date)
    
    # get all images for this post
    images = get_post_images(post['id'])
    
    # delete all associated image files
    for image in images:
        if image['filename']:
            original_path = os.path.join(app.config['UPLOAD_FOLDER'], image['filename'])
            optimized_path = os.path.join(OPTIMIZED_FOLDER, f"opt_{image['filename']}")
            
            if os.path.exists(original_path):
                os.remove(original_path)
            if os.path.exists(optimized_path):
                os.remove(optimized_path)
    
    conn = get_db_connection()
    # delete post (images will be deleted automatically due to CASCADE)
    conn.execute('DELETE FROM posts WHERE id = ?', (post['id'],))
    conn.commit()
    conn.close()
    
    flash('"{}" was successfully deleted!'.format(post['title']))
    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=False)