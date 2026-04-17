import os
import secrets

from rest_framework.permissions import BasePermission


class HasAPISecretKey(BasePermission):
    message = 'Valid X-Secret-Key header is required.'

    def has_permission(self, request, view):
        expected_key = os.environ.get('API_SECRET_KEY')
        provided_key = request.headers.get('X-Secret-Key')

        if not expected_key or not provided_key:
            return False

        return secrets.compare_digest(provided_key, expected_key)
