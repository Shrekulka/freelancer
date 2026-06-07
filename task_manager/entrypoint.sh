#!/bin/sh

set -e

# Выполняем миграции
python manage.py migrate --noinput

# Создаем суперпользователя, если его нет
# Используем переменные окружения или значения по умолчанию (admin/admin)
# Если заданы переменные DJANGO_SUPERUSER_PASSWORD, берём их. Иначе admin
SUPERUSER_PASSWORD=${DJANGO_SUPERUSER_PASSWORD:-admin}

python manage.py shell -c "
from django.contrib.auth.models import User;
import os;
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin');
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com');
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin');
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username, email, password);
    print(f'Superuser {username} created with password {password}');
else:
    print(f'Superuser {username} already exists');
"

# Собираем статику (если нужно)
python manage.py collectstatic --noinput

# Запускаем Gunicorn
exec "$@"