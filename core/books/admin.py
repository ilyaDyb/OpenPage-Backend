# """
# Админка для приложения books
# """
# from django.contrib import admin
# from core.books.models import Genre, Book


# @admin.register(Genre)
# class GenreAdmin(admin.ModelAdmin):
#     """Админка для жанров"""
#     list_display = ('id', 'name', 'slug', 'created_at')
#     list_display_links = ('id', 'name')
#     search_fields = ('name', 'description')
#     prepopulated_fields = {'slug': ('name',)}


# @admin.register(Book)
# class BookAdmin(admin.ModelAdmin):
#     """Админка для книг"""
#     list_display = (
#         'id', 'title', 'slug', 'get_authors', 'price', 
#         'is_free', 'is_free_to_read', 'allow_download',
#         'status', 'is_active', 'views_count', 'downloads_count',
#         'created_at'
#     )
#     list_display_links = ('id', 'title')
#     list_filter = ('status', 'is_active', 'is_free', 'allow_download', 'genres')
#     search_fields = ('title', 'description', 'authors__user__username')
#     prepopulated_fields = {'slug': ('title',)}
#     filter_horizontal = ('authors', 'genres')
#     readonly_fields = (
#         'views_count', 'downloads_count', 'created_at', 'updated_at',
#         'published_at'
#     )
    
#     fieldsets = (
#         ('Основная информация', {
#             'fields': ('title', 'slug', 'description', 'authors', 'genres')
#         }),
#         ('Файлы', {
#             'fields': ('cover', 'file', 'pages'),
#             'description': 'Загрузите обложку и файл книги'
#         }),
#         ('Цена и доступность', {
#             'fields': ('price', 'is_free', 'is_free_to_read', 'allow_download'),
#             'description': 'Настройте цену и условия доступа'
#         }),
#         ('Публикация', {
#             'fields': ('status', 'is_active', 'published_at'),
#             'description': 'Статус и дата публикации'
#         }),
#         ('Статистика', {
#             'fields': ('views_count', 'downloads_count'),
#             'classes': ('collapse',),
#             'description': 'Автоматически обновляемая статистика'
#         }),
#         ('Мета', {
#             'fields': ('created_at', 'updated_at'),
#             'classes': ('collapse',)
#         }),
#     )
    
#     def get_authors(self, obj):
#         """Получить список авторов"""
#         return ', '.join([author.full_name for author in obj.authors.all()])
#     get_authors.short_description = 'Авторы'
    
#     def save_model(self, request, obj, form, change):
#         """Автоматическая установка даты публикации при статусе published"""
#         if not change and obj.status == 'published':
#             from django.utils import timezone
#             obj.published_at = timezone.now()
#         super().save_model(request, obj, form, change)
