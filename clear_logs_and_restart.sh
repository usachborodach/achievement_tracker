rm /var/log/nginx/achievement_tracker*
rm /var/log/achievement_tracker/*
systemctl restart nginx
systemctl restart achievement_tracker