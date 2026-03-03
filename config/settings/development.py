"""Development settings."""
from .base import *

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '*']

# Use SQLite for development (easier setup)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Email - usa le impostazioni da .env (Aruba SMTP), o fallback a console
# Per testare email reali, commenta la riga sotto
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Debug toolbar (optional)
# INSTALLED_APPS += ['debug_toolbar']
# MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware']
# INTERNAL_IPS = ['127.0.0.1']

# Stripe Test Keys
STRIPE_PUBLIC_KEY = env('STRIPE_PUBLIC_KEY', default='pk_test_...')
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='sk_test_...')

# Disable WhiteNoise compression in development
STORAGES = {
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
    },
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
}
