import uuid

from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


User = get_user_model()


class UserRole(models.TextChoices):
    """Роли пользователей"""

    READER = 'reader', 'Читатель'
    AUTHOR = 'author', 'Автор'
    MODERATOR = 'moderator', 'Модератор'
    ADMIN = 'admin', 'Администратор'
    FINANCE_MANAGER = 'finance_manager', 'Финансовый менеджер'


class AuthorProfile(models.Model):
    """Профиль автора"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='author_profile', verbose_name='Пользователь')
    bio = models.TextField(blank=True, max_length=2000, verbose_name='Биография', help_text='Краткая информация об авторе')
    website = models.URLField(blank=True, verbose_name='Веб-сайт')
    telegram = models.CharField(max_length=100, blank=True, verbose_name='Telegram')
    vkontakte = models.URLField(blank=True, verbose_name='ВКонтакте')
    is_approved = models.BooleanField(default=False, verbose_name='Подтверждён автором', help_text='Статус подтвержден модератором')
    requested_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата запроса на статус автора')
    approved_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата подтверждения')
    total_views = models.PositiveIntegerField(default=0, verbose_name='Всего просмотров')
    total_sales = models.PositiveIntegerField(default=0, verbose_name='Всего продаж')
    total_donations = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Всего донатов')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Профиль автора'
        verbose_name_plural = 'Профили авторов'
        ordering = ['-total_views']

    def __str__(self):
        return f"Автор: {self.user.username}"

    @property
    def full_name(self):
        """Полное имя автора"""

        return f"{self.user.first_name} {self.user.last_name}".strip() or self.user.username


class ReaderProfile(models.Model):
    """Профиль читателя"""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='reader_profile', verbose_name='Пользователь')
    avatar = models.ImageField(upload_to='avatars/readers/', blank=True, null=True, verbose_name='Аватар')
    is_active = models.BooleanField(default=True, verbose_name='Активен', help_text='Может ли пользователь использовать профиль')
    preferred_genres = models.ManyToManyField('books.Genre', blank=True, related_name='readers', verbose_name='Предпочитаемые жанры')
    books_read = models.PositiveIntegerField(default=0, verbose_name='Прочитано книг')
    reviews_written = models.PositiveIntegerField(default=0, verbose_name='Написано отзывов')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Профиль читателя'
        verbose_name_plural = 'Профили читателей'
        ordering = ['-books_read']

    def __str__(self):
        return f"Читатель: {self.user.username}"


class Bookmark(models.Model):
    """Закладка в книге"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='bookmarks', verbose_name='Читатель')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='bookmarks', verbose_name='Книга', null=True, blank=True)
    page_number = models.PositiveIntegerField(verbose_name='Номер страницы')
    note = models.TextField(blank=True, max_length=500, verbose_name='Заметка')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Закладка'
        verbose_name_plural = 'Закладки'
        constraints = [
            models.UniqueConstraint(
                fields=['reader', 'book', 'page_number'],
                name='profiles_bookmark_unique_reader_book_page',
            ),
        ]

    def __str__(self):
        return f"Закладка: {self.reader.user.username} (стр. {self.page_number})"


class ReadingHistory(models.Model):
    """История чтения"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='reading_history', verbose_name='Читатель')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='reading_history', verbose_name='Книга', null=True, blank=True)
    started_at = models.DateTimeField(auto_now_add=True, verbose_name='Начало чтения')
    finished_at = models.DateTimeField(null=True, blank=True, verbose_name='Окончание чтения')
    last_page_read = models.PositiveIntegerField(default=0, verbose_name='Последняя прочитанная страница')
    progress_percentage = models.PositiveIntegerField(default=0, validators=[MaxValueValidator(100)], verbose_name='Процент прогресса')
    is_completed = models.BooleanField(default=False, verbose_name='Завершено')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'История чтения'
        verbose_name_plural = 'Истории чтения'
        ordering = ['-started_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reader', 'book'],
                name='profiles_reading_history_unique_reader_book',
            ),
        ]

    def __str__(self):
        status = "завершено" if self.is_completed else "в процессе"
        return f"{self.reader.user.username} ({status})"

    @property
    def current_page(self):
        return self.last_page_read

    def update_progress(self, current_page, total_pages):
        """Обновить прогресс чтения"""

        self.last_page_read = current_page
        self.progress_percentage = int((current_page / total_pages) * 100) if total_pages > 0 else 0

        completed_now = total_pages > 0 and current_page >= total_pages
        if completed_now:
            if not self.is_completed:
                self.finished_at = timezone.now()
            self.is_completed = True
        else:
            self.is_completed = False
            self.finished_at = None

        self.save(update_fields=['last_page_read', 'progress_percentage', 'is_completed', 'finished_at', 'updated_at'])


class Review(models.Model):
    """Отзыв о книге"""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader = models.ForeignKey(ReaderProfile, on_delete=models.CASCADE, related_name='reviews', verbose_name='Читатель')
    book = models.ForeignKey('books.Book', on_delete=models.CASCADE, related_name='reviews', verbose_name='Книга', null=True, blank=True)
    rating = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], verbose_name='Рейтинг')
    text = models.TextField(max_length=2000, verbose_name='Текст отзыва')
    is_verified_purchase = models.BooleanField(default=False, verbose_name='Проверенная покупка')
    helpful_count = models.PositiveIntegerField(default=0, verbose_name='Полезных голосов')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reader', 'book'],
                name='profiles_review_unique_reader_book',
            ),
        ]

    def __str__(self):
        return f"Отзыв: {self.reader.user.username} ({self.rating}/5)"

    def mark_as_helpful(self):
        """Отметить отзыв как полезный"""

        self.helpful_count += 1
        self.save(update_fields=['helpful_count'])
