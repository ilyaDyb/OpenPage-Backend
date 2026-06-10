import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class NotificationEventType(models.TextChoices):
    AUTHOR_NEW_BOOK = 'author.new_book', 'Author new book'
    BOOK_NEW_COMMENT = 'book.new_comment', 'Book new comment'
    COMMENT_REPLY = 'comment.reply', 'Comment reply'


class NotificationEventStatus(models.TextChoices):
    PENDING = 'pending', 'Pending'
    PROCESSING = 'processing', 'Processing'
    PROCESSED = 'processed', 'Processed'
    FAILED = 'failed', 'Failed'


class NotificationEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=64, choices=NotificationEventType.choices)
    event_key = models.CharField(max_length=255, unique=True)
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=20,
        choices=NotificationEventStatus.choices,
        default=NotificationEventStatus.PENDING,
        db_index=True,
    )
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=5)
    process_after = models.DateTimeField(default=timezone.now, db_index=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification event'
        verbose_name_plural = 'Notification events'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'process_after']),
            models.Index(fields=['event_type', 'created_at']),
        ]

    def __str__(self):
        return f'{self.event_type}:{self.event_key}'


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='triggered_notifications',
        null=True,
        blank=True,
    )
    notification_type = models.CharField(max_length=64, choices=NotificationEventType.choices)
    title = models.CharField(max_length=255)
    message = models.TextField(max_length=1000, blank=True)
    payload = models.JSONField(default=dict, blank=True)
    dedupe_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.recipient_id}:{self.notification_type}:{self.title}'

    def mark_as_read(self):
        if self.is_read:
            return

        self.is_read = True
        self.read_at = timezone.now()
        self.save(update_fields=['is_read', 'read_at', 'updated_at'])
