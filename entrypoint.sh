#!/bin/sh
set -e

INIT_SENTINEL=/tmp/openpage_init_done

if [ ! -f "$INIT_SENTINEL" ]; then
  echo "Applying makemigrations..."
  python manage.py makemigrations --noinput
fi

echo "Applying migrate..."
python manage.py migrate --noinput

if [ ! -f "$INIT_SENTINEL" ]; then
  echo "Collecting static files..."
  python manage.py collectstatic --noinput

  echo "Ensuring superuser exists..."
  python manage.py shell <<EOF
from django.contrib.auth import get_user_model
import os

User = get_user_model()
username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'admin123')

if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f'Superuser {username} created.')
else:
    print(f'Superuser {username} already exists.')
EOF

  touch "$INIT_SENTINEL"
fi

echo "Starting server..."
exec "$@"
