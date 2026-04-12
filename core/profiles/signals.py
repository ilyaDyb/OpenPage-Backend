from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.profiles.models import ReaderProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_reader_profile_for_new_user(sender, instance, created, raw=False, **kwargs):
    if raw or not created:
        return

    ReaderProfile.objects.get_or_create(user=instance)
