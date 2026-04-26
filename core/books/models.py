"""Модели книг и жанров."""
import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from core.profiles.models import AuthorProfile, ReaderProfile


class Genre(models.Model):
    """Жанр книги."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, verbose_name='Название жанра')
    slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name='Slug')
    description = models.TextField(blank=True, max_length=500, verbose_name='Описание жанра')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Жанр'
        verbose_name_plural = 'Жанры'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BookStatus(models.TextChoices):
    """Статусы книги."""

    DRAFT = 'draft', 'Черновик'
    PUBLISHED = 'published', 'Опубликовано'
    ARCHIVED = 'archived', 'Архивировано'


class Book(models.Model):
    """Книга."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, verbose_name='Название')
    slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='Slug')
    authors = models.ManyToManyField(AuthorProfile, related_name='books', verbose_name='Авторы')
    description = models.TextField(max_length=5000, blank=True, verbose_name='Описание')
    genres = models.ManyToManyField(Genre, related_name='books', blank=True, verbose_name='Жанры')

    cover = models.ImageField(upload_to='covers/', null=True, blank=True, verbose_name='Обложка')
    file = models.FileField(upload_to='books/', null=True, blank=True, verbose_name='Файл книги')

    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Цена')
    is_free = models.BooleanField(default=False, verbose_name='Бесплатно')
    is_free_to_read = models.BooleanField(default=True, verbose_name='Бесплатное чтение')
    allow_download = models.BooleanField(default=False, verbose_name='Разрешить скачивание')

    pages = models.PositiveIntegerField(default=0, verbose_name='Количество страниц')
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата публикации')

    views_count = models.PositiveIntegerField(default=0, verbose_name='Просмотры')
    downloads_count = models.PositiveIntegerField(default=0, verbose_name='Скачивания')

    status = models.CharField(
        max_length=20,
        choices=BookStatus.choices,
        default=BookStatus.DRAFT,
        verbose_name='Статус',
    )
    is_active = models.BooleanField(default=True, verbose_name='Активно')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Книга'
        verbose_name_plural = 'Книги'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['status', 'is_active']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def update_views(self, amount=1):
        """Увеличить счетчик просмотров."""
        self.views_count += amount
        self.save(update_fields=['views_count'])

    def update_downloads(self, amount=1):
        """Увеличить счетчик скачиваний."""
        self.downloads_count += amount
        self.save(update_fields=['downloads_count'])

    @property
    def display_price(self):
        """Отображаемая цена."""
        return 0 if self.is_free else self.price

    @property
    def authors_list(self):
        """Список имен авторов."""
        return ', '.join(author.full_name for author in self.authors.all())

    def can_read(self, user):
        """Проверка, может ли пользователь читать книгу."""
        if not user.is_authenticated:
            return False

        if self.is_free_to_read:
            return True

        return False

    def can_download(self, user):
        """Проверка, может ли пользователь скачать книгу."""
        if not user.is_authenticated:
            return False

        if not self.allow_download:
            return False

        if self.is_free or self.is_free_to_read:
            return True

        return False


class BookLike(models.Model):
    """Book like."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader = models.ForeignKey(
        ReaderProfile,
        on_delete=models.CASCADE,
        related_name='book_likes',
        verbose_name='Читатель',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='Книга',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Лайк книги'
        verbose_name_plural = 'Лайки книг'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reader', 'book'],
                name='books_book_like_unique_reader_book',
            ),
        ]

    def __str__(self):
        return f"Лайк книги: {self.reader.user.username} -> {self.book.title}"


class ReviewLike(models.Model):
    """Review like."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader = models.ForeignKey(
        ReaderProfile,
        on_delete=models.CASCADE,
        related_name='review_likes',
        verbose_name='Читатель',
    )
    review = models.ForeignKey(
        'profiles.Review',
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='Отзыв',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Лайк отзыва'
        verbose_name_plural = 'Лайки отзывов'
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(
                fields=['reader', 'review'],
                name='books_review_like_unique_reader_review',
            ),
        ]

    def __str__(self):
        return f"Лайк отзыва: {self.reader.user.username} -> {self.review_id}"


class BookComment(models.Model):
    """Book comment with one reply level."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reader = models.ForeignKey(
        ReaderProfile,
        on_delete=models.CASCADE,
        related_name='book_comments',
        verbose_name='Читатель',
    )
    book = models.ForeignKey(
        Book,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Книга',
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='replies',
        null=True,
        blank=True,
        verbose_name='Родительский комментарий',
    )
    text = models.TextField(max_length=2000, verbose_name='Текст комментария')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Комментарий к книге'
        verbose_name_plural = 'Комментарии к книгам'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['book', 'created_at']),
            models.Index(fields=['parent', 'created_at']),
        ]

    def __str__(self):
        return f"Комментарий: {self.reader.user.username} -> {self.book.title}"

    def clean(self):
        super().clean()

        if self.parent_id and self.parent and self.parent.book_id != self.book_id:
            raise ValidationError({'parent': 'Parent comment must belong to the same book.'})

        if self.parent_id and self.parent and self.parent.parent_id is not None:
            raise ValidationError({'parent': 'Replies can only target top-level comments.'})

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
