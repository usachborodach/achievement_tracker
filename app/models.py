import logging
from datetime import datetime

from flask_login import UserMixin

from .extensions import get_db

logger = logging.getLogger(__name__)


class User(UserMixin):
    def __init__(self, username: str):
        self.id = username


def days_collection():
    return get_db().days


def get_or_create_day(date_obj):
    """Возвращает документ дня, создавая его при отсутствии."""
    date_datetime = datetime(date_obj.year, date_obj.month, date_obj.day)
    doc = days_collection().find_one({'date': date_datetime})
    if doc is None:
        doc = {
            'date': date_datetime,
            'personal_coding': '',
            'work': '',
            'home_tasks': '',
        }
        days_collection().insert_one(doc)
        logger.info("Created new day record for %s", date_obj)
    return doc


def update_day_category(date_obj, category: str, text: str) -> bool:
    date_datetime = datetime(date_obj.year, date_obj.month, date_obj.day)
    result = days_collection().update_one(
        {'date': date_datetime},
        {'$set': {category: text}},
    )
    if result.matched_count == 0:
        get_or_create_day(date_obj)
        days_collection().update_one(
            {'date': date_datetime},
            {'$set': {category: text}},
        )
    return True