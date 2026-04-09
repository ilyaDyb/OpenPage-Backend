# Final migration to fix all auth_ issues

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('auth_', '0008_alter_user_telegram_id'),
    ]

    operations = [
        # Пустая миграция для завершения всех проблем
    ]
