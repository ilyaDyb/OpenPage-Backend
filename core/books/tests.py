# """
# Tests for Book model and reading functionality
# """
# from django.test import TestCase
# from django.contrib.auth import get_user_model
# from django.utils import timezone
# from core.books.models import Book, Genre, BookStatus
# from core.profiles.models import AuthorProfile, ReaderProfile

# User = get_user_model()


# class BookModelTests(TestCase):
#     """Тесты для модели Book"""
    
#     def setUp(self):
#         """Создание тестовых данных"""
#         self.user = User.objects.create_user(
#             username='testuser',
#             email='test@example.com',
#             password='testpass123'
#         )
        
#         # Создаем профиль автора
#         self.author_profile = AuthorProfile.objects.create(
#             user=self.user,
#             bio='Test author',
#             is_approved=True
#         )
        
#         # Создаем книгу
#         self.book = Book.objects.create(
#             title='Test Book',
#             slug='test-book',
#             description='Test description',
#             price=99.99,
#             is_free=False,
#             is_free_to_read=True,
#             allow_download=False,
#             pages=200,
#             status=BookStatus.PUBLISHED,
#             is_active=True
#         )
#         self.book.authors.add(self.author_profile)
    
#     def test_book_creation(self):
#         """Проверка создания книги"""
#         self.assertEqual(self.book.title, 'Test Book')
#         self.assertEqual(self.book.slug, 'test-book')
#         self.assertEqual(self.book.pages, 200)
#         self.assertEqual(self.book.status, BookStatus.PUBLISHED)
#         self.assertTrue(self.book.is_active)
    
#     def test_default_values(self):
#         """Проверка значений по умолчанию"""
#         book2 = Book.objects.create(
#             title='Another Book',
#             slug='another-book'
#         )
        
#         self.assertEqual(book2.price, 0)
#         self.assertFalse(book2.is_free)
#         self.assertTrue(book2.is_free_to_read)  # default=True
#         self.assertFalse(book2.allow_download)  # default=False
#         self.assertEqual(book2.status, BookStatus.DRAFT)
#         self.assertTrue(book2.is_active)
    
#     def test_can_read_free_book(self):
#         """Проверка can_read для бесплатной книги"""
#         # Книга с is_free_to_read=True
#         self.assertTrue(self.book.can_read(self.user))
    
#     def test_can_read_paid_book(self):
#         """Проверка can_read для платной книги"""
#         self.book.is_free_to_read = False
#         self.book.save()
        
#         # Пока возвращает False (нет системы покупок)
#         self.assertFalse(self.book.can_read(self.user))
    
#     def test_can_read_unauthenticated(self):
#         """Проверка can_read для неавторизованного"""
#         from django.contrib.auth.models import AnonymousUser
        
#         self.assertFalse(self.book.can_read(AnonymousUser()))
    
#     def test_can_download_allowed(self):
#         """Проверка can_download с разрешением"""
#         self.book.allow_download = True
#         self.book.is_free_to_read = True
#         self.book.save()
        
#         self.assertTrue(self.book.can_download(self.user))
    
#     def test_can_download_forbidden(self):
#         """Проверка can_download без разрешения"""
#         self.book.allow_download = False
#         self.book.save()
        
#         self.assertFalse(self.book.can_download(self.user))
    
#     def test_can_download_unauthenticated(self):
#         """Проверка can_download для неавторизованного"""
#         from django.contrib.auth.models import AnonymousUser
        
#         self.book.allow_download = True
#         self.book.save()
        
#         self.assertFalse(self.book.can_download(AnonymousUser()))
    
#     def test_book_slug_generation(self):
#         """Проверка автогенерации slug"""
#         book = Book.objects.create(title='My Test Book Title')
#         self.assertEqual(book.slug, 'my-test-book-title')
    
#     def test_book_authors_list(self):
#         """Проверка свойства authors_list"""
#         authors = self.book.authors_list
#         self.assertIn(self.author_profile.full_name, authors)
    
#     def test_update_views(self):
#         """Проверка обновления счетчика просмотров"""
#         initial_views = self.book.views_count
#         self.book.update_views(5)
        
#         self.assertEqual(self.book.views_count, initial_views + 5)
    
#     def test_update_downloads(self):
#         """Проверка обновления счетчика скачиваний"""
#         initial_downloads = self.book.downloads_count
#         self.book.update_downloads(3)
        
#         self.assertEqual(self.book.downloads_count, initial_downloads + 3)
    
#     def test_display_price(self):
#         """Проверка отображаемой цены"""
#         # Бесплатная книга
#         self.book.is_free = True
#         self.book.save()
#         self.assertEqual(self.book.display_price, 0)
        
#         # Платная книга
#         self.book.is_free = False
#         self.book.price = 199.99
#         self.book.save()
#         self.assertEqual(self.book.display_price, 199.99)


# class GenreModelTests(TestCase):
#     """Тесты для модели Genre"""
    
#     def test_genre_creation(self):
#         """Проверка создания жанра"""
#         genre = Genre.objects.create(
#             name='Фантастика',
#             description='Научная фантастика и фэнтези'
#         )
        
#         self.assertEqual(genre.name, 'Фантастика')
#         self.assertIsNotNone(genre.slug)
#         self.assertEqual(genre.slug, 'fantastika')
    
#     def test_genre_slug_generation(self):
#         """Проверка автогенерации slug"""
#         genre = Genre.objects.create(name='Приключенческий Роман')
#         self.assertEqual(genre.slug, 'priklyuchencheskiy-roman')
    
#     def test_genre_books_count(self):
#         """Проверка количества книг в жанре"""
#         genre = Genre.objects.create(name='Детектив')
        
#         # Создаем книгу с этим жанром
#         book = Book.objects.create(
#             title='Detective Story',
#             status=BookStatus.PUBLISHED,
#             is_active=True
#         )
#         book.genres.add(genre)
        
#         # Проверяем через аннотацию
#         from django.db.models import Count
#         annotated_genre = Genre.objects.annotate(
#             books_count=Count('books')
#         ).get(pk=genre.pk)
        
#         self.assertEqual(annotated_genre.books_count, 1)


# class BookReadingAPITests(TestCase):
#     """Тесты для API чтения книг"""
    
#     def setUp(self):
#         """Создание тестовых данных"""
#         self.user = User.objects.create_user(
#             username='reader',
#             email='reader@example.com',
#             password='testpass123'
#         )
        
#         # Создаем профиль читателя
#         self.reader_profile = ReaderProfile.objects.create(user=self.user)
        
#         # Создаем автора и книгу
#         author = User.objects.create_user(username='author', password='pass')
#         author_profile = AuthorProfile.objects.create(user=author, is_approved=True)
        
#         self.free_book = Book.objects.create(
#             title='Free Book',
#             slug='free-book',
#             is_free_to_read=True,
#             allow_download=True,
#             pages=100,
#             status=BookStatus.PUBLISHED,
#             is_active=True
#         )
#         self.free_book.authors.add(author_profile)
        
#         self.paid_book = Book.objects.create(
#             title='Paid Book',
#             slug='paid-book',
#             is_free_to_read=False,
#             allow_download=False,
#             pages=200,
#             status=BookStatus.PUBLISHED,
#             is_active=True
#         )
#         self.paid_book.authors.add(author_profile)
    
#     def test_read_free_book_success(self):
#         """Успешное чтение бесплатной книги"""
#         self.client.login(username='reader', password='testpass123')
        
#         response = self.client.get(f'/api/reading/books/{self.free_book.slug}/read/')
        
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(response.data['title'], 'Free Book')
    
#     def test_read_paid_book_forbidden(self):
#         """Попытка чтения платной книги без покупки"""
#         self.client.login(username='reader', password='testpass123')
        
#         response = self.client.get(f'/api/reading/books/{self.paid_book.slug}/read/')
        
#         self.assertEqual(response.status_code, 403)
    
#     def test_read_unauthenticated_forbidden(self):
#         """Чтение неавторизованным пользователем"""
#         response = self.client.get(f'/api/reading/books/{self.free_book.slug}/read/')
        
#         self.assertEqual(response.status_code, 401)
    
#     def test_update_progress_success(self):
#         """Успешное обновление прогресса"""
#         self.client.login(username='reader', password='testpass123')
        
#         response = self.client.post(
#             f'/api/reading/books/{self.free_book.slug}/progress/',
#             {'current_page': 50},
#             content_type='application/json'
#         )
        
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(response.data['progress_percentage'], 50)
#         self.assertEqual(response.data['last_page_read'], 50)
    
#     def test_update_progress_creates_history(self):
#         """Обновление прогресса создает историю чтения"""
#         self.client.login(username='reader', password='testpass123')
        
#         from core.profiles.models import ReadingHistory
        
#         # До обновления истории нет
#         self.assertFalse(ReadingHistory.objects.filter(
#             reader=self.reader_profile,
#             book=self.free_book
#         ).exists())
        
#         # Обновляем прогресс
#         self.client.post(
#             f'/api/reading/books/{self.free_book.slug}/progress/',
#             {'current_page': 25},
#             content_type='application/json'
#         )
        
#         # История создалась
#         self.assertTrue(ReadingHistory.objects.filter(
#             reader=self.reader_profile,
#             book=self.free_book
#         ).exists())
    
#     def test_download_free_book_success(self):
#         """Успешное скачивание бесплатной книги"""
#         self.client.login(username='reader', password='testpass123')
        
#         # Добавляем файл книге
#         from django.core.files.uploadedfile import SimpleUploadedFile
#         self.free_book.file.save(
#             'test.pdf',
#             SimpleUploadedFile('test.pdf', b'file content')
#         )
        
#         response = self.client.get(f'/api/reading/books/{self.free_book.slug}/download/')
        
#         self.assertEqual(response.status_code, 200)
#         self.assertEqual(response['Content-Type'], 'application/octet-stream')
    
#     def test_download_no_file_forbidden(self):
#         """Скачивание книги без файла"""
#         self.client.login(username='reader', password='testpass123')
        
#         response = self.client.get(f'/api/reading/books/{self.free_book.slug}/download/')
        
#         self.assertEqual(response.status_code, 404)
