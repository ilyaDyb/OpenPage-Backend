# Simple migration to add missing fields to User model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_', '0002_alter_user_options_user_is_author'),
    ]

    operations = [
        # Добавляем только отсутствующие поля
        migrations.AddField(
            model_name='user',
            name='role',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('reader', 'Читатель'),
                    ('author', 'Автор'),
                    ('moderator', 'Модератор'),
                    ('admin', 'Администратор'),
                    ('finance_manager', 'Финансовый менеджер'),
                ],
                default='reader',
                verbose_name='Роль'
            ),
        ),
    ]
