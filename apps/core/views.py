from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, DetailView
from django.core.mail import send_mail
from django.contrib import messages
from django.conf import settings
from apps.villa.models import Villa, BookableUnit
from apps.core.models import Page, FAQ, Testimonial, SiteSettings


class HomeView(TemplateView):
    """Home page view."""
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['villa'] = Villa.objects.filter(is_active=True).first()
        context['units'] = BookableUnit.objects.filter(is_active=True).order_by('sort_order')
        context['testimonials'] = Testimonial.objects.filter(is_active=True, is_featured=True)[:3]
        context['faqs'] = FAQ.objects.filter(is_active=True)[:5]
        return context


class PageDetailView(DetailView):
    """Generic page detail view."""
    model = Page
    template_name = 'core/page_detail.html'
    context_object_name = 'page'

    def get_queryset(self):
        return Page.objects.filter(is_published=True)


class ContactView(TemplateView):
    """Contact page view."""
    template_name = 'core/contact.html'

    def post(self, request, *args, **kwargs):
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        if not all([name, email, subject, message_text]):
            messages.error(request, 'Per favore compila tutti i campi obbligatori.')
            return self.get(request, *args, **kwargs)

        subject_map = {
            'info': 'Informazioni generali',
            'booking': 'Prenotazione',
            'availability': 'Disponibilità',
            'special': 'Richieste speciali',
            'other': 'Altro',
        }
        subject_label = subject_map.get(subject, subject)

        body = (
            f"Nuovo messaggio dal sito {settings.SITE_NAME}\n"
            f"{'=' * 40}\n\n"
            f"Nome: {name}\n"
            f"Email: {email}\n"
            f"Telefono: {phone or 'Non specificato'}\n"
            f"Argomento: {subject_label}\n\n"
            f"Messaggio:\n{message_text}\n"
        )

        try:
            site_settings_obj = SiteSettings.get_settings()
            recipient = site_settings_obj.email or getattr(settings, 'CONTACT_EMAIL', settings.DEFAULT_FROM_EMAIL)
        except Exception:
            recipient = getattr(settings, 'CONTACT_EMAIL', settings.DEFAULT_FROM_EMAIL)

        try:
            send_mail(
                subject=f'[{settings.SITE_NAME}] Contatto: {subject_label}',
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            messages.success(request, 'Messaggio inviato con successo! Ti risponderemo al più presto.')
        except Exception:
            messages.error(request, 'Si è verificato un errore nell\'invio del messaggio. Riprova più tardi.')

        return redirect('core:contact')


class PrivacyView(TemplateView):
    """Privacy policy page."""
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    """Terms and conditions page."""
    template_name = 'core/terms.html'


class MaintenanceView(TemplateView):
    """Maintenance page view."""
    template_name = 'maintenance.html'
