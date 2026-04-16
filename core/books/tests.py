from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.books.models import Book, BookStatus, Genre
from core.profiles.models import AuthorProfile


User = get_user_model()


class BookModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='author_user',
            email='author@example.com',
            password='testpass123',
            first_name='Jane',
            last_name='Writer',
        )
        self.author_profile = AuthorProfile.objects.create(user=self.user, is_approved=True)
        self.genre = Genre.objects.create(name='Fantasy')
        self.book = Book.objects.create(
            title='Test Book',
            description='Test description',
            price=Decimal('99.99'),
            is_free=False,
            is_free_to_read=True,
            allow_download=False,
            pages=200,
            status=BookStatus.PUBLISHED,
            is_active=True,
        )
        self.book.authors.add(self.author_profile)
        self.book.genres.add(self.genre)

    def test_book_generates_slug_when_missing(self):
        self.assertEqual(self.book.slug, 'test-book')

    def test_update_views_increments_counter(self):
        self.book.update_views(5)
        self.book.refresh_from_db()
        self.assertEqual(self.book.views_count, 5)

    def test_update_downloads_increments_counter(self):
        self.book.update_downloads(3)
        self.book.refresh_from_db()
        self.assertEqual(self.book.downloads_count, 3)

    def test_display_price_returns_zero_for_free_books(self):
        self.book.is_free = True
        self.assertEqual(self.book.display_price, 0)

    def test_authors_list_uses_author_full_name(self):
        self.assertEqual(self.book.authors_list, 'Jane Writer')

    def test_can_read_requires_authentication_for_paid_reading(self):
        self.book.is_free_to_read = False
        self.book.save(update_fields=['is_free_to_read'])
        self.assertFalse(self.book.can_read(self.user))

    def test_can_download_requires_permission_and_access(self):
        self.book.allow_download = True
        self.book.save(update_fields=['allow_download'])
        self.assertTrue(self.book.can_download(self.user))


class GenreModelTests(TestCase):
    def test_genre_generates_slug(self):
        genre = Genre.objects.create(name='Science Fiction')
        self.assertEqual(genre.slug, 'science-fiction')


class BookAPITests(APITestCase):
    def setUp(self):
        self.author_user = User.objects.create_user(
            username='author',
            email='author@test.com',
            password='testpass123',
        )
        self.reader_user = User.objects.create_user(
            username='reader',
            email='reader@test.com',
            password='testpass123',
        )
        self.moderator_user = User.objects.create_user(
            username='moderator',
            email='moderator@test.com',
            password='testpass123',
            role='moderator',
        )
        self.author_profile = AuthorProfile.objects.create(user=self.author_user, is_approved=True)
        self.unapproved_author_user = User.objects.create_user(
            username='pending_author',
            email='pending@test.com',
            password='testpass123',
        )
        self.unapproved_author_profile = AuthorProfile.objects.create(
            user=self.unapproved_author_user,
            is_approved=False,
        )
        self.genre = Genre.objects.create(name='Detective')
        self.book = Book.objects.create(
            title='Published Book',
            description='Detective story',
            is_free=True,
            price=Decimal('0.00'),
            is_free_to_read=True,
            allow_download=True,
            status=BookStatus.PUBLISHED,
            is_active=True,
            pages=150,
        )
        self.book.authors.add(self.author_profile)
        self.book.genres.add(self.genre)
        self.draft_book = Book.objects.create(
            title='Draft Book',
            description='Hidden draft',
            status=BookStatus.DRAFT,
            is_active=True,
            pages=50,
        )
        self.draft_book.authors.add(self.author_profile)

    def test_book_list_requires_authentication(self):
        response = self.client.get(reverse('books:book-list'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_book_list_returns_only_published_books(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.get(reverse('books:book-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Published Book')

    def test_book_detail_increments_views(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.get(reverse('books:book-detail', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(self.book.views_count, 1)

    def test_non_author_cannot_view_draft_book(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.get(reverse('books:book-detail', kwargs={'pk': self.draft_book.pk}))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_view_own_draft_book(self):
        self.client.force_authenticate(user=self.author_user)
        response = self.client.get(reverse('books:book-detail', kwargs={'pk': self.draft_book.pk}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_book_by_slug_returns_same_book(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.get(reverse('books:book-by-slug', kwargs={'slug': self.book.slug}))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(self.book.id))

    def test_book_create_requires_approved_author_profile(self):
        self.client.force_authenticate(user=self.unapproved_author_user)
        response = self.client.post(
            reverse('books:book-create'),
            {'title': 'Reader Book', 'pages': 20, 'status': BookStatus.DRAFT},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_create_adds_current_author(self):
        self.client.force_authenticate(user=self.author_user)
        response = self.client.post(
            reverse('books:book-create'),
            {
                'title': 'New Book',
                'description': 'Created by author',
                'genre_ids': [str(self.genre.id)],
                'status': BookStatus.DRAFT,
                'pages': 123,
                'is_free': True,
                'price': '0.00',
                'is_free_to_read': True,
                'allow_download': False,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        created_book = Book.objects.get(title='New Book')
        self.assertTrue(created_book.authors.filter(pk=self.author_profile.pk).exists())

    def test_book_update_is_limited_to_book_author(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.patch(
            reverse('books:book-update', kwargs={'pk': self.book.pk}),
            {'title': 'Hacked title'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_book_author_can_update_book(self):
        self.client.force_authenticate(user=self.author_user)
        response = self.client.patch(
            reverse('books:book-update', kwargs={'pk': self.book.pk}),
            {'title': 'Updated title'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(self.book.title, 'Updated title')

    def test_moderator_can_delete_book(self):
        self.client.force_authenticate(user=self.moderator_user)
        response = self.client.delete(reverse('books:book-delete', kwargs={'pk': self.book.pk}))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Book.objects.filter(pk=self.book.pk).exists())

    def test_book_create_validates_cover_and_file_extensions(self):
        self.client.force_authenticate(user=self.author_user)
        response = self.client.post(
            reverse('books:book-create'),
            {
                'title': 'Invalid upload book',
                'pages': 20,
                'status': BookStatus.DRAFT,
                'is_free': True,
                'price': '0.00',
                'cover': SimpleUploadedFile('cover.txt', b'bad cover', content_type='text/plain'),
                'file': SimpleUploadedFile('book.exe', b'bad file', content_type='application/octet-stream'),
            },
            format='multipart',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('cover', response.data)
        self.assertIn('file', response.data)

    def test_book_create_validates_unique_slug(self):
        self.client.force_authenticate(user=self.author_user)
        response = self.client.post(
            reverse('books:book-create'),
            {
                'title': 'Another title',
                'slug': self.book.slug,
                'pages': 20,
                'status': BookStatus.DRAFT,
                'is_free': True,
                'price': '0.00',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('slug', response.data)

    def test_genre_list_is_available_for_authenticated_user(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.get(reverse('books:genre-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]['name'], 'Detective')

    def test_genre_create_requires_moderator(self):
        self.client.force_authenticate(user=self.reader_user)
        response = self.client.post(
            reverse('books:genre-list'),
            {'name': 'Sci-Fi', 'description': 'Space stories'},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_genre_crud_works_for_moderator(self):
        self.client.force_authenticate(user=self.moderator_user)

        create_response = self.client.post(
            reverse('books:genre-list'),
            {'name': 'Sci-Fi', 'description': 'Space stories'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        genre_id = create_response.data['id']

        update_response = self.client.patch(
            reverse('books:genre-detail', kwargs={'pk': genre_id}),
            {'description': 'Updated description'},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        self.assertEqual(update_response.data['description'], 'Updated description')

        delete_response = self.client.delete(reverse('books:genre-detail', kwargs={'pk': genre_id}))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)

    def test_my_books_returns_current_author_books(self):
        self.client.force_authenticate(user=self.author_user)
        response = self.client.get(reverse('books:my-books'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
