import uuid
import logging

from django.contrib.auth.models import AbstractUser
from django.db import models
from datetime import timedelta
from django.utils import timezone

logger = logging.getLogger(__name__)

class User(AbstractUser):
    is_author = models.BooleanField(
        default=False,
        verbose_name='Статус автора',
        help_text='Отметьте, если пользователь может публиковать книги'
    )
    
    email_confirmed = models.BooleanField(
        default=False,
        verbose_name='Подтвержденный email',
    )

    telegram_confirmed = models.BooleanField(
        default=False,
        verbose_name='Подтвержденный Telegram',
    )

    telegram_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name='Telegram ID',
        help_text='Telegram user ID for QR login'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username


class QRAuthRequest(models.Model):
    """
    Model for storing QR authentication requests.
    Used for the QR code login flow.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scanned', 'Scanned'),
        ('confirmed', 'Confirmed'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]
    
    token = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text='Unique token for QR authentication'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    telegram_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Telegram user ID who scanned the QR code'
    )
    
    telegram_username = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text='Telegram username'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='qr_auth_requests',
        help_text='Linked user account (after confirmation)'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='Time when QR auth request was created'
    )
    
    expires_at = models.DateTimeField(
        help_text='Time when QR auth request expires'
    )
    
    confirmed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Time when login was confirmed'
    )
    
    qr_code_image = models.ImageField(
        upload_to='qr_codes/',
        null=True,
        blank=True,
        help_text='Generated QR code image'
    )
    
    class Meta:
        verbose_name = 'QR Authentication Request'
        verbose_name_plural = 'QR Authentication Requests'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"QR Auth {self.token} - {self.status}"
    
    def is_expired(self):
        """Check if the token has expired"""
        return timezone.now() > self.expires_at
    
    def generate_qr_code_image(self, qr_link: str) -> str:
        """
        Generate QR code image and save to media folder.
        Returns relative URL to the image.
        """
        import qrcode
        from PIL import Image
        import os
        from django.conf import settings
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_link)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Generate filename
        filename = f"qr_{self.token}.png"
        
        # Ensure media directory exists
        media_root = settings.MEDIA_ROOT
        qr_dir = os.path.join(media_root, 'qr_codes')
        os.makedirs(qr_dir, exist_ok=True)
        
        # Save image
        filepath = os.path.join(qr_dir, filename)
        img.save(filepath)
        
        # Update model
        relative_path = f"qr_codes/{filename}"
        self.qr_code_image = relative_path
        self.save(update_fields=['qr_code_image'])
        
        logger.info(f"✅ Generated QR code image: {relative_path}")
        return relative_path
    
    def delete_qr_code_image(self):
        """Delete QR code image file"""
        import os
        from django.conf import settings
        
        if self.qr_code_image:
            try:
                filepath = os.path.join(settings.MEDIA_ROOT, self.qr_code_image)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    logger.info(f"🗑️ Deleted QR code image: {filepath}")
                
                # Clear database field
                self.qr_code_image = None
                self.save(update_fields=['qr_code_image'])
            except Exception as e:
                logger.error(f"❌ Error deleting QR image: {e}")
    
    def save(self, *args, **kwargs):
        """Set default expiration time if not set and cleanup on status change"""
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=5)
        
        # Check if this is an update
        if self.pk:
            try:
                old_instance = QRAuthRequest.objects.get(pk=self.pk)
                # If status changed to confirmed/expired/cancelled, delete QR image
                if (old_instance.status in ['pending', 'scanned'] and 
                    self.status in ['confirmed', 'expired', 'cancelled']):
                    # Schedule image deletion after save
                    from django.db import transaction
                    transaction.on_commit(self.delete_qr_code_image)
            except QRAuthRequest.DoesNotExist:
                pass
        
        super().save(*args, **kwargs)