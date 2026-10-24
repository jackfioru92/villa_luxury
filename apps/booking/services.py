"""
Booking services - Core business logic for availability and pricing.
"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Tuple
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.db.models import Q
from django.utils import translation
from django.utils.formats import date_format
from django.utils.translation import get_language, gettext as _
from apps.villa.models import BookableUnit, SeasonPrice
from apps.booking.models import BlockedDate, Booking, BookingPriceDetail


def send_new_booking_notification(booking: Booking):
    """
    Invia email di notifica all'admin quando viene creata una nuova prenotazione.
    """
    try:
        subject = f'[{settings.SITE_NAME}] Nuova prenotazione #{booking.booking_number}'
        
        message = (
            f"Nuova prenotazione ricevuta!\n"
            f"{'=' * 50}\n\n"
            f"Numero prenotazione: {booking.booking_number}\n"
            f"Ospite: {booking.guest_full_name}\n"
            f"Email: {booking.guest_email}\n"
            f"Telefono: {booking.guest_phone}\n\n"
            f"Sistemazione: {booking.unit.name}\n"
            f"Check-in: {booking.check_in.strftime('%d/%m/%Y')}\n"
            f"Check-out: {booking.check_out.strftime('%d/%m/%Y')}\n"
            f"Notti: {booking.nights}\n"
            f"Ospiti: {booking.num_guests}\n\n"
            f"Totale: €{booking.total_amount}\n"
            f"Acconto richiesto: €{booking.deposit_amount}\n\n"
            f"Stato: In attesa di pagamento\n\n"
            f"Accedi alla dashboard per gestire la prenotazione:\n"
            f"https://altesiasuite.com/dashboard/prenotazioni/{booking.id}/\n"
        )
        
        if booking.experiences:
            message += f"\nEsperienze richieste: {booking.experiences}\n"
        if booking.guest_notes:
            message += f"\nNote ospite:\n{booking.guest_notes}\n"
        
        recipient = getattr(settings, 'CONTACT_EMAIL', settings.DEFAULT_FROM_EMAIL)
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=True,
        )
    except Exception:
        # Non bloccare la prenotazione se l'email fallisce
        pass


def send_booking_confirmation_to_guest(booking: Booking):
    """
    Invia email di conferma all'ospite quando la prenotazione viene confermata.

    Va nella lingua scelta dall'ospite sul sito: questa funzione viene
    chiamata dal webhook Stripe, fuori da una richiesta HTTP, quindi la
    lingua attiva non è quella dell'ospite e va forzata a mano.
    """
    try:
        with translation.override(booking.language or settings.LANGUAGE_CODE):
            separator = '=' * 50
            subject = _(
                'Prenotazione Confermata #%(number)s - Altèsia Suite'
            ) % {'number': booking.booking_number}

            message = _(
                "Gentile %(first_name)s,\n"
                "\n"
                "La tua prenotazione è stata confermata! Ti aspettiamo.\n"
                "\n"
                "%(separator)s\n"
                "DETTAGLI PRENOTAZIONE\n"
                "%(separator)s\n"
                "\n"
                "Numero prenotazione: %(number)s\n"
                "Sistemazione: %(unit)s\n"
                "\n"
                "Check-in: %(check_in)s\n"
                "   Orario: dalle 15:00\n"
                "Check-out: %(check_out)s\n"
                "   Orario: entro le 10:00\n"
                "\n"
                "Notti: %(nights)s\n"
                "Ospiti: %(guests)s\n"
                "\n"
                "%(separator)s\n"
                "RIEPILOGO PAGAMENTO\n"
                "%(separator)s\n"
                "\n"
                "Totale soggiorno: €%(total)s\n"
                "Acconto pagato: €%(deposit)s\n"
                "Saldo da pagare in loco: €%(balance)s\n"
                "\n"
            ) % {
                'first_name': booking.guest_first_name,
                'separator': separator,
                'number': booking.booking_number,
                'unit': booking.unit.name,
                'check_in': date_format(booking.check_in, 'l j F Y'),
                'check_out': date_format(booking.check_out, 'l j F Y'),
                'nights': booking.nights,
                'guests': booking.num_guests,
                'total': booking.total_amount,
                'deposit': booking.deposit_amount,
                'balance': booking.balance_due,
            }

            if booking.experiences:
                message += _('Esperienze richieste: %(experiences)s\n') % {
                    'experiences': booking.experiences
                }
            if booking.guest_notes:
                message += _('Le tue note: %(notes)s\n\n') % {
                    'notes': booking.guest_notes
                }

            message += _(
                "%(separator)s\n"
                "INFORMAZIONI UTILI\n"
                "%(separator)s\n"
                "\n"
                "Indirizzo: Strada di Civitella Benazzone 20, 06134 Perugia (PG), Umbria\n"
                "Mappa: https://www.google.com/maps/search/?api=1&query=43.20914077758789,12.454292297363281\n"
                "\n"
                "Per qualsiasi domanda o richiesta speciale,\n"
                "non esitare a contattarci:\n"
                "Email: info@altesiasuite.com\n"
                "Telefono: +39 347 6532405\n"
                "\n"
                "Ti aspettiamo!\n"
                "Il team di Altèsia Suite\n"
            ) % {'separator': separator}

            try:
                html_message = render_to_string(
                    'booking/email/booking_confirmation.html', {'booking': booking}
                )
            except Exception:
                html_message = None

            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[booking.guest_email],
                html_message=html_message,
                fail_silently=True,
            )
    except Exception:
        pass


class AvailabilityService:
    """Service for checking and managing availability."""

    @staticmethod
    def is_date_available(unit: BookableUnit, check_date: date) -> bool:
        """Check if a specific date is available for a unit."""
        return not BlockedDate.objects.filter(
            unit__in=unit.blocking_units(),
            date=check_date
        ).exists()

    @staticmethod
    def is_range_available(unit: BookableUnit, check_in: date, check_out: date) -> bool:
        """Check if a date range is fully available."""
        blocked_count = BlockedDate.objects.filter(
            unit__in=unit.blocking_units(),
            date__gte=check_in,
            date__lt=check_out
        ).count()
        return blocked_count == 0

    @staticmethod
    def get_blocked_dates(unit: BookableUnit, start_date: date, end_date: date) -> List[date]:
        """Get list of blocked dates in a range."""
        return list(BlockedDate.objects.filter(
            unit__in=unit.blocking_units(),
            date__gte=start_date,
            date__lte=end_date
        ).values_list('date', flat=True).distinct())

    @staticmethod
    def get_availability_calendar(unit: BookableUnit, year: int, month: int) -> Dict[str, dict]:
        """
        Get availability calendar for a month.
        Returns dict with date as key and availability info as value.
        """
        from calendar import monthrange
        
        first_day = date(year, month, 1)
        last_day = date(year, month, monthrange(year, month)[1])
        
        blocked = set(BlockedDate.objects.filter(
            unit__in=unit.blocking_units(),
            date__gte=first_day,
            date__lte=last_day
        ).values_list('date', flat=True))
        
        calendar_data = {}
        current = first_day
        today = date.today()
        min_advance = getattr(settings, 'BOOKING_MIN_ADVANCE_DAYS', 1)
        
        while current <= last_day:
            is_past = current < today
            is_too_soon = current < today + timedelta(days=min_advance)
            is_blocked = current in blocked
            
            calendar_data[current.isoformat()] = {
                'date': current,
                'available': not (is_past or is_too_soon or is_blocked),
                'is_past': is_past,
                'is_blocked': is_blocked,
                'price': PricingService.get_price_for_date(unit, current) if not is_past else None
            }
            current += timedelta(days=1)
        
        return calendar_data

    @staticmethod
    def get_next_available_dates(unit: BookableUnit, min_nights: int = None) -> Tuple[Optional[date], Optional[date]]:
        """Find the next available check-in and check-out dates."""
        if min_nights is None:
            min_nights = unit.min_nights
        
        today = date.today()
        min_advance = getattr(settings, 'BOOKING_MIN_ADVANCE_DAYS', 1)
        start_search = today + timedelta(days=min_advance)
        
        # Search up to 365 days ahead
        for i in range(365):
            check_in = start_search + timedelta(days=i)
            check_out = check_in + timedelta(days=min_nights)
            
            if AvailabilityService.is_range_available(unit, check_in, check_out):
                return check_in, check_out
        
        return None, None


class PricingService:
    """Service for calculating booking prices."""

    @staticmethod
    def get_price_for_date(unit: BookableUnit, check_date: date) -> Decimal:
        """Get the price for a specific date."""
        season_price = SeasonPrice.objects.filter(
            unit=unit,
            start_date__lte=check_date,
            end_date__gte=check_date
        ).first()
        
        if season_price:
            return season_price.price_per_night
        return unit.base_price

    @staticmethod
    def get_season_for_date(unit: BookableUnit, check_date: date) -> Optional[str]:
        """Get the season name for a date."""
        season_price = SeasonPrice.objects.filter(
            unit=unit,
            start_date__lte=check_date,
            end_date__gte=check_date
        ).first()
        
        return season_price.name if season_price else None

    @staticmethod
    def calculate_booking_price(
        unit: BookableUnit,
        check_in: date,
        check_out: date,
        num_guests: int = 1
    ) -> Dict:
        """
        Calculate full price breakdown for a booking.
        Returns dict with all pricing details.
        """
        nights = (check_out - check_in).days
        
        if nights <= 0:
            raise ValueError(_("Check-out deve essere dopo check-in"))
        
        if nights < unit.min_nights:
            raise ValueError(
                _("Soggiorno minimo: %(nights)s notti") % {'nights': unit.min_nights}
            )
        
        if nights > unit.max_nights:
            raise ValueError(
                _("Soggiorno massimo: %(nights)s notti") % {'nights': unit.max_nights}
            )
        
        if num_guests > unit.max_guests:
            raise ValueError(
                _("Massimo %(guests)s ospiti") % {'guests': unit.max_guests}
            )
        
        # Calculate price per night
        price_breakdown = []
        total_price = Decimal('0.00')
        current_date = check_in
        
        while current_date < check_out:
            price = PricingService.get_price_for_date(unit, current_date)
            season = PricingService.get_season_for_date(unit, current_date)
            
            price_breakdown.append({
                'date': current_date,
                'price': price,
                'season': season or 'Base'
            })
            
            total_price += price
            current_date += timedelta(days=1)
        
        # Calculate averages and totals
        avg_price_per_night = total_price / nights
        cleaning_fee = unit.cleaning_fee
        subtotal = total_price
        total_amount = subtotal + cleaning_fee
        
        # Calculate deposit
        deposit_percentage = Decimal(getattr(settings, 'BOOKING_DEPOSIT_PERCENTAGE', 30))
        deposit_amount = (total_amount * deposit_percentage / 100).quantize(Decimal('0.01'))
        balance_due = total_amount - deposit_amount
        
        return {
            'nights': nights,
            'price_breakdown': price_breakdown,
            'price_per_night_avg': avg_price_per_night,
            'subtotal': subtotal,
            'cleaning_fee': cleaning_fee,
            'total_amount': total_amount,
            'deposit_amount': deposit_amount,
            'deposit_percentage': deposit_percentage,
            'balance_due': balance_due,
            'currency': 'EUR'
        }


class BookingService:
    """Service for creating and managing bookings."""

    @staticmethod
    def create_booking(
        unit: BookableUnit,
        check_in: date,
        check_out: date,
        guest_data: dict,
        user=None
    ) -> Booking:
        """
        Create a new booking (pending status).
        Does NOT create blocked dates until confirmed via payment webhook.
        """
        # Verify availability
        if not AvailabilityService.is_range_available(unit, check_in, check_out):
            raise ValueError(_("Le date selezionate non sono più disponibili"))
        
        # Calculate pricing
        num_guests = guest_data.get('num_guests', 1)
        pricing = PricingService.calculate_booking_price(
            unit, check_in, check_out, num_guests
        )
        
        # Create booking
        booking = Booking.objects.create(
            unit=unit,
            user=user,
            language=get_language() or settings.LANGUAGE_CODE,
            experiences=guest_data.get('experiences', ''),
            guest_first_name=guest_data['first_name'],
            guest_last_name=guest_data['last_name'],
            guest_email=guest_data['email'],
            guest_phone=guest_data['phone'],
            guest_country=guest_data.get('country', ''),
            check_in=check_in,
            check_out=check_out,
            num_guests=num_guests,
            nights=pricing['nights'],
            price_per_night_avg=pricing['price_per_night_avg'],
            subtotal=pricing['subtotal'],
            cleaning_fee=pricing['cleaning_fee'],
            total_amount=pricing['total_amount'],
            deposit_amount=pricing['deposit_amount'],
            balance_due=pricing['balance_due'],
            currency=pricing['currency'],
            guest_notes=guest_data.get('notes', ''),
            arrival_time=guest_data.get('arrival_time'),
            status=Booking.Status.PENDING,
            payment_status=Booking.PaymentStatus.PENDING
        )
        
        # Create price details
        for item in pricing['price_breakdown']:
            BookingPriceDetail.objects.create(
                booking=booking,
                date=item['date'],
                price=item['price'],
                season_name=item['season']
            )
        
        # Invia notifica email all'admin
        send_new_booking_notification(booking)
        
        return booking

    @staticmethod
    def confirm_booking(booking: Booking) -> Booking:
        """
        Confirm a booking after successful payment.
        Creates blocked dates to prevent double bookings.
        """
        # Double-check availability
        if not AvailabilityService.is_range_available(
            booking.unit, booking.check_in, booking.check_out
        ):
            # Someone else booked in the meantime
            raise ValueError(_("Le date non sono più disponibili"))
        
        booking.confirm()
        
        # Invia email di conferma all'ospite
        send_booking_confirmation_to_guest(booking)
        
        return booking

    @staticmethod
    def cancel_booking(booking: Booking, reason: str = '') -> Booking:
        """Cancel a booking and free up the dates."""
        booking.cancel(reason)
        return booking

    @staticmethod
    def get_bookings_for_user(user) -> List[Booking]:
        """Get all bookings for a user."""
        return Booking.objects.filter(
            Q(user=user) | Q(guest_email=user.email)
        ).order_by('-created_at')

    @staticmethod
    def get_booking_by_number(booking_number: str, email: str = None) -> Optional[Booking]:
        """
        Get booking by number, optionally verifying email for guests.
        """
        filters = {'booking_number': booking_number}
        if email:
            filters['guest_email__iexact'] = email
        
        return Booking.objects.filter(**filters).first()
