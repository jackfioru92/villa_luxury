from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import UUIDModel
import uuid


class CustomUserManager(BaseUserManager):
    """Custom user manager using email as username."""

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError(_('L\'email è obbligatoria'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser deve avere is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser deve avere is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Custom user model with email as username."""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_('Email'), unique=True)
    first_name = models.CharField(_('Nome'), max_length=150, blank=True)
    last_name = models.CharField(_('Cognome'), max_length=150, blank=True)
    phone = models.CharField(_('Telefono'), max_length=30, blank=True)
    country = models.CharField(_('Paese'), max_length=100, blank=True)
    
    # Status
    is_active = models.BooleanField(_('Attivo'), default=True)
    is_staff = models.BooleanField(_('Staff'), default=False)
    
    # Timestamps
    date_joined = models.DateTimeField(_('Data registrazione'), default=timezone.now)
    last_login = models.DateTimeField(_('Ultimo accesso'), null=True, blank=True)
    
    # Email verification
    email_verified = models.BooleanField(_('Email verificata'), default=False)
    email_verified_at = models.DateTimeField(_('Email verificata il'), null=True, blank=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _('Utente')
        verbose_name_plural = _('Utenti')

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return first_name plus last_name, with a space in between."""
        full_name = f'{self.first_name} {self.last_name}'.strip()
        return full_name or self.email

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name or self.email.split('@')[0]

    @property
    def full_name(self):
        return self.get_full_name()

    def get_bookings(self):
        """Get all bookings for this user."""
        from apps.booking.models import Booking
        return Booking.objects.filter(
            models.Q(user=self) | models.Q(guest_email=self.email)
        ).order_by('-created_at')
