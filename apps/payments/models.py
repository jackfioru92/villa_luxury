from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import UUIDModel, TimeStampedModel
from apps.booking.models import Booking


class Payment(UUIDModel, TimeStampedModel):
    """Payment record linked to Stripe."""
    
    class PaymentType(models.TextChoices):
        DEPOSIT = 'DEPOSIT', _('Acconto')
        BALANCE = 'BALANCE', _('Saldo')
        FULL = 'FULL', _('Pagamento completo')
        REFUND = 'REFUND', _('Rimborso')
    
    class Status(models.TextChoices):
        PENDING = 'PENDING', _('In attesa')
        PROCESSING = 'PROCESSING', _('In elaborazione')
        COMPLETED = 'COMPLETED', _('Completato')
        FAILED = 'FAILED', _('Fallito')
        REFUNDED = 'REFUNDED', _('Rimborsato')
        CANCELLED = 'CANCELLED', _('Cancellato')
    
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Prenotazione')
    )
    amount = models.DecimalField(
        _('Importo'),
        max_digits=10,
        decimal_places=2
    )
    currency = models.CharField(_('Valuta'), max_length=3, default='EUR')
    payment_type = models.CharField(
        _('Tipo'),
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.DEPOSIT
    )
    status = models.CharField(
        _('Stato'),
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )
    
    # Stripe fields
    stripe_checkout_session_id = models.CharField(
        _('Stripe Checkout Session ID'),
        max_length=200,
        blank=True,
        db_index=True
    )
    stripe_payment_intent_id = models.CharField(
        _('Stripe Payment Intent ID'),
        max_length=200,
        blank=True,
        db_index=True
    )
    stripe_charge_id = models.CharField(
        _('Stripe Charge ID'),
        max_length=200,
        blank=True
    )
    
    # Metadata
    customer_email = models.EmailField(_('Email cliente'), blank=True)
    receipt_url = models.URLField(_('URL ricevuta'), blank=True)
    
    # Timestamps
    completed_at = models.DateTimeField(_('Completato il'), null=True, blank=True)
    failed_at = models.DateTimeField(_('Fallito il'), null=True, blank=True)
    failure_reason = models.TextField(_('Motivo fallimento'), blank=True)

    class Meta:
        verbose_name = _('Pagamento')
        verbose_name_plural = _('Pagamenti')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.booking.booking_number} - €{self.amount} ({self.get_status_display()})"


class PaymentLog(UUIDModel):
    """Log of all Stripe webhook events for auditing."""
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='logs',
        null=True,
        blank=True,
        verbose_name=_('Pagamento')
    )
    event_id = models.CharField(
        _('Stripe Event ID'),
        max_length=200,
        unique=True,
        db_index=True
    )
    event_type = models.CharField(_('Tipo evento'), max_length=100)
    event_data = models.JSONField(_('Dati evento'))
    processed = models.BooleanField(_('Processato'), default=False)
    processed_at = models.DateTimeField(_('Processato il'), null=True, blank=True)
    error_message = models.TextField(_('Errore'), blank=True)
    created_at = models.DateTimeField(_('Ricevuto il'), auto_now_add=True)

    class Meta:
        verbose_name = _('Log pagamento')
        verbose_name_plural = _('Log pagamenti')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.event_type} - {self.event_id}"
