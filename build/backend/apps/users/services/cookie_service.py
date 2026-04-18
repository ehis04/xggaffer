from django.conf import settings

def get_cookie_config():
    return {
        'access_name': getattr(settings, 'AUTH_COOKIE_ACCESS', 'access_token'),
        'refresh_name': getattr(settings, 'AUTH_COOKIE_REFRESH', 'refresh_token'),
        'secure': getattr(settings, 'AUTH_COOKIE_SECURE', False),
        'httponly': getattr(settings, 'AUTH_COOKIE_HTTP_ONLY', True),
        'path': getattr(settings, 'AUTH_COOKIE_PATH', '/'),
        'samesite': getattr(settings, 'AUTH_COOKIE_SAMESITE', 'Lax'),
        'access_max_age': getattr(settings, 'AUTH_COOKIE_ACCESS_MAX_AGE', 60 * 15),
        'refresh_max_age': getattr(settings, 'AUTH_COOKIE_REFRESH_MAX_AGE', 60 * 60 * 24 * 7),
        'refresh_max_age_session': getattr(settings, 'AUTH_COOKIE_REFRESH_MAX_AGE_SESSION', None),
    }

def set_auth_cookies(response, access_token, refresh_token, remember_me=False):
    config = get_cookie_config()

    response.set_cookie(
        key=config['access_name'],
        value=access_token,
        max_age=config['access_max_age'],
        secure=config['secure'],
        httponly=config['httponly'],
        samesite=config['samesite'],
        path=config['path'],
    )

    refresh_max_age = (
        config['refresh_max_age'] if remember_me 
        else config['refresh_max_age_session']
    )
    
    response.set_cookie(
        key=config['refresh_name'],
        value=refresh_token,
        max_age=refresh_max_age,
        secure=config['secure'],
        httponly=config['httponly'],
        samesite=config['samesite'],
        path=config['path'],
    )
    
    return response

def clear_auth_cookies(response):
    config = get_cookie_config()

    response.set_cookie(
        key=config['access_name'],
        value='',
        max_age=0,
        secure=config['secure'],
        httponly=config['httponly'],
        samesite=config['samesite'],
        path=config['path'],
    )
    
    response.set_cookie(
        key=config['refresh_name'],
        value='',
        max_age=0,
        secure=config['secure'],
        httponly=config['httponly'],
        samesite=config['samesite'],
        path=config['path'],
    )
    
    return response

def get_access_token_from_cookie(request):
    config = get_cookie_config()
    return request.COOKIES.get(config['access_name'])


def get_refresh_token_from_cookie(request):
    config = get_cookie_config()
    return request.COOKIES.get(config['refresh_name'])