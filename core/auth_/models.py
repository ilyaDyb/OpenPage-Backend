from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_author = models.BooleanField(
        default=False,
        verbose_name='Статус автора',
        help_text='Отметьте, если пользователь может публиковать книги'
    )
    
    email_confirmed = models.BooleanField(
        default=False,
        verbose_name='Подтвержденный email',
    )

    telegram_confirmed = models.BooleanField(
        default=False,
        verbose_name='Подтвержденный Telegram',
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username