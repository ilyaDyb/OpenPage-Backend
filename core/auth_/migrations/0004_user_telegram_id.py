# Generated migration for telegram_id field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_', '0003_user_email_confirmed_user_telegram_confirmed'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='telegram_id',
            field=models.BigIntegerField(
                blank=True,
                help_text='Telegram user ID for QR login',
                null=True,
                unique=True,
                verbose_name='Telegram ID'
            ),
        ),
    ]
