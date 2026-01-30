from django.db import models
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from apps.core.models import UUIDModel, TimeStampedModel


class Villa(UUIDModel, TimeStampedModel):
    """Main villa model."""
    name = models.CharField(_('Nome'), max_length=200)
    slug = models.SlugField(_('Slug'), unique=True)
    tagline = models.CharField(_('Tagline'), max_length=300, blank=True)
    description = models.TextField(_('Descrizione'))
    description_short = models.TextField(_('Descrizione breve'), max_length=500, blank=True)
    
    # Location
    address = models.TextField(_('Indirizzo'))
    city = models.CharField(_('Città'), max_length=100)
    province = models.CharField(_('Provincia'), max_length=100)
    postal_code = models.CharField(_('CAP'), max_length=10)
    country = models.CharField(_('Paese'), max_length=100, default='Italia')
    latitude = models.DecimalField(_('Latitudine'), max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(_('Longitudine'), max_digits=9, decimal_places=6, null=True, blank=True)
    
    # Features
    total_guests = models.PositiveIntegerField(_('Ospiti totali'), default=10)
    total_bedrooms = models.PositiveIntegerField(_('Camere totali'), default=5)
    total_bathrooms = models.PositiveIntegerField(_('Bagni totali'), default=5)
    total_sqm = models.PositiveIntegerField(_('Metri quadri'), null=True, blank=True)
    
    # Media
    hero_image = models.ImageField(_('Immagine hero'), upload_to='villa/hero/', null=True, blank=True)
    hero_video_url = models.URLField(_('URL video hero'), blank=True)
    
    # SEO
    meta_title = models.CharField(_('Meta title'), max_length=70, blank=True)
    meta_description = models.CharField(_('Meta description'), max_length=160, blank=True)
    
    is_active = models.BooleanField(_('Attiva'), default=True)

    class Meta:
        verbose_name = _('Villa')
        verbose_name_plural = _('Ville')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('villa:detail', kwargs={'slug': self.slug})


class BookableUnit(UUIDModel, TimeStampedModel):
    """Bookable unit within a villa (full villa, apartment, room)."""
    
    class UnitType(models.TextChoices):
        FULL_VILLA = 'FULL', _('Intera Villa')
        APARTMENT = 'APT', _('Appartamento')
        ROOM = 'ROOM', _('Camera')
    
    villa = models.ForeignKey(
        Villa,
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name=_('Villa')
    )
    name = models.CharField(_('Nome'), max_length=200)
    slug = models.SlugField(_('Slug'))
    unit_type = models.CharField(
        _('Tipo'),
        max_length=10,
        choices=UnitType.choices,
        default=UnitType.FULL_VILLA
    )
    description = models.TextField(_('Descrizione'))
    description_short = models.TextField(_('Descrizione breve'), max_length=300, blank=True)
    
    # Capacity
    max_guests = models.PositiveIntegerField(_('Ospiti max'), default=2)
    bedrooms = models.PositiveIntegerField(_('Camere'), default=1)
    bathrooms = models.PositiveIntegerField(_('Bagni'), default=1)
    beds_description = models.CharField(_('Descrizione letti'), max_length=200, blank=True)
    
    # Pricing
    base_price = models.DecimalField(
        _('Prezzo base/notte'),
        max_digits=10,
        decimal_places=2,
        help_text=_('Prezzo per notte in bassa stagione')
    )
    cleaning_fee = models.DecimalField(
        _('Costo pulizie'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    
    # Booking rules
    min_nights = models.PositiveIntegerField(_('Notti minime'), default=2)
    max_nights = models.PositiveIntegerField(_('Notti massime'), default=30)
    
    # Media
    main_image = models.ImageField(_('Immagine principale'), upload_to='villa/units/', null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(_('Attivo'), default=True)
    sort_order = models.PositiveIntegerField(_('Ordine'), default=0)

    class Meta:
        verbose_name = _('Unità prenotabile')
        verbose_name_plural = _('Unità prenotabili')
        ordering = ['sort_order', 'name']
        unique_together = ['villa', 'slug']

    def __str__(self):
        return f"{self.villa.name} - {self.name}"

    def get_absolute_url(self):
        return reverse('villa:unit_detail', kwargs={
            'villa_slug': self.villa.slug,
            'unit_slug': self.slug
        })

    def get_price_for_date(self, date):
        """Get the price for a specific date (considering seasons)."""
        season_price = self.season_prices.filter(
            start_date__lte=date,
            end_date__gte=date
        ).first()
        
        if season_price:
            return season_price.price_per_night
        return self.base_price


class SeasonPrice(UUIDModel):
    """Seasonal pricing for a bookable unit."""
    unit = models.ForeignKey(
        BookableUnit,
        on_delete=models.CASCADE,
        related_name='season_prices',
        verbose_name=_('Unità')
    )
    name = models.CharField(_('Nome stagione'), max_length=100)
    start_date = models.DateField(_('Data inizio'))
    end_date = models.DateField(_('Data fine'))
    price_per_night = models.DecimalField(
        _('Prezzo/notte'),
        max_digits=10,
        decimal_places=2
    )
    min_nights = models.PositiveIntegerField(
        _('Notti minime'),
        null=True,
        blank=True,
        help_text=_('Sovrascrive il minimo dell\'unità per questa stagione')
    )

    class Meta:
        verbose_name = _('Prezzo stagionale')
        verbose_name_plural = _('Prezzi stagionali')
        ordering = ['start_date']

    def __str__(self):
        return f"{self.unit.name} - {self.name}"


class Amenity(UUIDModel):
    """Amenities/features that can be assigned to villas or units."""
    
    class Category(models.TextChoices):
        COMFORT = 'COMFORT', _('Comfort')
        OUTDOOR = 'OUTDOOR', _('Esterni')
        KITCHEN = 'KITCHEN', _('Cucina')
        SERVICES = 'SERVICES', _('Servizi')
        ENTERTAINMENT = 'ENTERTAINMENT', _('Intrattenimento')
        SAFETY = 'SAFETY', _('Sicurezza')
    
    name = models.CharField(_('Nome'), max_length=100)
    icon = models.CharField(_('Icona'), max_length=50, blank=True, help_text=_('Classe icona (es: heroicons)'))
    category = models.CharField(
        _('Categoria'),
        max_length=20,
        choices=Category.choices,
        default=Category.COMFORT
    )
    is_highlighted = models.BooleanField(_('In evidenza'), default=False)

    class Meta:
        verbose_name = _('Amenity')
        verbose_name_plural = _('Amenities')
        ordering = ['category', 'name']

    def __str__(self):
        return self.name


class VillaAmenity(models.Model):
    """Many-to-many through model for villa amenities."""
    villa = models.ForeignKey(Villa, on_delete=models.CASCADE, related_name='villa_amenities')
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)
    description = models.CharField(_('Descrizione'), max_length=200, blank=True)

    class Meta:
        verbose_name = _('Amenity villa')
        verbose_name_plural = _('Amenities villa')
        unique_together = ['villa', 'amenity']


class UnitAmenity(models.Model):
    """Many-to-many through model for unit amenities."""
    unit = models.ForeignKey(BookableUnit, on_delete=models.CASCADE, related_name='unit_amenities')
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)
    description = models.CharField(_('Descrizione'), max_length=200, blank=True)

    class Meta:
        verbose_name = _('Amenity unità')
        verbose_name_plural = _('Amenities unità')
        unique_together = ['unit', 'amenity']


class GalleryImage(UUIDModel, TimeStampedModel):
    """Gallery images for villas and units."""
    villa = models.ForeignKey(
        Villa,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        null=True,
        blank=True,
        verbose_name=_('Villa')
    )
    unit = models.ForeignKey(
        BookableUnit,
        on_delete=models.CASCADE,
        related_name='gallery_images',
        null=True,
        blank=True,
        verbose_name=_('Unità')
    )
    image = models.ImageField(_('Immagine'), upload_to='gallery/')
    alt_text = models.CharField(_('Alt text'), max_length=200, blank=True)
    caption = models.CharField(_('Didascalia'), max_length=300, blank=True)
    is_hero = models.BooleanField(_('Immagine hero'), default=False)
    sort_order = models.PositiveIntegerField(_('Ordine'), default=0)

    class Meta:
        verbose_name = _('Immagine galleria')
        verbose_name_plural = _('Immagini galleria')
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.alt_text or f"Image {self.pk}"
