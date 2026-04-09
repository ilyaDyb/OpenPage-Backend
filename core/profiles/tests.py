"""
Tests for profiles app
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from core.profiles.models import AuthorProfile, ReaderProfile

User = get_user_model()


class AuthorProfileModelTests(TestCase):
    """Тесты для модели AuthorProfile"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_author',
            email='author@test.com',
            password='testpass123'
        )
    
    def test_create_author_profile(self):
        """Создание профиля автора"""
        author_profile = AuthorProfile.objects.create(
            user=self.user,
            bio='Test bio',
            website='https://test.com',
            telegram='@testauthor'
        )
        
        self.assertEqual(author_profile.user, self.user)
        self.assertEqual(author_profile.bio, 'Test bio')
        self.assertFalse(author_profile.is_approved)
        self.assertIsNone(author_profile.approved_at)
    
    def test_author_profile_full_name(self):
        """Проверка full_name"""
        self.user.first_name = 'John'
        self.user.last_name = 'Doe'
        self.user.save()
        
        author_profile = AuthorProfile.objects.create(user=self.user)
        self.assertEqual(author_profile.full_name, 'John Doe')
    
    def test_author_profile_default_values(self):
        """Проверка значений по умолчанию"""
        author_profile = AuthorProfile.objects.create(user=self.user)
        
        self.assertEqual(author_profile.total_views, 0)
        self.assertEqual(author_profile.total_sales, 0)
        self.assertEqual(author_profile.total_donations, 0)
        self.assertFalse(author_profile.is_approved)


class ReaderProfileModelTests(TestCase):
    """Тесты для модели ReaderProfile"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='test_reader',
            email='reader@test.com',
            password='testpass123'
        )
    
    def test_create_reader_profile(self):
        """Создание профиля читателя"""
        reader_profile = ReaderProfile.objects.create(
            user=self.user,
            is_active=True
        )
        
        self.assertEqual(reader_profile.user, self.user)
        self.assertTrue(reader_profile.is_active)
        self.assertEqual(reader_profile.books_read, 0)
        self.assertEqual(reader_profile.reviews_written, 0)
    
    def test_reader_profile_default_values(self):
        """Проверка значений по умолчанию"""
        reader_profile = ReaderProfile.objects.create(user=self.user)
        
        self.assertTrue(reader_profile.is_active)
        self.assertEqual(reader_profile.books_read, 0)
        self.assertEqual(reader_profile.reviews_written, 0)


class ProfileAPITests(TestCase):
    """Тесты для API профилей"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.reader_profile = ReaderProfile.objects.create(user=self.user)
    
    def test_get_current_user_profile_authenticated(self):
        """Получение профиля текущего пользователя"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('profiles:profile-current')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')
    
    def test_get_current_user_profile_unauthenticated(self):
        """Получение профиля без авторизации"""
        url = reverse('profiles:profile-current')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_update_current_user_profile(self):
        """Обновление профиля пользователя"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('profiles:profile-current')
        data = {
            'email': 'newemail@test.com',
            'first_name': 'New',
            'last_name': 'Name'
        }
        response = self.client.patch(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, 'newemail@test.com')
        self.assertEqual(self.user.first_name, 'New')
    
    def test_get_public_profile(self):
        """Получение публичного профиля"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('profiles:profile-public', kwargs={'pk': self.user.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.user.id))


class CreateReaderProfileTests(TestCase):
    """Тесты для создания профиля читателя"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='newuser',
            email='new@test.com',
            password='testpass123'
        )
    
    def test_create_reader_profile_success(self):
        """Успешное создание профиля читателя"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('profiles:create-reader')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(hasattr(self.user, 'reader_profile'))
    
    def test_create_reader_profile_already_exists(self):
        """Попытка создать профиль повторно"""
        self.client.force_authenticate(user=self.user)
        ReaderProfile.objects.create(user=self.user)
        
        url = reverse('profiles:create-reader')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)


class CreateAuthorProfileTests(TestCase):
    """Тесты для создания профиля автора"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='authoruser',
            email='author@test.com',
            password='testpass123'
        )
    
    def test_create_author_profile_success(self):
        """Успешное создание профиля автора"""
        self.client.force_authenticate(user=self.user)
        
        url = reverse('profiles:create-author')
        data = {
            'bio': 'I am a writer',
            'website': 'https://myblog.com'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(hasattr(self.user, 'author_profile'))
        self.assertFalse(self.user.author_profile.is_approved)
    
    def test_create_author_profile_already_exists(self):
        """Попытка создать профиль автора повторно"""
        self.client.force_authenticate(user=self.user)
        AuthorProfile.objects.create(user=self.user)
        
        url = reverse('profiles:create-author')
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
