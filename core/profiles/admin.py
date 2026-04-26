from django.contrib import admin
from django.utils import timezone

from core.profiles.models import AuthorProfile, Bookmark, ReaderProfile, ReadingHistory, Review


@admin.register(AuthorProfile)
class AuthorProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'full_name_display',
        'is_approved',
        'requested_at',
        'approved_at',
        'total_views',
        'total_sales',
        'total_donations',
        'created_at',
    )
    list_filter = ('is_approved', 'requested_at', 'approved_at', 'created_at')
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'telegram',
        'website',
    )
    raw_id_fields = ('user',)
    readonly_fields = (
        'created_at',
        'updated_at',
        'requested_at',
        'approved_at',
        'total_views',
        'total_sales',
        'total_donations',
    )
    list_select_related = ('user',)
    actions = ('approve_selected_authors',)

    fieldsets = (
        (
            'Пользователь',
            {
                'fields': ('user', 'bio'),
            },
        ),
        (
            'Контакты',
            {
                'fields': ('website', 'telegram', 'vkontakte'),
            },
        ),
        (
            'Модерация',
            {
                'fields': ('is_approved', 'requested_at', 'approved_at'),
            },
        ),
        (
            'Статистика',
            {
                'fields': ('total_views', 'total_sales', 'total_donations'),
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

    @admin.display(description='Полное имя')
    def full_name_display(self, obj):
        return obj.full_name

    @admin.action(description='Подтвердить выбранные профили авторов')
    def approve_selected_authors(self, request, queryset):
        approved_count = 0
        for profile in queryset.select_related('user'):
            changed = False
            if not profile.is_approved:
                profile.is_approved = True
                profile.approved_at = timezone.now()
                profile.save(update_fields=['is_approved', 'approved_at'])
                changed = True

            user = profile.user
            user_fields_to_update = []
            if not user.is_author:
                user.is_author = True
                user_fields_to_update.append('is_author')
            if getattr(user, 'role', 'reader') == 'reader':
                user.role = 'author'
                user_fields_to_update.append('role')
            if user_fields_to_update:
                user.save(update_fields=user_fields_to_update)
                changed = True

            if changed:
                approved_count += 1

        self.message_user(request, f'Подтверждено профилей авторов: {approved_count}')


@admin.register(ReaderProfile)
class ReaderProfileAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'is_active',
        'books_read',
        'reviews_written',
        'preferred_genres_count',
        'created_at',
        'updated_at',
    )
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
    )
    raw_id_fields = ('user',)
    filter_horizontal = ('preferred_genres',)
    readonly_fields = ('books_read', 'reviews_written', 'created_at', 'updated_at')
    list_select_related = ('user',)

    @admin.display(description='Любимых жанров')
    def preferred_genres_count(self, obj):
        return obj.preferred_genres.count()


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ('book', 'reader', 'page_number', 'short_note', 'created_at')
    list_filter = ('created_at',)
    search_fields = (
        'book__title',
        'book__slug',
        'reader__user__username',
        'reader__user__email',
        'note',
    )
    raw_id_fields = ('reader', 'book')
    readonly_fields = ('id', 'created_at')
    date_hierarchy = 'created_at'
    list_select_related = ('book', 'reader__user')

    @admin.display(description='Заметка')
    def short_note(self, obj):
        note = obj.note.strip()
        if not note:
            return '—'
        return note[:80] + '...' if len(note) > 80 else note


@admin.register(ReadingHistory)
class ReadingHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'book',
        'reader',
        'current_page_display',
        'progress_percentage',
        'is_completed',
        'started_at',
        'updated_at',
        'finished_at',
    )
    list_filter = ('is_completed', 'started_at', 'updated_at', 'finished_at')
    search_fields = (
        'book__title',
        'book__slug',
        'reader__user__username',
        'reader__user__email',
    )
    raw_id_fields = ('reader', 'book')
    readonly_fields = (
        'id',
        'last_page_read',
        'current_page_display',
        'progress_percentage',
        'is_completed',
        'started_at',
        'updated_at',
        'finished_at',
    )
    date_hierarchy = 'started_at'
    list_select_related = ('book', 'reader__user')

    fieldsets = (
        (
            'Связи',
            {
                'fields': ('id', 'reader', 'book'),
            },
        ),
        (
            'Прогресс',
            {
                'fields': (
                    'last_page_read',
                    'current_page_display',
                    'progress_percentage',
                    'is_completed',
                ),
            },
        ),
        (
            'Время',
            {
                'fields': ('started_at', 'updated_at', 'finished_at'),
            },
        ),
    )

    @admin.display(description='Текущая страница')
    def current_page_display(self, obj):
        return obj.current_page


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = (
        'book',
        'reader',
        'rating',
        'is_verified_purchase',
        'helpful_count',
        'created_at',
        'updated_at',
    )
    list_filter = ('rating', 'is_verified_purchase', 'created_at', 'updated_at')
    search_fields = (
        'book__title',
        'book__slug',
        'reader__user__username',
        'reader__user__email',
        'text',
    )
    raw_id_fields = ('reader', 'book')
    readonly_fields = ('id', 'helpful_count', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'
    list_select_related = ('book', 'reader__user')
