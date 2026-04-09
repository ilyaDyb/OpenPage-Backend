"""
Миграция для создания моделей профилей
"""
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('profiles', '__first__'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # AuthorProfile migration will be auto-generated
        # ReaderProfile migration will be auto-generated
        # Bookmark migration will be auto-generated
        # ReadingHistory migration will be auto-generated
        # Review migration will be auto-generated
    ]
