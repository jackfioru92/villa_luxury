from django.conf import settings


def site_settings(request):
    """Add site settings to all templates."""
    from apps.core.models import SiteSettings
    
    try:
        settings_obj = SiteSettings.get_settings()
    except Exception:
        settings_obj = None
    
    return {
        'site_settings': settings_obj,
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Villa Luxury'),
        'STRIPE_PUBLIC_KEY': getattr(settings, 'STRIPE_PUBLIC_KEY', ''),
    }
