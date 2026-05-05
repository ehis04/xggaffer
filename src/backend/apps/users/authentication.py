from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings

#JWT authentication class that checks for an access token in cookies before falling back to the default header-based JWT authentication
class CookieJWTAuthentication(JWTAuthentication):
    # authenticates the request by reading the JWT token from the configured auth cookie
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