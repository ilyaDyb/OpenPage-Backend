"""
Custom JWT Authentication
"""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication with proper error handling.
    Returns 401 with login options when token is invalid/expired.
    """
    
    def authenticate(self, request):
        """
        Custom authentication that handles automatic logout on token expiration.
        Returns 401 with login options when token is invalid/expired.
        """
        try:
            return super().authenticate(request)
        except AuthenticationFailed as e:
            # Re-raise authentication failures to trigger 401 response
            raise e
        except TokenError as e:
            # Token expired or invalid - suggest re-authentication
            raise AuthenticationFailed(
                {"detail": str(e), "login_required": True}
            )
