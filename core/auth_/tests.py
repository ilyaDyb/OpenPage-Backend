import os
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.auth_.models import QRAuthRequest
from core.auth_.serializers import UserCreateSerializer


class UserCreateSerializerTests(TestCase):
    @patch("core.auth_.serializers.email_domain_exists", return_value=False)
    def test_rejects_email_with_nonexistent_domain(self, mocked_email_domain_exists):
        serializer = UserCreateSerializer(
            data={
                "username": "reader1",
                "email": "reader@missing-domain.invalid",
                "password": "StrongPassword123",
                "password2": "StrongPassword123",
            }
        )

        self.assertFalse(serializer.is_valid())
        self.assertEqual(
            serializer.errors["email"][0],
            "Email domain does not exist or is unreachable."
        )
        mocked_email_domain_exists.assert_called_once_with("reader@missing-domain.invalid")


@override_settings(ROOT_URLCONF="core.open_page.urls")
class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = "/api/user/register/"
        self.payload = {
            "username": "reader2",
            "email": "reader2@example.com",
            "password": "StrongPassword123",
            "password2": "StrongPassword123",
            "first_name": "Test",
            "last_name": "User",
        }

    @patch("core.auth_.serializers.email_domain_exists", return_value=True)
    @patch("core.auth_.views.get_registration_data", return_value=None)
    @patch("core.auth_.views.store_registration_data")
    @patch("core.auth_.views.send_verification_email", side_effect=Exception("smtp failed"))
    def test_does_not_store_registration_if_email_send_fails(
        self,
        mocked_send_email,
        mocked_store_registration_data,
        mocked_get_registration_data,
        mocked_email_domain_exists,
    ):
        response = self.client.post(self.url, self.payload, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["type"], "validation_error")
        self.assertEqual(
            response.json()["errors"]["email"][0],
            "Failed to send verification code to this email."
        )
        mocked_send_email.assert_called_once()
        mocked_get_registration_data.assert_called_once_with(self.payload["email"])
        mocked_store_registration_data.assert_not_called()
        mocked_email_domain_exists.assert_called_once_with(self.payload["email"])


@override_settings(ROOT_URLCONF="core.open_page.urls")
class QRAuthSecurityTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.qr_request = QRAuthRequest.objects.create(expires_at=timezone.now() + timedelta(minutes=5))

    @patch.dict(os.environ, {"API_SECRET_KEY": "super-secret"}, clear=False)
    def test_qr_confirm_requires_secret_key(self):
        response = self.client.post(
            "/api/qr-auth/confirm/",
            {
                "token": str(self.qr_request.token),
                "telegram_id": 123456,
                "telegram_username": "readerbot",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["type"], "permission_denied")

    @patch.dict(os.environ, {"API_SECRET_KEY": "super-secret"}, clear=False)
    def test_qr_confirm_accepts_valid_secret_key(self):
        response = self.client.post(
            "/api/qr-auth/confirm/",
            {
                "token": str(self.qr_request.token),
                "telegram_id": 123456,
                "telegram_username": "readerbot",
            },
            format="json",
            HTTP_X_SECRET_KEY="super-secret",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
