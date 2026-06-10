import logging
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.notifications.models import (
    Notification,
    NotificationEvent,
    NotificationEventStatus,
    NotificationEventType,
)


logger = logging.getLogger(__name__)


def emit_notification_event(event_type, payload, event_key=None, process_after=None):
    """
    Persist a durable notification event and ask Celery to process it after commit.

    Producers should call this helper instead of creating Notification rows
    directly. If Redis/Celery is temporarily unavailable the event remains in
    the database and can be picked up by process_pending_notification_events.
    """

    event_key = event_key or build_event_key(event_type, payload)
    defaults = {
        'event_type': event_type,
        'payload': payload,
        'process_after': process_after or timezone.now(),
    }
    event, created = NotificationEvent.objects.get_or_create(
        event_key=event_key,
        defaults=defaults,
    )

    if not created and event.status == NotificationEventStatus.FAILED:
        event.status = NotificationEventStatus.PENDING
        event.payload = payload
        event.process_after = process_after or timezone.now()
        event.last_error = ''
        event.save(update_fields=['status', 'payload', 'process_after', 'last_error', 'updated_at'])

    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        enqueue_notification_event(event.pk)
    else:
        transaction.on_commit(lambda: enqueue_notification_event(event.pk))
    return event


def notify_author_new_book(book):
    if not book.pk or not book.is_active or book.status != 'published':
        return None

    return emit_notification_event(
        NotificationEventType.AUTHOR_NEW_BOOK,
        {'book_id': str(book.pk)},
        event_key=f'{NotificationEventType.AUTHOR_NEW_BOOK}:{book.pk}',
    )


def notify_book_comment_created(comment):
    if not comment.pk:
        return None

    event_type = (
        NotificationEventType.COMMENT_REPLY
        if comment.parent_id
        else NotificationEventType.BOOK_NEW_COMMENT
    )
    return emit_notification_event(
        event_type,
        {'comment_id': str(comment.pk)},
        event_key=f'{event_type}:{comment.pk}',
    )


def enqueue_notification_event(event_id):
    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        process_event(event_id)
        return

    try:
        from core.notifications.tasks import process_notification_event

        process_notification_event.delay(str(event_id))
    except Exception:
        logger.exception('Failed to enqueue notification event %s', event_id)


def process_event(event_id):
    with transaction.atomic():
        event = NotificationEvent.objects.select_for_update().get(pk=event_id)
        if event.status == NotificationEventStatus.PROCESSED:
            return 0

        if event.process_after > timezone.now():
            return 0

        event.status = NotificationEventStatus.PROCESSING
        event.attempts += 1
        event.save(update_fields=['status', 'attempts', 'updated_at'])

    try:
        created_count = dispatch_event(event.event_type, event.payload)
    except Exception as exc:
        mark_event_failed(event.pk, exc)
        raise

    NotificationEvent.objects.filter(pk=event.pk).update(
        status=NotificationEventStatus.PROCESSED,
        processed_at=timezone.now(),
        last_error='',
        updated_at=timezone.now(),
    )
    return created_count


def process_pending_events(limit=100):
    now = timezone.now()
    stale_processing_cutoff = now - timedelta(minutes=10)
    event_ids = list(
        NotificationEvent.objects.filter(
            Q(status=NotificationEventStatus.PENDING, process_after__lte=now)
            | Q(status=NotificationEventStatus.PROCESSING, updated_at__lte=stale_processing_cutoff)
        )
        .order_by('created_at')
        .values_list('id', flat=True)[:limit]
    )
    processed_count = 0
    for event_id in event_ids:
        processed_count += process_event(event_id)
    return processed_count


def dispatch_event(event_type, payload):
    handlers = {
        NotificationEventType.AUTHOR_NEW_BOOK: handle_author_new_book,
        NotificationEventType.BOOK_NEW_COMMENT: handle_book_new_comment,
        NotificationEventType.COMMENT_REPLY: handle_comment_reply,
    }
    handler = handlers.get(event_type)
    if handler is None:
        raise ValueError(f'Unsupported notification event type: {event_type}')
    return handler(payload)


def mark_event_failed(event_id, exc):
    with transaction.atomic():
        event = NotificationEvent.objects.select_for_update().get(pk=event_id)
        can_retry = event.attempts < event.max_attempts
        event.status = NotificationEventStatus.PENDING if can_retry else NotificationEventStatus.FAILED
        event.last_error = str(exc)[:2000]
        event.process_after = timezone.now() + timedelta(minutes=min(event.attempts, 10))
        event.save(update_fields=['status', 'last_error', 'process_after', 'updated_at'])


def handle_author_new_book(payload):
    from core.books.models import Book, BookStatus
    from core.profiles.models import AuthorSubscription

    book = Book.objects.prefetch_related('authors__user').get(pk=payload['book_id'])
    if book.status != BookStatus.PUBLISHED or not book.is_active:
        return 0

    author_ids = list(book.authors.values_list('id', flat=True))
    author_user_ids = set(book.authors.values_list('user_id', flat=True))
    subscriptions = (
        AuthorSubscription.objects.filter(
            author_id__in=author_ids,
            notify_new_books=True,
            reader__is_active=True,
        )
        .select_related('reader__user')
        .order_by('reader__user_id')
    )

    recipients = {}
    for subscription in subscriptions:
        recipient = subscription.reader.user
        if recipient.pk not in author_user_ids:
            recipients[recipient.pk] = recipient

    payload_data = build_book_payload(book)
    created_count = 0
    for recipient in recipients.values():
        _, created = create_notification(
            recipient=recipient,
            notification_type=NotificationEventType.AUTHOR_NEW_BOOK,
            title='New book from an author you follow',
            message=f'"{book.title}" is now available.',
            payload=payload_data,
            dedupe_key=f'{NotificationEventType.AUTHOR_NEW_BOOK}:{book.pk}:{recipient.pk}',
        )
        created_count += int(created)
    return created_count


def handle_book_new_comment(payload):
    from core.books.models import BookComment

    comment = (
        BookComment.objects.select_related('reader__user', 'book')
        .prefetch_related('book__authors__user')
        .get(pk=payload['comment_id'])
    )
    if comment.parent_id:
        return 0

    recipients = [
        author.user
        for author in comment.book.authors.all()
        if author.user_id != comment.reader.user_id
    ]
    created_count = 0
    for recipient in recipients:
        _, created = create_notification(
            recipient=recipient,
            actor=comment.reader.user,
            notification_type=NotificationEventType.BOOK_NEW_COMMENT,
            title='New comment on your book',
            message=f'{comment.reader.user.username} commented on "{comment.book.title}".',
            payload=build_comment_payload(comment),
            dedupe_key=f'{NotificationEventType.BOOK_NEW_COMMENT}:{comment.pk}:{recipient.pk}',
        )
        created_count += int(created)
    return created_count


def handle_comment_reply(payload):
    from core.books.models import BookComment

    reply = (
        BookComment.objects.select_related(
            'reader__user',
            'book',
            'parent__reader__user',
        )
        .get(pk=payload['comment_id'])
    )
    if not reply.parent_id or reply.parent.reader.user_id == reply.reader.user_id:
        return 0

    _, created = create_notification(
        recipient=reply.parent.reader.user,
        actor=reply.reader.user,
        notification_type=NotificationEventType.COMMENT_REPLY,
        title='New reply to your comment',
        message=f'{reply.reader.user.username} replied to your comment on "{reply.book.title}".',
        payload=build_comment_payload(reply),
        dedupe_key=f'{NotificationEventType.COMMENT_REPLY}:{reply.pk}:{reply.parent.reader.user_id}',
    )
    return int(created)


def create_notification(
    *,
    recipient,
    notification_type,
    title,
    message='',
    payload=None,
    actor=None,
    dedupe_key=None,
):
    defaults = {
        'recipient': recipient,
        'actor': actor,
        'notification_type': notification_type,
        'title': title,
        'message': message,
        'payload': payload or {},
    }

    if dedupe_key:
        return Notification.objects.get_or_create(
            dedupe_key=dedupe_key,
            defaults=defaults,
        )

    return Notification.objects.create(**defaults), True


def build_event_key(event_type, payload):
    payload_key = ':'.join(f'{key}={payload[key]}' for key in sorted(payload))
    return f'{event_type}:{payload_key}'


def build_book_payload(book):
    return {
        'book_id': str(book.pk),
        'book_slug': book.slug,
        'book_title': book.title,
        'author_ids': [str(author_id) for author_id in book.authors.values_list('id', flat=True)],
    }


def build_comment_payload(comment):
    return {
        'book_id': str(comment.book_id),
        'book_slug': comment.book.slug,
        'book_title': comment.book.title,
        'comment_id': str(comment.pk),
        'parent_comment_id': str(comment.parent_id) if comment.parent_id else None,
    }
