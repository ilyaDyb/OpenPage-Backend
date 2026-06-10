from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from core.profiles.models import RecentBookView


def record_recent_book_view(user, book):
    if not user.is_authenticated or not hasattr(user, 'reader_profile'):
        return None

    try:
        with transaction.atomic():
            recent_view, created = RecentBookView.objects.get_or_create(
                reader=user.reader_profile,
                book=book,
            )
            if not created:
                RecentBookView.objects.filter(pk=recent_view.pk).update(
                    viewed_count=F('viewed_count') + 1,
                    last_viewed_at=timezone.now(),
                )
                recent_view.refresh_from_db()
            return recent_view
    except IntegrityError:
        RecentBookView.objects.filter(reader=user.reader_profile, book=book).update(
            viewed_count=F('viewed_count') + 1,
            last_viewed_at=timezone.now(),
        )
        return RecentBookView.objects.get(reader=user.reader_profile, book=book)
