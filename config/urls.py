"""
URL configuration for villa_luxury project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# Allauth requires these URL names without namespace
from apps.accounts.views import CustomConfirmEmailView, EmailVerificationSentView

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    
    # Core pages (home, contact, etc.)
    path('', include('apps.core.urls', namespace='core')),
    
    # Villa and units
    path('villa/', include('apps.villa.urls', namespace='villa')),
    
    # Booking system
    path('prenota/', include('apps.booking.urls', namespace='booking')),
    
    # Payments
    path('payment/', include('apps.payments.urls', namespace='payments')),
    
    # User accounts
    path('account/', include('apps.accounts.urls', namespace='accounts')),
    # Social login (allauth) - PRIMA delle override per url resolution
    path('accounts/', include('allauth.urls')),
    
    # Override allauth email verification URLs (senza namespace, richiesto da allauth internamente)
    # Devono essere DOPO allauth.urls per fare override del reverse()
    path('account/email/verify/<key>/', CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    path('account/email/verify/', EmailVerificationSentView.as_view(), name='account_email_verification_sent'),
    
    # Admin dashboard
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin
admin.site.site_header = 'Villa Luxury Admin'
admin.site.site_title = 'Villa Luxury'
admin.site.index_title = 'Gestione Villa'
