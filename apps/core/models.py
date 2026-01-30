from django.db import models
from django.utils.translation import gettext_lazy as _
import uuid


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""
    created_at = models.DateTimeField(_('Creato il'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Aggiornato il'), auto_now=True)

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """Abstract base model with UUID primary key."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class SiteSettings(models.Model):
    """Singleton model for site-wide settings."""
    site_name = models.CharField(_('Nome sito'), max_length=200, default='Villa Luxury')
    site_description = models.TextField(_('Descrizione sito'), blank=True)
    site_keywords = models.CharField(_('Keywords SEO'), max_length=500, blank=True)
    
    # Contact info
    email = models.EmailField(_('Email'), blank=True)
    phone = models.CharField(_('Telefono'), max_length=30, blank=True)
    whatsapp = models.CharField(_('WhatsApp'), max_length=30, blank=True)
    address = models.TextField(_('Indirizzo'), blank=True)
    
    # Social media
    facebook_url = models.URLField(_('Facebook'), blank=True)
    instagram_url = models.URLField(_('Instagram'), blank=True)
    
    # Booking settings
    check_in_time = models.TimeField(_('Orario check-in'), default='15:00')
    check_out_time = models.TimeField(_('Orario check-out'), default='10:00')
    
    # Legal
    privacy_policy = models.TextField(_('Privacy Policy'), blank=True)
    terms_conditions = models.TextField(_('Termini e Condizioni'), blank=True)
    
    class Meta:
        verbose_name = _('Impostazioni sito')
        verbose_name_plural = _('Impostazioni sito')

    def save(self, *args, **kwargs):
        """Ensure only one instance exists."""
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Prevent deletion."""
        pass

    @classmethod
    def get_settings(cls):
        """Get or create the singleton instance."""
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return self.site_name


class Page(UUIDModel, TimeStampedModel):
    """Custom static pages (es: Chi siamo, Servizi, etc.)."""
    title = models.CharField(_('Titolo'), max_length=200)
    slug = models.SlugField(_('Slug'), unique=True)
    content = models.TextField(_('Contenuto'))
    meta_description = models.CharField(_('Meta description'), max_length=160, blank=True)
    is_published = models.BooleanField(_('Pubblicata'), default=True)
    show_in_menu = models.BooleanField(_('Mostra nel menu'), default=False)
    menu_order = models.PositiveIntegerField(_('Ordine menu'), default=0)
    
    class Meta:
        verbose_name = _('Pagina')
        verbose_name_plural = _('Pagine')
        ordering = ['menu_order', 'title']

    def __str__(self):
        return self.title


class FAQ(UUIDModel, TimeStampedModel):
    """Frequently Asked Questions."""
    question = models.CharField(_('Domanda'), max_length=500)
    answer = models.TextField(_('Risposta'))
    order = models.PositiveIntegerField(_('Ordine'), default=0)
    is_active = models.BooleanField(_('Attiva'), default=True)
    
    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQ')
        ordering = ['order']

    def __str__(self):
        return self.question


class Testimonial(UUIDModel, TimeStampedModel):
    """Guest testimonials/reviews."""
    guest_name = models.CharField(_('Nome ospite'), max_length=200)
    guest_country = models.CharField(_('Paese'), max_length=100, blank=True)
    content = models.TextField(_('Testimonianza'))
    rating = models.PositiveSmallIntegerField(_('Valutazione'), default=5)
    stay_date = models.DateField(_('Data soggiorno'), null=True, blank=True)
    is_featured = models.BooleanField(_('In evidenza'), default=False)
    is_active = models.BooleanField(_('Attiva'), default=True)
    
    class Meta:
        verbose_name = _('Testimonianza')
        verbose_name_plural = _('Testimonianze')
        ordering = ['-is_featured', '-created_at']

    def __str__(self):
        return f"{self.guest_name} - {self.rating}★"
