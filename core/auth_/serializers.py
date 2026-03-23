from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from core.auth_.validators import is_valid_email_format

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_author')
        read_only_fields = ('id',)


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password]
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        label='Confirm password',
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'first_name', 'last_name')

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "User with this email already exists."})
        if not is_valid_email_format(attrs['email']):
            raise serializers.ValidationError({"email": "Email format is invalid"})

        return attrs

    def save(self, **kwargs):
        pass

class EmailVerifySerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)

class QRSessionRequestSerializer(serializers.Serializer):
    """Serializer for requesting a QR login session"""
    telegram_id = serializers.IntegerField(
        required=True,
        help_text="User's Telegram ID"
    )

class QRLoginConfirmSerializer(serializers.Serializer):
    """Serializer for confirming QR code login"""
    session_code = serializers.CharField(
        max_length=36,
        required=True,
        help_text="QR session code to verify"
    )

class TelegramLinkSerializer(serializers.Serializer):
    """Serializer for linking Telegram account to existing user"""
    telegram_id = serializers.IntegerField(required=True)
    username_or_email = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

class LoginChoiceSerializer(serializers.Serializer):
    """Serializer for login choice response"""
    message = serializers.CharField()
    options = serializers.ListField(child=serializers.DictField())

class QRAuthRequestSerializer(serializers.Serializer):
    """Serializer for creating QR auth request"""
    token = serializers.UUIDField(read_only=True)
    qr_link = serializers.CharField(read_only=True)
    qr_code_url = serializers.CharField(read_only=True, required=False)
    expires_in = serializers.IntegerField(read_only=True)
    
    class Meta:
        ref_name = 'QRAuthRequest'

class QRAuthStatusSerializer(serializers.Serializer):
    """Serializer for QR auth status response"""
    status = serializers.CharField()
    authenticated = serializers.BooleanField()
    access_token = serializers.CharField(allow_null=True, required=False)
    refresh_token = serializers.CharField(allow_null=True, required=False)
    user = UserSerializer(allow_null=True, required=False)
    message = serializers.CharField(required=False)
    
    class Meta:
        ref_name = 'QRAuthStatus'

class QRAuthConfirmSerializer(serializers.Serializer):
    """Serializer for backend QR auth confirmation from bot (internal use)"""
    token = serializers.UUIDField()
    telegram_id = serializers.IntegerField()
    telegram_username = serializers.CharField(max_length=255, allow_blank=True)
    
    class Meta:
        ref_name = 'QRAuthConfirm'

class QRAuthConfirmedSerializer(serializers.Serializer):
    """Serializer for final confirmation from bot (internal use)"""
    token = serializers.UUIDField()
    telegram_id = serializers.IntegerField()
    
    class Meta:
        ref_name = 'QRAuthConfirmed'

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['is_author'] = user.is_author
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user).data
        return data
