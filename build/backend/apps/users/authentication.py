from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings


class CookieJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        cookie_name = getattr(settings, 'AUTH_COOKIE_ACCESS', 'access_token')
        raw_token = request.COOKIES.get(cookie_name)

        if raw_token is None:
            try:
                return super().authenticate(request)
            except Exception:
                # Catch all exceptions to allow unauthenticated requests
                return None

        try:
            validated_token = self.get_validated_token(raw_token)
            user = self.get_user(validated_token)
            return (user, validated_token)
        except Exception:
            # Catch all exceptions to allow unauthenticated requests
            return None