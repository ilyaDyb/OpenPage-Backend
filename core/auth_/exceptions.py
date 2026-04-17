from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated, NotFound, PermissionDenied, ValidationError
from rest_framework.views import exception_handler

from core.api_errors import build_error_payload


LOGIN_OPTIONS = [
    {
        'type': 'email',
        'label': 'Login with Email',
        'endpoint': '/api/token/',
        'method': 'POST',
    },
    {
        'type': 'telegram_qr',
        'label': 'Login with Telegram QR Code',
        'endpoint': '/api/qr-auth/create/',
        'method': 'POST',
    },
]


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return response

    if isinstance(exc, ValidationError):
        errors = normalize_validation_errors(response.data)
        response.data = build_error_payload(
            error_type='validation_error',
            detail='Validation failed.',
            status_code=response.status_code,
            errors=errors,
        )
        return response

    if isinstance(exc, (AuthenticationFailed, NotAuthenticated)) or response.status_code == 401:
        detail = extract_detail(response.data, default='Authentication required.')
        extra = {}

        if isinstance(exc, AuthenticationFailed) and isinstance(exc.detail, dict) and exc.detail.get('login_required'):
            extra = {
                'login_required': True,
                'login_options': LOGIN_OPTIONS,
            }
            detail = str(exc.detail.get('detail', detail))
        elif 'blacklisted' in str(response.data).lower():
            detail = 'Session expired. Please login again.'
            extra = {
                'login_required': True,
                'login_options': LOGIN_OPTIONS,
            }

        response.data = build_error_payload(
            error_type='authentication_error',
            detail=detail,
            status_code=response.status_code,
            extra=extra,
        )
        return response

    if isinstance(exc, PermissionDenied) or response.status_code == 403:
        response.data = build_error_payload(
            error_type='permission_denied',
            detail=extract_detail(response.data, default='You do not have permission to perform this action.'),
            status_code=response.status_code,
        )
        return response

    if isinstance(exc, NotFound) or response.status_code == 404:
        response.data = build_error_payload(
            error_type='not_found',
            detail=extract_detail(response.data, default='Resource not found.'),
            status_code=response.status_code,
        )
        return response

    if response.status_code == 400:
        response.data = build_error_payload(
            error_type='bad_request',
            detail=extract_detail(response.data, default='Bad request.'),
            status_code=response.status_code,
            errors=normalize_validation_errors(response.data),
        )

    return response


def extract_detail(data, default):
    if isinstance(data, dict) and 'detail' in data:
        value = data['detail']
        if isinstance(value, list):
            return str(value[0])
        return str(value)

    if isinstance(data, list) and data:
        return str(data[0])

    if isinstance(data, str):
        return data

    return default


def normalize_validation_errors(data):
    if isinstance(data, dict):
        if 'detail' in data and len(data) == 1:
            return {'non_field_errors': ensure_list(data['detail'])}

        return {
            key: normalize_validation_errors(value)
            for key, value in data.items()
        }

    if isinstance(data, list):
        if all(not isinstance(item, (dict, list)) for item in data):
            return [str(item) for item in data]
        return [normalize_validation_errors(item) for item in data]

    return ensure_list(data)


def ensure_list(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]
