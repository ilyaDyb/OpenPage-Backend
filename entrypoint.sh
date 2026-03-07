#!/bin/sh

# entrypoint.sh

echo "Применение миграций..."
python manage.py makemigrations --noinput
python manage.py migrate --noinput

# echo "Сбор статических файлов..."
# python manage.py collectstatic --noinput

# echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell || true

echo "Запуск сервера..."
exec "$@"