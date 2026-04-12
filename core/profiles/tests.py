from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from drf_spectacular.generators import SchemaGenerator
from rest_framework import status
from rest_framework.test import APITestCase

from core.profiles.models import AuthorProfile, ReaderProfile


User = get_user_model()


class AuthorProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_author',
            email='author@test.com',
            password='testpass123',
        )

    def test_create_author_profile_sets_expected_defaults(self):
        author_profile = AuthorProfile.objects.create(
            user=self.user,
            bio='Test bio',
            website='https://test.com',
            telegram='@testauthor',
        )

        self.assertEqual(author_profile.user, self.user)
        self.assertEqual(author_profile.bio, 'Test bio')
        self.assertFalse(author_profile.is_approved)
        self.assertIsNone(author_profile.approved_at)
        self.assertEqual(author_profile.total_views, 0)
        self.assertEqual(author_profile.total_sales, 0)
        self.assertEqual(author_profile.total_donations, 0)

    def test_full_name_falls_back_to_user_name_parts(self):
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save(update_fields=['first_name', 'last_name'])

        author_profile = AuthorProfile.objects.create(user=self.user)

        self.assertEqual(author_profile.full_name, 'John Doe')


class ReaderProfileModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_reader',
            email='reader@test.com',
            password='testpass123',
        )

    def test_user_creation_auto_creates_reader_profile(self):
        reader_profile = self.user.reader_profile

        self.assertEqual(reader_profile.user, self.user)
        self.assertTrue(reader_profile.is_active)
        self.assertEqual(reader_profile.books_read, 0)
        self.assertEqual(reader_profile.reviews_written, 0)

    def test_updating_user_does_not_create_duplicate_reader_profile(self):
        self.user.first_name = 'Updated'
        self.user.save(update_fields=['first_name'])

        self.assertEqual(ReaderProfile.objects.filter(user=self.user).count(), 1)


class ProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123',
        )

    def test_get_current_user_profile_requires_authentication(self):
        response = self.client.get(reverse('profiles:current-user-profile'))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
            response.content.decode('utf-8', errors='replace'),
        )

    def test_get_current_user_profile_returns_nested_profiles(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.get(reverse('profiles:current-user-profile'))

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content.decode('utf-8', errors='replace'),
        )
        self.assertEqual(response.data['username'], self.user.username)
        self.assertIsNotNone(response.data['reader_profile'])
        self.assertIsNone(response.data['author_profile'])

    def test_patch_current_user_profile_updates_only_editable_fields(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse('profiles:current-user-profile'),
            {
                'email': 'newemail@test.com',
                'first_name': 'New',
                'last_name': 'Name',
                'role': 'admin',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@test.com')
        self.assertEqual(self.user.first_name, 'New')
        self.assertEqual(self.user.last_name, 'Name')
        self.assertEqual(self.user.role, 'reader')

    def test_get_public_profile_by_id_is_available_without_auth(self):
        response = self.client.get(
            reverse('profiles:public-user-profile', kwargs={'pk': self.user.pk})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.user.id)
        self.assertEqual(response.data['username'], self.user.username)

    def test_get_public_profile_by_username_uses_dedicated_route(self):
        response = self.client.get(
            reverse('profiles:user-profile-by-username', kwargs={'username': self.other_user.username})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], self.other_user.username)

    def test_create_reader_profile_returns_conflict_when_profile_exists(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(reverse('profiles:reader-profile'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_new_user_already_has_reader_profile(self):
        self.assertTrue(hasattr(self.other_user, 'reader_profile'))
        self.assertEqual(ReaderProfile.objects.filter(user=self.other_user).count(), 1)

    def test_create_author_profile_creates_pending_profile(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('profiles:author-profile'),
            {
                'bio': 'I am a writer',
                'website': 'https://myblog.com',
                'telegram': '@writer',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.user.refresh_from_db()
        self.assertTrue(hasattr(self.user, 'author_profile'))
        self.assertFalse(self.user.author_profile.is_approved)
        self.assertIsNotNone(self.user.author_profile.requested_at)

    def test_create_author_profile_returns_validation_errors(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse('profiles:author-profile'),
            {'website': 'not-a-valid-url'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('website', response.data)


class ProfileSchemaTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.schema = SchemaGenerator().get_schema(request=None, public=True)

    def test_bearer_security_scheme_is_registered(self):
        security_schemes = self.schema['components']['securitySchemes']

        self.assertIn('Bearer', security_schemes)
        self.assertEqual(security_schemes['Bearer']['type'], 'http')
        self.assertEqual(security_schemes['Bearer']['scheme'], 'bearer')
        self.assertEqual(security_schemes['Bearer']['bearerFormat'], 'JWT')

    def test_protected_profile_endpoint_uses_bearer_auth(self):
        current_profile_get = self.schema['paths']['/api/profile/']['get']

        self.assertEqual(current_profile_get['operationId'], 'profile_me_retrieve')
        self.assertEqual(current_profile_get['security'], [{'Bearer': []}])

    def test_profile_routes_have_stable_unique_operation_ids(self):
        self.assertEqual(
            self.schema['paths']['/api/profile/{id}/']['get']['operationId'],
            'profile_public_retrieve',
        )
        self.assertEqual(
            self.schema['paths']['/api/profile/username/{username}/']['get']['operationId'],
            'profile_username_retrieve',
        )
        self.assertEqual(
            self.schema['paths']['/api/profile/reader/']['post']['operationId'],
            'profile_reader_create',
        )
        self.assertEqual(
            self.schema['paths']['/api/profile/author/']['post']['operationId'],
            'profile_author_create',
        )
