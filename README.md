# Achievement Tracker

## Установка

```bash
apt install python3.10-venv
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

ln -sf \
  /root/achievement_tracker/deploy/achievement_tracker.service \
  /etc/systemd/system/achievement_tracker.service
systemctl daemon-reload
systemctl enable --now achievement_tracker

ln -sf \
  /root/achievement_tracker/deploy/nginx.conf \
  /etc/nginx/sites-enabled/achievement_tracker
nginx -t && systemctl restart nginx

# logrotate
ln -sf /root/achievement_tracker/deploy/achievement_tracker.logrotate \
       /etc/logrotate.d/achievement_tracker
```

## Запуск тестов

```bash
pytest -q
```