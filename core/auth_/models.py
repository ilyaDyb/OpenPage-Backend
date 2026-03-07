from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    is_author = models.BooleanField(
        default=False,
        verbose_name='Статус автора',
        help_text='Отметьте, если пользователь может публиковать книги'
    )
    # Можно добавить общие поля (например, телефон), если понадобятся

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.username