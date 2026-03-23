"""
OpenAPI extensions for custom authentication
"""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema


class CustomJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    OpenAPI schema extension for CustomJWTAuthentication
    Maps to 'Bearer' authentication in Swagger UI
    """
    target_class = 'core.auth_.authentication.CustomJWTAuthentication'
    name = 'Bearer'
    match_subclasses = True
    
    def get_security_definition(self, auto_schema: AutoSchema) -> dict:
        return {
            'type': 'http',
            'scheme': 'bearer',
            'bearerFormat': 'JWT',
            'in': 'header',
            'name': 'Authorization',
            'description': 'Enter your JWT access token in the format: `Bearer {token}`'
        }
