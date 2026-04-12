from .settings import *  # noqa: F403,F401


DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # noqa: F405
    }
}

MIDDLEWARE = [
    middleware
    for middleware in MIDDLEWARE  # noqa: F405
    if middleware != 'core.auth_.middleware.SecretKeyMiddleware'
]

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
DEBUG_PROPAGATE_EXCEPTIONS = True
