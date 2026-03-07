from django.contrib.auth import get_user_model

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