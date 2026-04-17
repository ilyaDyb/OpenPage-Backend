from rest_framework.response import Response


def build_error_payload(error_type, detail, status_code, errors=None, extra=None):
    payload = {
        'type': error_type,
        'detail': detail,
        'status_code': status_code,
    }

    if errors:
        payload['errors'] = errors

    if extra:
        payload.update(extra)

    return payload


def error_response(error_type, detail, status_code, errors=None, extra=None):
    return Response(
        build_error_payload(
            error_type=error_type,
            detail=detail,
            status_code=status_code,
            errors=errors,
            extra=extra,
        ),
        status=status_code,
    )
