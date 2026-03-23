from rest_framework.views import exception_handler
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.response import Response


def custom_exception_handler(exc, context):
    """
    Custom exception handler that provides login options on authentication failure.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Handle 401 Unauthorized responses
        if response.status_code == 401 and isinstance(exc, AuthenticationFailed):
            # Check if the detail contains login_required flag
            if isinstance(exc.detail, dict) and exc.detail.get('login_required'):
                response.data = {
                    'detail': str(exc.detail.get('detail', 'Authentication required')),
                    'login_required': True,
                    'login_options': [
                        {
                            'type': 'email',
                            'label': 'Login with Email',
                            'endpoint': '/api/token/',
                            'method': 'POST'
                        },
                        {
                            'type': 'telegram_qr',
                            'label': 'Login with Telegram QR Code',
                            'endpoint': '/api/qr-session/create/',
                            'method': 'POST'
                        }
                    ]
                }
        
        # Handle token blacklisted
        if response.status_code == 401 and 'blacklisted' in str(response.data):
            response.data = {
                'detail': 'Session expired. Please login again.',
                'login_required': True,
                'login_options': [
                    {
                        'type': 'email',
                        'label': 'Login with Email',
                        'endpoint': '/api/token/',
                        'method': 'POST'
                    },
                    {
                        'type': 'telegram_qr',
                        'label': 'Login with Telegram QR Code',
                        'endpoint': '/api/qr-session/create/',
                        'method': 'POST'
                    }
                ]
            }

    return response
