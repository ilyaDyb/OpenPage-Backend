# Generated migration for QRAuthRequest model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('auth_', '0004_user_telegram_id'),
    ]

    operations = [
        migrations.CreateModel(
            name='QRAuthRequest',
            fields=[
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, help_text='Unique token for QR authentication', primary_key=True, serialize=False)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('scanned', 'Scanned'), ('confirmed', 'Confirmed'), ('expired', 'Expired'), ('cancelled', 'Cancelled')], db_index=True, default='pending', max_length=20)),
                ('telegram_id', models.BigIntegerField(blank=True, help_text='Telegram user ID who scanned the QR code', null=True)),
                ('telegram_username', models.CharField(blank=True, help_text='Telegram username', max_length=255, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, help_text='Time when QR auth request was created')),
                ('expires_at', models.DateTimeField(help_text='Time when QR auth request expires')),
                ('confirmed_at', models.DateTimeField(blank=True, help_text='Time when login was confirmed', null=True)),
                ('user', models.ForeignKey(blank=True, help_text='Linked user account (after confirmation)', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='qr_auth_requests', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'QR Authentication Request',
                'verbose_name_plural': 'QR Authentication Requests',
                'ordering': ['-created_at'],
            },
        ),
    ]
