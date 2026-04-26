import os
import shutil

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from core.books.models import Book, BookStatus, Genre, ReviewLike
from core.profiles.models import AuthorProfile, Bookmark, ReadingHistory, Review


User = get_user_model()


@override_settings(ROOT_URLCONF='core.open_page.urls')
class ReadingAPITests(APITestCase):
    def setUp(self):
        self.media_root = os.path.join(os.getcwd(), 'test_media_reading')
        shutil.rmtree(self.media_root, ignore_errors=True)
        os.makedirs(os.path.join(self.media_root, 'books'), exist_ok=True)
        self.media_override = override_settings(MEDIA_ROOT=self.media_root)
        self.media_override.enable()

        with open(os.path.join(self.media_root, 'books', 'readable-book.pdf'), 'wb') as file_handle:
            file_handle.write(b'pdf-data')
        with open(os.path.join(self.media_root, 'books', 'locked-book.pdf'), 'wb') as file_handle:
            file_handle.write(b'locked-data')

        self.reader_user = User.objects.create_user(
            username='reader1',
            email='reader1@example.com',
            password='testpass123',
        )
        self.author_user = User.objects.create_user(
            username='author1',
            email='author1@example.com',
            password='testpass123',
        )
        self.moderator_user = User.objects.create_user(
            username='moderator1',
            email='moderator1@example.com',
            password='testpass123',
            role='moderator',
        )
        self.pending_author_user = User.objects.create_user(
            username='pending1',
            email='pending1@example.com',
            password='testpass123',
        )

        self.author_profile = AuthorProfile.objects.create(user=self.author_user, is_approved=True)
        self.genre = Genre.objects.create(name='Adventure')

        self.book = Book.objects.create(
            title='Readable Book',
            description='Book for reading tests',
            status=BookStatus.PUBLISHED,
            is_active=True,
            is_free=True,
            is_free_to_read=True,
            allow_download=True,
            pages=10,
            file='books/readable-book.pdf',
        )
        self.book.authors.add(self.author_profile)
        self.book.genres.add(self.genre)

        self.paid_book = Book.objects.create(
            title='Locked Book',
            description='Not readable for regular readers',
            status=BookStatus.PUBLISHED,
            is_active=True,
            is_free=False,
            is_free_to_read=False,
            allow_download=False,
            pages=8,
            file='books/locked-book.pdf',
        )
        self.paid_book.authors.add(self.author_profile)

    def tearDown(self):
        self.media_override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_book_read_creates_history(self):
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.get(reverse('reading:book-read', kwargs={'slug': self.book.slug}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['book']['slug'], self.book.slug)
        self.assertEqual(str(response.data['reading_history']['book']), str(self.book.pk))
        self.assertEqual(response.data['reading_history']['current_page'], 0)
        self.assertIn('updated_at', response.data['reading_history'])
        self.assertEqual(response.data['bookmarks'], [])
        self.assertTrue(
            ReadingHistory.objects.filter(reader=self.reader_user.reader_profile, book=self.book).exists()
        )

    def test_book_read_returns_book_specific_bookmarks(self):
        other_bookmark_book = Book.objects.create(
            title='Second readable book',
            description='Another readable book',
            status=BookStatus.PUBLISHED,
            is_active=True,
            is_free=True,
            is_free_to_read=True,
            pages=20,
        )
        other_bookmark_book.authors.add(self.author_profile)
        bookmark = Bookmark.objects.create(
            reader=self.reader_user.reader_profile,
            book=self.book,
            page_number=4,
            note='Resume here',
        )
        Bookmark.objects.create(
            reader=self.reader_user.reader_profile,
            book=other_bookmark_book,
            page_number=2,
            note='Other book page',
        )
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.get(reverse('reading:book-read', kwargs={'slug': self.book.slug}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['bookmarks']), 1)
        self.assertEqual(response.data['bookmarks'][0]['id'], str(bookmark.id))
        self.assertEqual(response.data['bookmarks'][0]['page_number'], 4)

    def test_book_read_blocks_non_readable_book_for_regular_reader(self):
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.get(reverse('reading:book-read', kwargs={'slug': self.paid_book.slug}))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(response.data['type'], 'permission_denied')

    def test_book_download_returns_file_and_updates_counter(self):
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.get(reverse('reading:book-download', kwargs={'slug': self.book.slug}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.book.refresh_from_db()
        self.assertEqual(self.book.downloads_count, 1)
        self.assertIn('attachment;', response['Content-Disposition'])

    def test_book_progress_updates_history_and_books_read(self):
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.post(
            reverse('reading:book-progress', kwargs={'slug': self.book.slug}),
            {'current_page': 10},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        history = ReadingHistory.objects.get(reader=self.reader_user.reader_profile, book=self.book)
        self.assertEqual(response.data['current_page'], 10)
        self.assertEqual(response.data['last_page_read'], 10)
        self.assertIn('updated_at', response.data)
        self.assertTrue(history.is_completed)
        self.reader_user.reader_profile.refresh_from_db()
        self.assertEqual(self.reader_user.reader_profile.books_read, 1)

    def test_book_progress_accepts_last_page_read_alias(self):
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.post(
            reverse('reading:book-progress', kwargs={'slug': self.book.slug}),
            {'last_page_read': 6},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['current_page'], 6)
        history = ReadingHistory.objects.get(reader=self.reader_user.reader_profile, book=self.book)
        self.assertEqual(history.last_page_read, 6)

    def test_bookmark_routes_create_list_and_delete(self):
        self.client.force_authenticate(user=self.reader_user)

        create_response = self.client.post(
            reverse('reading:bookmark-create'),
            {'book': str(self.book.pk), 'page_number': 3, 'note': 'Remember this page'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        list_response = self.client.get(reverse('reading:bookmark-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        bookmark_id = create_response.data['id']
        delete_response = self.client.delete(
            reverse('reading:bookmark-delete', kwargs={'pk': bookmark_id})
        )
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Bookmark.objects.filter(pk=bookmark_id).exists())

    def test_bookmark_list_can_be_filtered_by_book(self):
        second_book = Book.objects.create(
            title='Filter Book',
            description='For bookmark filtering',
            status=BookStatus.PUBLISHED,
            is_active=True,
            is_free=True,
            is_free_to_read=True,
            pages=12,
        )
        second_book.authors.add(self.author_profile)
        Bookmark.objects.create(reader=self.reader_user.reader_profile, book=self.book, page_number=3)
        Bookmark.objects.create(reader=self.reader_user.reader_profile, book=second_book, page_number=5)
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.get(reverse('reading:bookmark-list'), {'book': str(self.book.pk)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(str(response.data[0]['book']), str(self.book.pk))

    def test_bookmark_create_rejects_duplicate_page(self):
        Bookmark.objects.create(reader=self.reader_user.reader_profile, book=self.book, page_number=3)
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.post(
            reverse('reading:bookmark-create'),
            {'book': str(self.book.pk), 'page_number': 3},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['type'], 'validation_error')
        self.assertIn('page_number', response.data['errors'])

    def test_reading_history_routes_create_list_update(self):
        self.client.force_authenticate(user=self.reader_user)

        create_response = self.client.post(
            reverse('reading:reading-history-create'),
            {'book': str(self.book.pk), 'last_page_read': 1},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        history_id = create_response.data['id']

        duplicate_response = self.client.post(
            reverse('reading:reading-history-create'),
            {'book': str(self.book.pk)},
            format='json',
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_200_OK)

        list_response = self.client.get(reverse('reading:reading-history-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        update_response = self.client.patch(
            reverse('reading:reading-history-update', kwargs={'pk': history_id}),
            {'last_page_read': 10},
            format='json',
        )
        self.assertEqual(update_response.status_code, status.HTTP_200_OK)
        history = ReadingHistory.objects.get(pk=history_id)
        self.assertTrue(history.is_completed)

    def test_reading_progress_can_reset_completion_and_books_read(self):
        self.client.force_authenticate(user=self.reader_user)

        self.client.post(
            reverse('reading:book-progress', kwargs={'slug': self.book.slug}),
            {'current_page': 10},
            format='json',
        )
        downgrade_response = self.client.post(
            reverse('reading:book-progress', kwargs={'slug': self.book.slug}),
            {'current_page': 5},
            format='json',
        )

        self.assertEqual(downgrade_response.status_code, status.HTTP_200_OK)
        history = ReadingHistory.objects.get(reader=self.reader_user.reader_profile, book=self.book)
        self.assertFalse(history.is_completed)
        self.reader_user.reader_profile.refresh_from_db()
        self.assertEqual(self.reader_user.reader_profile.books_read, 0)

    def test_review_routes_create_list_detail_helpful_delete(self):
        self.client.force_authenticate(user=self.reader_user)

        create_response = self.client.post(
            reverse('reading:review-create'),
            {'book': str(self.book.pk), 'rating': 5, 'text': 'Great book'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        review_id = create_response.data['id']

        list_response = self.client.get(reverse('reading:review-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        filtered_response = self.client.get(
            reverse('reading:review-list'),
            {'book': str(self.book.pk)},
        )
        self.assertEqual(filtered_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filtered_response.data), 1)

        detail_response = self.client.get(reverse('reading:review-detail', kwargs={'pk': review_id}))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)

        helpful_response = self.client.post(
            reverse('reading:review-helpful', kwargs={'pk': review_id}),
            format='json',
        )
        self.assertEqual(helpful_response.status_code, status.HTTP_200_OK)
        self.assertEqual(helpful_response.data['helpful_count'], 1)

        delete_response = self.client.delete(reverse('reading:review-delete', kwargs={'pk': review_id}))
        self.assertEqual(delete_response.status_code, status.HTTP_204_NO_CONTENT)
        self.reader_user.reader_profile.refresh_from_db()
        self.assertEqual(self.reader_user.reader_profile.reviews_written, 0)

    def test_review_like_routes_and_metadata(self):
        self.client.force_authenticate(user=self.reader_user)

        create_response = self.client.post(
            reverse('reading:review-create'),
            {'book': str(self.book.pk), 'rating': 5, 'text': 'Great book'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        review_id = create_response.data['id']

        like_response = self.client.post(
            reverse('reading:review-like', kwargs={'pk': review_id}),
            format='json',
        )
        self.assertEqual(like_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(like_response.data['liked'])
        self.assertEqual(like_response.data['likes_count'], 1)
        self.assertEqual(like_response.data['helpful_count'], 1)

        duplicate_like_response = self.client.post(
            reverse('reading:review-like', kwargs={'pk': review_id}),
            format='json',
        )
        self.assertEqual(duplicate_like_response.status_code, status.HTTP_200_OK)
        self.assertEqual(duplicate_like_response.data['likes_count'], 1)

        detail_response = self.client.get(reverse('reading:review-detail', kwargs={'pk': review_id}))
        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertTrue(detail_response.data['is_liked'])
        self.assertEqual(detail_response.data['likes_count'], 1)
        self.assertEqual(detail_response.data['helpful_count'], 1)

        delete_response = self.client.delete(
            reverse('reading:review-like', kwargs={'pk': review_id})
        )
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)
        self.assertFalse(delete_response.data['liked'])
        self.assertEqual(delete_response.data['likes_count'], 0)
        self.assertFalse(ReviewLike.objects.filter(review_id=review_id).exists())

    def test_review_create_rejects_duplicate_review(self):
        Review.objects.create(reader=self.reader_user.reader_profile, book=self.book, rating=4, text='Old review')
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.post(
            reverse('reading:review-create'),
            {'book': str(self.book.pk), 'rating': 5, 'text': 'Duplicate review'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['type'], 'validation_error')
        self.assertIn('book', response.data['errors'])

    def test_review_detail_not_found_uses_error_envelope(self):
        self.client.force_authenticate(user=self.reader_user)

        response = self.client.get(reverse('reading:review-detail', kwargs={'pk': '00000000-0000-0000-0000-000000000000'}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['type'], 'not_found')

    def test_author_request_flow_for_moderator(self):
        self.client.force_authenticate(user=self.pending_author_user)

        create_response = self.client.post(
            reverse('reading:author-request'),
            {'bio': 'Want to publish books', 'website': 'https://writer.example.com'},
            format='json',
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        request_id = create_response.data['id']

        self.client.force_authenticate(user=self.moderator_user)
        list_response = self.client.get(reverse('reading:author-requests-list'))
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_response.data), 1)

        moderate_response = self.client.patch(
            reverse('reading:author-request-moderate', kwargs={'pk': request_id}),
            {'approve': True},
            format='json',
        )
        self.assertEqual(moderate_response.status_code, status.HTTP_200_OK)
        self.pending_author_user.refresh_from_db()
        self.assertTrue(self.pending_author_user.is_author)
        self.assertEqual(self.pending_author_user.role, 'author')

    def test_bookmark_unique_constraint_blocks_duplicate_rows(self):
        Bookmark.objects.create(reader=self.reader_user.reader_profile, book=self.book, page_number=7)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Bookmark.objects.create(reader=self.reader_user.reader_profile, book=self.book, page_number=7)

    def test_reading_history_unique_constraint_blocks_duplicate_rows(self):
        ReadingHistory.objects.create(reader=self.reader_user.reader_profile, book=self.book)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReadingHistory.objects.create(reader=self.reader_user.reader_profile, book=self.book)

    def test_review_unique_constraint_blocks_duplicate_rows(self):
        Review.objects.create(reader=self.reader_user.reader_profile, book=self.book, rating=4, text='First')

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Review.objects.create(reader=self.reader_user.reader_profile, book=self.book, rating=5, text='Second')

    def test_review_like_unique_constraint_blocks_duplicate_rows(self):
        review = Review.objects.create(
            reader=self.reader_user.reader_profile,
            book=self.book,
            rating=4,
            text='First',
        )
        ReviewLike.objects.create(reader=self.reader_user.reader_profile, review=review)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ReviewLike.objects.create(reader=self.reader_user.reader_profile, review=review)
