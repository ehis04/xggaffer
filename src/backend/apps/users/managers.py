from django.contrib.auth.models import BaseUserManager

# manages how normal users and superusers are created for the custom User model
class UserManager(BaseUserManager):
    # creates a normal user account using an email address and password
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        
        email = self.normalize_email(email.strip())
        
        if not email:
            raise ValueError('Users must have an email address')
        
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        
        from .models import UserProfile
        UserProfile.objects.create(user=user)
        
        return user
    # creates an admin user account and enforces the required staff and superuser flags
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)