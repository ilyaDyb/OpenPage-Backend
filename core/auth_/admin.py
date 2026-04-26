from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from core.auth_.models import QRAuthRequest


User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'is_author',
        'email_confirmed',
        'telegram_confirmed',
        'is_staff',
        'is_active',
        'date_joined',
    )
    list_filter = (
        'role',
        'is_author',
        'email_confirmed',
        'telegram_confirmed',
        'is_staff',
        'is_superuser',
        'is_active',
        'groups',
    )
    search_fields = (
        'username',
        'email',
        'first_name',
        'last_name',
        'telegram_id',
    )
    ordering = ('username',)
    readonly_fields = ('last_login', 'date_joined')

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Роли и статусы',
            {
                'fields': ('role', 'is_author'),
            },
        ),
        (
            'Подтверждения и Telegram',
            {
                'fields': ('email_confirmed', 'telegram_confirmed', 'telegram_id'),
            },
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            'Дополнительно',
            {
                'classes': ('wide',),
                'fields': (
                    'email',
                    'first_name',
                    'last_name',
                    'role',
                    'is_author',
                    'email_confirmed',
                    'telegram_confirmed',
                    'telegram_id',
                ),
            },
        ),
    )


@admin.register(QRAuthRequest)
class QRAuthRequestAdmin(admin.ModelAdmin):
    list_display = (
        'token',
        'status',
        'user',
        'telegram_username',
        'telegram_id',
        'created_at',
        'expires_at',
        'confirmed_at',
        'is_expired_display',
    )
    list_filter = ('status', 'created_at', 'expires_at', 'confirmed_at')
    search_fields = (
        'token',
        'telegram_username',
        'telegram_id',
        'user__username',
        'user__email',
    )
    raw_id_fields = ('user',)
    readonly_fields = ('token', 'created_at', 'confirmed_at', 'qr_code_image_preview')
    date_hierarchy = 'created_at'

    fieldsets = (
        (
            'Основное',
            {
                'fields': ('token', 'status', 'user'),
            },
        ),
        (
            'Telegram',
            {
                'fields': ('telegram_id', 'telegram_username'),
            },
        ),
        (
            'Сроки',
            {
                'fields': ('created_at', 'expires_at', 'confirmed_at'),
            },
        ),
        (
            'QR-код',
            {
                'fields': ('qr_code_image', 'qr_code_image_preview'),
            },
        ),
    )

    @admin.display(boolean=True, description='Истёк')
    def is_expired_display(self, obj):
        return obj.is_expired()

    @admin.display(description='Превью QR-кода')
    def qr_code_image_preview(self, obj):
        if not obj.qr_code_image:
            return 'Нет изображения'
        return format_html(
            '<img src="{}" alt="QR Code" style="max-height: 240px; max-width: 240px;" />',
            obj.qr_code_image.url,
        )
