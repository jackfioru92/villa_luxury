from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.utils import timezone
from apps.core.models import UUIDModel, TimeStampedModel
from apps.villa.models import BookableUnit
import uuid
from datetime import date


class Booking(UUIDModel, TimeStampedModel):
    """Main booking model."""
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('In attesa')
        CONFIRMED = 'CONFIRMED', _('Confermata')
        CANCELLED = 'CANCELLED', _('Cancellata')
        COMPLETED = 'COMPLETED', _('Completata')
        NO_SHOW = 'NO_SHOW', _('No show')
    
    class PaymentStatus(models.TextChoices):
        PENDING = 'PENDING', _('In attesa')
        DEPOSIT_PAID = 'DEPOSIT_PAID', _('Acconto pagato')
        FULLY_PAID = 'FULLY_PAID', _('Pagato totalmente')
        REFUNDED = 'REFUNDED', _('Rimborsato')
        PARTIALLY_REFUNDED = 'PARTIAL_REFUND', _('Parzialmente rimborsato')
    
    # Booking reference
    booking_number = models.CharField(
        _('Numero prenotazione'),
        max_length=20,
        unique=True,
        editable=False
    )
    
    # Unit booked
    unit = models.ForeignKey(
        BookableUnit,
        on_delete=models.PROTECT,
        related_name='bookings',
        verbose_name=_('Unità')
    )
    
    # User (optional - can be guest booking)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='bookings',
        verbose_name=_('Utente')
    )
    
    # Guest info (used when not logged in)
    guest_first_name = models.CharField(_('Nome'), max_length=100)
    guest_last_name = models.CharField(_('Cognome'), max_length=100)
    guest_email = models.EmailField(_('Email'))
    guest_phone = models.CharField(_('Telefono'), max_length=30)
    guest_country = models.CharField(_('Paese'), max_length=100, blank=True)
    
    # Dates
    check_in = models.DateField(_('Check-in'))
    check_out = models.DateField(_('Check-out'))
    num_guests = models.PositiveIntegerField(_('Numero ospiti'), default=1)
    
    # Pricing
    nights = models.PositiveIntegerField(_('Notti'), default=1)
    price_per_night_avg = models.DecimalField(
        _('Prezzo medio/notte'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    subtotal = models.DecimalField(
        _('Subtotale'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    cleaning_fee = models.DecimalField(
        _('Costo pulizie'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    total_amount = models.DecimalField(
        _('Totale'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    deposit_amount = models.DecimalField(
        _('Acconto'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    balance_due = models.DecimalField(
        _('Saldo dovuto'),
        max_digits=10,
        decimal_places=2,
        default=0
    )
    currency = models.CharField(_('Valuta'), max_length=3, default='EUR')
    
    # Status
    status = models.CharField(
        _('Stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    payment_status = models.CharField(
        _('Stato pagamento'),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )
    
    # Notes
    guest_notes = models.TextField(_('Note ospite'), blank=True)
    admin_notes = models.TextField(_('Note admin'), blank=True)
    
    # Special requests
    arrival_time = models.TimeField(_('Orario arrivo previsto'), null=True, blank=True)
    
    # Timestamps
    confirmed_at = models.DateTimeField(_('Confermata il'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Cancellata il'), null=True, blank=True)
    cancellation_reason = models.TextField(_('Motivo cancellazione'), blank=True)

    class Meta:
        verbose_name = _('Prenotazione')
        verbose_name_plural = _('Prenotazioni')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking_number} - {self.guest_full_name}"

    def save(self, *args, **kwargs):
        if not self.booking_number:
            self.booking_number = self.generate_booking_number()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_booking_number():
        """Generate unique booking number (VL-YYYY-XXXXX)."""
        year = timezone.now().year
        random_part = uuid.uuid4().hex[:5].upper()
        return f"VL-{year}-{random_part}"

    @property
    def guest_full_name(self):
        return f"{self.guest_first_name} {self.guest_last_name}"

    @property
    def is_upcoming(self):
        return self.check_in > date.today() and self.status == self.Status.CONFIRMED

    @property
    def is_current(self):
        today = date.today()
        return self.check_in <= today <= self.check_out and self.status == self.Status.CONFIRMED

    @property
    def is_past(self):
        return self.check_out < date.today()

    def confirm(self):
        """Confirm the booking and create blocked dates."""
        self.status = self.Status.CONFIRMED
        self.confirmed_at = timezone.now()
        self.save()
        self.create_blocked_dates()

    def cancel(self, reason=''):
        """Cancel the booking and remove blocked dates."""
        self.status = self.Status.CANCELLED
        self.cancelled_at = timezone.now()
        self.cancellation_reason = reason
        self.save()
        self.blocked_dates.all().delete()

    def create_blocked_dates(self):
        """Create BlockedDate entries for this booking."""
        from datetime import timedelta
        
        current_date = self.check_in
        while current_date < self.check_out:
            BlockedDate.objects.get_or_create(
                unit=self.unit,
                date=current_date,
                defaults={
                    'reason': BlockedDate.Reason.BOOKING,
                    'booking': self
                }
            )
            current_date += timedelta(days=1)


class BlockedDate(UUIDModel):
    """Blocked dates for a unit (bookings, maintenance, etc.)."""
    
    class Reason(models.TextChoices):
        BOOKING = 'BOOKING', _('Prenotazione')
        MAINTENANCE = 'MAINTENANCE', _('Manutenzione')
        OWNER = 'OWNER', _('Uso proprietario')
        OTHER = 'OTHER', _('Altro')
    
    unit = models.ForeignKey(
        BookableUnit,
        on_delete=models.CASCADE,
        related_name='blocked_dates',
        verbose_name=_('Unità')
    )
    date = models.DateField(_('Data'))
    reason = models.CharField(
        _('Motivo'),
        max_length=20,
        choices=Reason.choices,
        default=Reason.BOOKING
    )
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='blocked_dates',
        verbose_name=_('Prenotazione')
    )
    note = models.CharField(_('Nota'), max_length=200, blank=True)

    class Meta:
        verbose_name = _('Data bloccata')
        verbose_name_plural = _('Date bloccate')
        unique_together = ['unit', 'date']
        ordering = ['date']

    def __str__(self):
        return f"{self.unit.name} - {self.date}"


class BookingPriceDetail(UUIDModel):
    """Detailed price breakdown by night."""
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='price_details',
        verbose_name=_('Prenotazione')
    )
    date = models.DateField(_('Data'))
    price = models.DecimalField(_('Prezzo'), max_digits=10, decimal_places=2)
    season_name = models.CharField(_('Stagione'), max_length=100, blank=True)

    class Meta:
        verbose_name = _('Dettaglio prezzo')
        verbose_name_plural = _('Dettagli prezzo')
        ordering = ['date']

    def __str__(self):
        return f"{self.booking.booking_number} - {self.date}"
