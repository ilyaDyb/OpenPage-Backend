import socket
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from rest_framework_simplejwt.exceptions import AuthenticationFailed

from core.utils import exception_handler


User = get_user_model()

@exception_handler
def validate_user_login_data(username_or_email: str, password: str):
    if not username_or_email or not password:
        raise AuthenticationFailed("Username or email and password are required", code=400)

    if "@" in username_or_email:
        user = User.objects.filter(email=username_or_email).first()
        field = "email"
    else:
        user = User.objects.filter(username=username_or_email).first()
        field = "username"

    if user is None:
        raise AuthenticationFailed(f"User with such {field} does not exist", code=400)

    if not user.check_password(password):
        raise AuthenticationFailed("Incorrect password", code=400)

    return user

def is_valid_email_format(email):
    try:
        validate_email(email)
        return True
    except ValidationError:
        return False


def email_domain_exists(email):
    try:
        domain = email.rsplit("@", 1)[1].strip().lower()
    except IndexError:
        return False

    if not domain:
        return False

    try:
        ascii_domain = domain.encode("idna").decode("ascii")
        socket.getaddrinfo(ascii_domain, None)
    except (UnicodeError, socket.gaierror, OSError):
        return False

    return True
