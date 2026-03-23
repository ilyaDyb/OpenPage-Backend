"""
Management command to cleanup expired QR authentication requests.
Deletes QR code images and removes old database records.

Usage:
    python manage.py cleanup_qr_auth
"""

import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from core.auth_.models import QRAuthRequest


class Command(BaseCommand):
    help = 'Cleanup expired QR authentication requests and their images'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Delete records older than this many days (default: 7)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting'
        )

    def handle(self, *args, **options):
        days = options['days']
        dry_run = options['dry_run']
        
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        
        # Find expired QR auth requests
        expired_requests = QRAuthRequest.objects.filter(
            expires_at__lt=cutoff_date
        ) | QRAuthRequest.objects.filter(
            status__in=['expired', 'cancelled', 'confirmed'],
            created_at__lt=cutoff_date
        )
        
        total_count = expired_requests.count()
        deleted_count = 0
        images_deleted = 0
        
        self.stdout.write(f"Found {total_count} expired QR auth requests older than {days} days")
        
        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN - No changes will be made\n"))
        
        for qr_request in expired_requests:
            if not dry_run:
                # Delete image if exists
                if qr_request.qr_code_image:
                    try:
                        from django.conf import settings
                        filepath = os.path.join(settings.MEDIA_ROOT, qr_request.qr_code_image)
                        if os.path.exists(filepath):
                            os.remove(filepath)
                            images_deleted += 1
                            self.stdout.write(f"🗑️ Deleted image: {filepath}")
                    except Exception as e:
                        self.stderr.write(f"Error deleting image: {e}")
                
                # Delete database record
                token = qr_request.token
                qr_request.delete()
                deleted_count += 1
                self.stdout.write(f"✅ Deleted QR request: {token}")
            else:
                self.stdout.write(f"Would delete: {qr_request.token} (status: {qr_request.status})")
        
        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\nDRY RUN: Would delete {deleted_count} records and {images_deleted} images"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Successfully deleted {deleted_count} records and {images_deleted} images"
            ))
