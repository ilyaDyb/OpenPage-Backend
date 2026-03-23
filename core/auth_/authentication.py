from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework.exceptions import AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that handles automatic logout on token expiration.
    Returns 401 with login options when token is invalid/expired.
    """
    
    def get_validated_token(self, raw_token):
        token = super().get_validated_token(raw_token)
        jti = token['jti']
        if BlacklistedToken.objects.filter(token__jti=jti).exists():
            raise InvalidToken({"detail": "Token is blacklisted"})
        return token
    
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
