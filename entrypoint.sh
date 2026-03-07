#!/bin/sh

# entrypoint.sh

echo "Применение миграций..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

echo "Создание суперпользователя (если не существует)..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Суперпользователь {username} создан.')
else:
    print(f'Суперпользователь {username} уже существует.')
EOF

echo "Запуск сервера..."
exec "$@"