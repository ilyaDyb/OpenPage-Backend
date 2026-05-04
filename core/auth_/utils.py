import random
import uuid
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail

def generate_verification_code():
    """Генерирует 6-значный код"""
    return str(random.randint(100000, 999999))

def send_verification_email(email, code):
    """Отправляет код на email"""
    subject = 'Подтверждение email'
    message = f'Ваш код подтверждения: {code}'
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])

def store_registration_data(email, user_data, code, ttl=300):
    """Сохраняет данные регистрации и код в Redis на 5 минут"""
    key = f'reg:{email}'
    data = user_data.copy()
    data['code'] = code
    cache.set(key, data, ttl)

def get_registration_data(email):
    """Получает данные регистрации по email"""
    key = f'reg:{email}'
    return cache.get(key)

def delete_registration_data(email):
    """Удаляет данные регистрации"""
    key = f'reg:{email}'
    cache.delete(key)
