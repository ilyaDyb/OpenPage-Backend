import os
from django.http import JsonResponse
from django.conf import settings

class SecretKeyMiddleware:
    """
    Проверяет наличие и совпадение заголовка X-Secret-Key.
    Исключённые пути задаются в SECRET_KEY_EXEMPT_PATHS.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        exempt_paths = getattr(settings, 'SECRET_KEY_EXEMPT_PATHS', [
            '/admin/',
            '/static/',
            '/media/',
            '/redoc/',
            '/api/docs/',
            '/api/schema/',
        ])

        if settings.DEBUG:
            return self.get_response(request)
        
        path = request.path_info
        for exempt in exempt_paths:
            if path.startswith(exempt):
                return self.get_response(request)

        expected_key = os.environ.get('API_SECRET_KEY')
        if not expected_key:
            # В production это критично, в dev можно вернуть 500
            return JsonResponse({'error': 'API secret key not configured'}, status=500)

        provided_key = request.headers.get('X-Secret-Key')
        if not provided_key or provided_key != expected_key:
            return JsonResponse({'error': 'Invalid or missing API secret key'}, status=403)

        return self.get_response(request)