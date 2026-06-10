from celery import shared_task

from core.notifications.services import process_event, process_pending_events


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={'max_retries': 3})
def process_notification_event(self, event_id):
    return process_event(event_id)


@shared_task
def process_pending_notification_events(limit=100):
    return process_pending_events(limit=limit)
