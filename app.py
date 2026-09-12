import os
import logging
import time
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from pymongo import MongoClient
from dotenv import load_dotenv
from werkzeug.security import check_password_hash
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key-change-in-production')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['REMEMBER_COOKIE_DURATION']   = timedelta(days=30)
app.config['REMEMBER_COOKIE_HTTPONLY']   = True
app.config['REMEMBER_COOKIE_SAMESITE']   = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY']    = True
app.config['SESSION_COOKIE_SAMESITE']    = 'Lax'
app.config['SESSION_COOKIE_SECURE']      = False  # True только когда будет HTTPS

# ---------- ДОБАВЛЯЕМ ЛИМИТЕР (опционально) ----------
# Ограничиваем количество запросов с одного IP: 60 в минуту (можно настроить)
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["60 per minute"],
    storage_uri="memory://",
)

# ---------- ЛОГИРОВАНИЕ ВСЕХ ЗАПРОСОВ ----------
@app.before_request
def before_request():
    request.start_time = time.time()
    session.permanent = True

@app.after_request
def after_request(response):
    if hasattr(request, 'start_time'):
        elapsed = time.time() - request.start_time
        logger.info(
            f"Request: {request.method} {request.path} "
            f"IP: {request.remote_addr} "
            f"Status: {response.status_code} "
            f"Time: {elapsed:.3f}s"
        )
    return response

# ---------- ОБРАБОТЧИК ОШИБОК ----------
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    return e

@app.errorhandler(Exception)
def handle_exception(e):
    logger.exception("Unhandled exception occurred")
    return "Internal Server Error", 500

# ---------- MongoDB ----------
client = MongoClient(os.getenv('MONGO_URI', 'mongodb://localhost:27017/achievements'))
db = client.get_database()
days_collection = db.days

# Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username):
        self.id = username

@login_manager.user_loader
def load_user(user_id):
    if user_id == os.getenv('USERNAME'):
        return User(user_id)
    return None

PASSWORD_HASH = os.getenv('PASSWORD_HASH')
def verify_password(username, password):
    return (username == os.getenv('USERNAME') and
            check_password_hash(PASSWORD_HASH, password))

CATEGORIES = {
    'personal_coding': 'Кодил для себя',
    'work': 'Работал',
    'home_tasks': 'Домашние задачи'
}

def get_or_create_day(date_obj):
    date_datetime = datetime(date_obj.year, date_obj.month, date_obj.day)
    doc = days_collection.find_one({'date': date_datetime})
    if doc is None:
        new_doc = {
            'date': date_datetime,
            'personal_coding': '',
            'work': '',
            'home_tasks': ''
        }
        days_collection.insert_one(new_doc)
        doc = new_doc
        logger.info(f"Created new day record for {date_obj}")
    return doc

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if verify_password(username, password):
            user = User(username)
            login_user(user, remember=True)
            logger.info(f"User {username} logged in from {request.remote_addr}")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('index'))
        else:
            logger.warning(f"Failed login attempt for {username} from {request.remote_addr}")
            flash('Неверный логин или пароль', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logger.info(f"User {current_user.id} logged out from {request.remote_addr}")
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    date_str = request.args.get('date')
    if date_str:
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            date_obj = datetime.now().date()
    else:
        date_obj = datetime.now().date()

    doc = get_or_create_day(date_obj)
    return render_template('index.html',
                           date=date_obj,
                           doc=doc,
                           categories=CATEGORIES,
                           timedelta=timedelta)

@app.route('/update', methods=['POST'])
@login_required
def update():
    try:
        data = request.json
        date_str = data.get('date')
        category = data.get('category')
        text = data.get('text', '').strip()

        if not date_str or not category:
            logger.warning(f"Missing fields from {request.remote_addr}: {data}")
            return jsonify({'success': False, 'message': 'Недостаточно данных'}), 400

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        if category not in CATEGORIES:
            logger.warning(f"Invalid category {category} from {request.remote_addr}")
            return jsonify({'success': False, 'message': 'Неверная категория'}), 400

        result = days_collection.update_one(
            {'date': datetime(date_obj.year, date_obj.month, date_obj.day)},
            {'$set': {category: text}}
        )
        if result.matched_count:
            logger.info(f"Updated {category} for {date_str} by {current_user.id}: {text[:50]}")
            return jsonify({'success': True})
        else:
            # если документа нет – создаём
            get_or_create_day(date_obj)
            days_collection.update_one(
                {'date': datetime(date_obj.year, date_obj.month, date_obj.day)},
                {'$set': {category: text}}
            )
            logger.info(f"Created and updated {category} for {date_str}")
            return jsonify({'success': True})
    except Exception as e:
        logger.exception(f"Error in /update: {e}")
        return jsonify({'success': False, 'message': 'Internal error'}), 500

if __name__ == '__main__':
    logger.info("Starting achievement tracker in debug mode (port 8004)")
    app.run(host='0.0.0.0', port=8004, debug=False)