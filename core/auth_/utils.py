import random
import uuid
import redis
from django.conf import settings
from django.core.mail import send_mail

redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True
)

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
    redis_client.hset(key, mapping=data)
    redis_client.expire(key, ttl)

def get_registration_data(email):
    """Получает данные регистрации по email"""
    key = f'reg:{email}'
    data = redis_client.hgetall(key)
    return data if data else None

def delete_registration_data(email):
    """Удаляет данные регистрации"""
    key = f'reg:{email}'
    redis_client.delete(key)