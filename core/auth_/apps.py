from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core.auth_'
    label = 'auth_'

    def ready(self):
        # Import OpenAPI extensions so drf-spectacular registers them at startup.
        from core.auth_ import openapi_extensions  # noqa: F401
