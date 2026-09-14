import logging
from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user

from .models import get_or_create_day, update_day_category

logger = logging.getLogger(__name__)
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
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
    return render_template(
        'index.html',
        date=date_obj,
        doc=doc,
        categories=current_app.config['CATEGORIES'],
        timedelta=timedelta,
    )


@main_bp.route('/update', methods=['POST'])
@login_required
def update():
    try:
        data = request.get_json(silent=True) or {}
        date_str = data.get('date')
        category = data.get('category')
        text = (data.get('text') or '').strip()

        if not date_str or not category:
            logger.warning("Missing fields from %s: %s", request.remote_addr, data)
            return jsonify({'success': False, 'message': 'Недостаточно данных'}), 400

        if category not in current_app.config['CATEGORIES']:
            logger.warning("Invalid category %s from %s", category, request.remote_addr)
            return jsonify({'success': False, 'message': 'Неверная категория'}), 400

        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        update_day_category(date_obj, category, text)
        logger.info("Updated %s for %s by %s: %.50s",
                    category, date_str, current_user.id, text)
        return jsonify({'success': True})
    except Exception as e:
        logger.exception("Error in /update: %s", e)
        return jsonify({'success': False, 'message': 'Internal error'}), 500