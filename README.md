# Achievement Tracker

## Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Конфигурация `.env`

```bash
# SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# PASSWORD_HASH
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('мой_пароль'))"
```

## Локальный запуск

```bash
flask --app wsgi create-index
python run.py
```

## Продакшен (systemd + nginx + gunicorn)

```bash
mkdir -p /var/log/achievement_tracker

ln -sf /root/achievement_tracker/deploy/achievement_tracker.service \
       /etc/systemd/system/achievement_tracker.service
systemctl daemon-reload
systemctl enable --now achievement_tracker

ln -sf /root/achievement_tracker/deploy/nginx.conf \
       /etc/nginx/sites-enabled/achievement_tracker
nginx -t && systemctl restart nginx

# logrotate
ln -sf /root/achievement_tracker/deploy/achievement_tracker.logrotate \
       /etc/logrotate.d/achievement_tracker
```

## Полезные команды

```bash
flask --app wsgi create-index   # создать уникальный индекс на days.date
pytest -q                       # запустить тесты
journalctl -u achievement_tracker -f
```

---

## Что и почему улучшено

| Было | Стало | Почему |
|---|---|---|
| `app.py` со всем кодом | Пакет `app/` с блюпринтами | Читаемость, тестируемость, изоляция |
| Глобальные `MongoClient`, `login_manager` | `extensions.py` + `create_app()` | Нет циклических импортов, легко мокать в тестах |
| `create_index.py` запускается systemd-ом напрямую | CLI-команда `flask create-index` | Единый контекст приложения, доступ к конфигу |
| Конфиги в корне | `deploy/` | Чистота репозитория, единая точка деплоя |
| `.env` в репо-структуре | `.env.example` + `.gitignore` | Безопасность |
| `multi-user.targets` (опечатка) | `multi-user.target` | Сервис вообще запускался? |
| Константы `CATEGORIES` в модуле | `app.config['CATEGORIES']` | Единый источник истины |
| Ручные try/except во вьюхах | Общий error-handler + `get_json(silent=True)` | Меньше дублирования |

Если хочешь — могу отдельно показать, как переписать `index.html` под `base.html` (убрать дублирование `<head>`), или добавить Alembic-подобные миграции/бэкапы для MongoDB.