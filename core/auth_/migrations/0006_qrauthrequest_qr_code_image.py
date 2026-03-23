# Generated migration for QRAuthRequest.qr_code_image field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('auth_', '0005_qrauthrequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='qrauthrequest',
            name='qr_code_image',
            field=models.ImageField(blank=True, help_text='Generated QR code image', null=True, upload_to='qr_codes/'),
        ),
    ]
