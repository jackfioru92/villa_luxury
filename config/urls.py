"""
URL configuration for villa_luxury project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.conf.urls.static import static

# Allauth requires these URL names without namespace
from apps.accounts.views import CustomConfirmEmailView, EmailVerificationSentView
from apps.booking.calendar_views import calendar_feed

# URL SENZA prefisso di lingua.
# Qui vanno gli endpoint chiamati da sistemi esterni (o con redirect_uri
# registrato altrove), che devono avere un indirizzo stabile e identico
# in tutte le lingue.
urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Feed iCal disponibilità (Booking.com, Airbnb, ...) - l'URL deve finire con .ics
    # e resta identico in ogni lingua: è già pubblicato sui portali.
    path('calendario/<slug:unit_slug>/<str:token>.ics', calendar_feed, name='calendar_feed'),

    # Social login (allauth): il redirect_uri di Google è registrato sulla
    # Google Cloud Console, quindi non può cambiare con la lingua.
    path('accounts/', include('allauth.urls')),
]

# URL CON prefisso di lingua.
# prefix_default_language=False: l'italiano resta sugli indirizzi attuali
# (/, /villa/, /prenota/...), l'inglese vive sotto /en/.
urlpatterns += i18n_patterns(
    # Cambio lingua (view set_language di Django).
    # Deve stare DENTRO i18n_patterns: set_language usa translate_url(), che
    # risolve la URL di partenza nella lingua attiva durante la richiesta.
    # Sulle URL senza prefisso Django forza sempre LANGUAGE_CODE, quindi da
    # una pagina inglese il form deve postare su /en/i18n/setlang/ perche'
    # il ritorno all'italiano riesca a tradurre l'indirizzo.
    path('i18n/', include('django.conf.urls.i18n')),

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

    # Admin dashboard
    path('dashboard/', include('apps.dashboard.urls', namespace='dashboard')),

    # Override allauth email verification URLs (senza namespace, richiesto da
    # allauth internamente). Devono stare DOPO allauth.urls per fare override
    # del reverse(). Qui dentro il link di verifica nasce nella lingua in cui
    # l'utente si è registrato, e la pagina di conferma gli risponde nella sua
    # lingua; i link già inviati restano validi perché l'italiano non ha prefisso.
    path('account/email/verify/<key>/', CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    path('account/email/verify/', EmailVerificationSentView.as_view(), name='account_email_verification_sent'),

    prefix_default_language=False,
)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Customize admin
admin.site.site_header = 'Villa Luxury Admin'
admin.site.site_title = 'Villa Luxury'
admin.site.index_title = 'Gestione Villa'
