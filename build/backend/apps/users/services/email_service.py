import resend
from django.conf import settings
from django.template.loader import render_to_string

resend.api_key = settings.RESEND_API_KEY


def send_verification_email(user):
    token = user.generate_verification_token()
    verification_url = f"{settings.FRONTEND_URL}/verify-email/confirm?token={token}"
    
    context = {
        'first_name': user.first_name,
        'verification_url': verification_url,
    }
    
    html_content = render_to_string('emails/verification_email.html', context)
    text_content = render_to_string('emails/verification_email.txt', context)
    
    try:
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [user.email],
            "subject": "Verify your xgGaffer account",
            "html": html_content,
            "text": text_content,
        })
        return True
    except Exception as e:
        print(f"Failed to send verification email to {user.email}: {e}")
        return False


def send_password_reset_email(user, reset_token):
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    
    context = {
        'first_name': user.first_name,
        'reset_url': reset_url,
    }
    
    html_content = render_to_string('emails/password_reset_email.html', context)
    text_content = render_to_string('emails/password_reset_email.txt', context)
    
    try:
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [user.email],
            "subject": "Reset your xgGaffer password",
            "html": html_content,
            "text": text_content,
        })
        return True
    except Exception as e:
        print(f"Failed to send password reset email to {user.email}: {e}")
        return False