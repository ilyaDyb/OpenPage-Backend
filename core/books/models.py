# """
# Модели книг и жанров
# """
# import uuid
# from django.db import models
# from django.utils.text import slugify
# from django.urls import reverse
# from django.utils import timezone

# from core.profiles.models import AuthorProfile


# class Genre(models.Model):
#     """Жанр книги"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     name = models.CharField(max_length=100, unique=True, verbose_name='Название жанра')
#     slug = models.SlugField(max_length=100, unique=True, blank=True, verbose_name='Slug')
#     description = models.TextField(blank=True, max_length=500, verbose_name='Описание жанра')
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
#     updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
#     class Meta:
#         verbose_name = 'Жанр'
#         verbose_name_plural = 'Жанры'
#         ordering = ['name']
    
#     def __str__(self):
#         return self.name
    
#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)


# class BookStatus(models.TextChoices):
#     """Статусы книги"""
#     DRAFT = 'draft', 'Черновик'
#     PUBLISHED = 'published', 'Опубликовано'
#     ARCHIVED = 'archived', 'Архивировано'


# class Book(models.Model):
#     """Книга"""
#     id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
#     title = models.CharField(max_length=255, verbose_name='Название')
#     slug = models.SlugField(max_length=255, unique=True, blank=True, verbose_name='Slug')
#     authors = models.ManyToManyField(AuthorProfile, related_name='books', verbose_name='Авторы')
#     description = models.TextField(max_length=5000, blank=True, verbose_name='Описание')
#     genres = models.ManyToManyField(Genre, related_name='books', blank=True, verbose_name='Жанры')
    
#     # Файлы
#     cover = models.ImageField(upload_to='covers/', null=True, blank=True, verbose_name='Обложка')
#     file = models.FileField(upload_to='books/', null=True, blank=True, verbose_name='Файл книги')
    
#     # Цена и доступность
#     price = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Цена')
#     is_free = models.BooleanField(default=False, verbose_name='Бесплатно')
#     is_free_to_read = models.BooleanField(default=True, verbose_name='Бесплатное чтение')
#     allow_download = models.BooleanField(default=False, verbose_name='Разрешить скачивание')
    
#     # Параметры
#     pages = models.PositiveIntegerField(default=0, verbose_name='Количество страниц')
#     published_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата публикации')
    
#     # Статистика
#     views_count = models.PositiveIntegerField(default=0, verbose_name='Просмотры')
#     downloads_count = models.PositiveIntegerField(default=0, verbose_name='Скачивания')
    
#     # Статус и активность
#     status = models.CharField(max_length=20, choices=BookStatus.choices, default=BookStatus.DRAFT, verbose_name='Статус')
#     is_active = models.BooleanField(default=True, verbose_name='Активно')
    
#     # Мета
#     created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
#     updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
#     class Meta:
#         verbose_name = 'Книга'
#         verbose_name_plural = 'Книги'
#         ordering = ['-created_at']
#         indexes = [
#             models.Index(fields=['slug']),
#             models.Index(fields=['status', 'is_active']),
#         ]
    
#     def __str__(self):
#         return self.title
    
#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.title)
#         super().save(*args, **kwargs)
    
#     def get_absolute_url(self):
#         """Получить URL книги"""
#         return reverse('books:book-detail', kwargs={'pk': self.pk})
    
#     def update_views(self, amount=1):
#         """Увеличить счетчик просмотров"""
#         self.views_count += amount
#         self.save(update_fields=['views_count'])
    
#     def update_downloads(self, amount=1):
#         """Увеличить счетчик скачиваний"""
#         self.downloads_count += amount
#         self.save(update_fields=['downloads_count'])
    
#     @property
#     def display_price(self):
#         """Отображаемая цена (0 если бесплатно)"""
#         return 0 if self.is_free else self.price
    
#     @property
#     def authors_list(self):
#         """Список имен авторов"""
#         return ', '.join([author.full_name for author in self.authors.all()])
    
#     def can_read(self, user):
#         """
#         Проверка, может ли пользователь читать книгу
#         Если книга бесплатная (is_free_to_read=True) - всегда True
#         Если платная - нужна покупка (TODO: реализовать проверку покупки)
#         """
#         if not user.is_authenticated:
#             return False
        
#         if self.is_free_to_read:
#             return True
        
#         # TODO: Проверить покупку книги
#         # Пока возвращаем False для платных книг
#         return False
    
#     def can_download(self, user):
#         """
#         Проверка, может ли пользователь скачать книгу
#         Требуется allow_download=True и покупка (или бесплатность)
#         """
#         if not user.is_authenticated:
#             return False
        
#         if not self.allow_download:
#             return False
        
#         # Для бесплатных книг или купленных
#         if self.is_free or self.is_free_to_read:
#             return True
        
#         # TODO: Проверить покупку
#         return False
