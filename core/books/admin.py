from django.contrib import admin
from django.db.models import Count
from django.utils import timezone

from core.books.models import Book, BookComment, BookLike, BookStatus, Genre, ReviewLike


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'books_count', 'created_at', 'updated_at')
    search_fields = ('name', 'slug', 'description')
    readonly_fields = ('id', 'created_at', 'updated_at')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('name',)

    @admin.display(description='Книг')
    def books_count(self, obj):
        return obj.books.count()


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'authors_display',
        'status',
        'is_active',
        'display_price_admin',
        'pages',
        'views_count',
        'downloads_count',
        'likes_count',
        'comments_count',
        'reviews_count',
        'created_at',
    )
    list_filter = (
        'status',
        'is_active',
        'is_free',
        'is_free_to_read',
        'allow_download',
        'genres',
        'created_at',
        'published_at',
    )
    search_fields = (
        'title',
        'slug',
        'description',
        'authors__user__username',
        'authors__user__first_name',
        'authors__user__last_name',
    )
    filter_horizontal = ('authors', 'genres')
    readonly_fields = (
        'id',
        'authors_list',
        'views_count',
        'downloads_count',
        'likes_count',
        'comments_count',
        'reviews_count',
        'created_at',
        'updated_at',
        'published_at',
    )
    date_hierarchy = 'created_at'
    actions = ('publish_books', 'archive_books', 'activate_books', 'deactivate_books')

    fieldsets = (
        (
            'Основная информация',
            {
                'fields': ('id', 'title', 'slug', 'description', 'authors', 'authors_list', 'genres'),
            },
        ),
        (
            'Файлы',
            {
                'fields': ('cover', 'file', 'pages'),
            },
        ),
        (
            'Цена и доступ',
            {
                'fields': ('price', 'is_free', 'is_free_to_read', 'allow_download'),
            },
        ),
        (
            'Публикация',
            {
                'fields': ('status', 'is_active', 'published_at'),
            },
        ),
        (
            'Статистика',
            {
                'fields': (
                    'views_count',
                    'downloads_count',
                    'likes_count',
                    'comments_count',
                    'reviews_count',
                ),
                'classes': ('collapse',),
            },
        ),
        (
            'Мета',
            {
                'fields': ('created_at', 'updated_at'),
                'classes': ('collapse',),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .prefetch_related('authors', 'genres')
            .annotate(
                admin_likes_count=Count('likes', distinct=True),
                admin_comments_count=Count('comments', distinct=True),
                admin_reviews_count=Count('reviews', distinct=True),
            )
        )

    @admin.display(description='Авторы')
    def authors_display(self, obj):
        return obj.authors_list

    @admin.display(description='Цена')
    def display_price_admin(self, obj):
        return obj.display_price

    @admin.display(description='Лайков', ordering='admin_likes_count')
    def likes_count(self, obj):
        return getattr(obj, 'admin_likes_count', obj.likes.count())

    @admin.display(description='Комментариев', ordering='admin_comments_count')
    def comments_count(self, obj):
        return getattr(obj, 'admin_comments_count', obj.comments.count())

    @admin.display(description='Отзывов', ordering='admin_reviews_count')
    def reviews_count(self, obj):
        return getattr(obj, 'admin_reviews_count', obj.reviews.count())

    @admin.action(description='Опубликовать выбранные книги')
    def publish_books(self, request, queryset):
        updated = queryset.exclude(status=BookStatus.PUBLISHED).update(
            status=BookStatus.PUBLISHED,
            published_at=timezone.now(),
        )
        self.message_user(request, f'Опубликовано книг: {updated}')

    @admin.action(description='Архивировать выбранные книги')
    def archive_books(self, request, queryset):
        updated = queryset.exclude(status=BookStatus.ARCHIVED).update(status=BookStatus.ARCHIVED)
        self.message_user(request, f'Архивировано книг: {updated}')

    @admin.action(description='Активировать выбранные книги')
    def activate_books(self, request, queryset):
        updated = queryset.filter(is_active=False).update(is_active=True)
        self.message_user(request, f'Активировано книг: {updated}')

    @admin.action(description='Деактивировать выбранные книги')
    def deactivate_books(self, request, queryset):
        updated = queryset.filter(is_active=True).update(is_active=False)
        self.message_user(request, f'Деактивировано книг: {updated}')

    def save_model(self, request, obj, form, change):
        if obj.status == BookStatus.PUBLISHED and obj.published_at is None:
            obj.published_at = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(BookLike)
class BookLikeAdmin(admin.ModelAdmin):
    list_display = ('book', 'reader', 'created_at')
    list_filter = ('created_at',)
    search_fields = (
        'book__title',
        'book__slug',
        'reader__user__username',
        'reader__user__email',
    )
    raw_id_fields = ('book', 'reader')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    list_select_related = ('book', 'reader__user')


@admin.register(ReviewLike)
class ReviewLikeAdmin(admin.ModelAdmin):
    list_display = ('review', 'review_book', 'reader', 'created_at')
    list_filter = ('created_at',)
    search_fields = (
        'review__book__title',
        'review__book__slug',
        'review__reader__user__username',
        'reader__user__username',
    )
    raw_id_fields = ('review', 'reader')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    list_select_related = ('review__book', 'review__reader__user', 'reader__user')

    @admin.display(description='Книга')
    def review_book(self, obj):
        return obj.review.book


@admin.register(BookComment)
class BookCommentAdmin(admin.ModelAdmin):
    list_display = ('short_text', 'book', 'reader', 'parent', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = (
        'text',
        'book__title',
        'book__slug',
        'reader__user__username',
        'reader__user__email',
    )
    raw_id_fields = ('book', 'reader', 'parent')
    readonly_fields = ('id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_select_related = ('book', 'reader__user', 'parent')

    @admin.display(description='Комментарий')
    def short_text(self, obj):
        text = obj.text.strip()
        return text[:80] + '...' if len(text) > 80 else text
