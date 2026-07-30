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
    """
    try:
        subject = f'Prenotazione Confermata #{booking.booking_number} - Altèsia Suite'
        
        message = (
            f"Gentile {booking.guest_first_name},\n\n"
            f"La tua prenotazione è stata confermata! Ti aspettiamo.\n\n"
            f"{'=' * 50}\n"
            f"DETTAGLI PRENOTAZIONE\n"
            f"{'=' * 50}\n\n"
            f"Numero prenotazione: {booking.booking_number}\n"
            f"Sistemazione: {booking.unit.name}\n\n"
            f"Check-in: {booking.check_in.strftime('%A %d %B %Y')}\n"
            f"   Orario: dalle 15:00\n"
            f"Check-out: {booking.check_out.strftime('%A %d %B %Y')}\n"
            f"   Orario: entro le 10:00\n\n"
            f"Notti: {booking.nights}\n"
            f"Ospiti: {booking.num_guests}\n\n"
            f"{'=' * 50}\n"
            f"RIEPILOGO PAGAMENTO\n"
            f"{'=' * 50}\n\n"
            f"Totale soggiorno: €{booking.total_amount}\n"
            f"Acconto pagato: €{booking.deposit_amount}\n"
            f"Saldo da pagare in loco: €{booking.balance_due}\n\n"
        )
        
        if booking.guest_notes:
            message += f"Le tue note: {booking.guest_notes}\n\n"
        
        message += (
            f"{'=' * 50}\n"
            f"INFORMAZIONI UTILI\n"
            f"{'=' * 50}\n\n"
            f"Indirizzo: Strada di Civitella Benazzone 20, 06134 Perugia (PG), Umbria\n"
            f"Coordinate GPS: 43.1480, 12.3830\n\n"
            f"Per qualsiasi domanda o richiesta speciale,\n"
            f"non esitare a contattarci:\n"
            f"Email: info@altesiasuite.com\n"
            f"Telefono: +39 347 6532405\n\n"
            f"Ti aspettiamo!\n"
            f"Il team di Altèsia Suite\n"
        )
        
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
            unit=unit,
            date=check_date
        ).exists()

    @staticmethod
    def is_range_available(unit: BookableUnit, check_in: date, check_out: date) -> bool:
        """Check if a date range is fully available."""
        blocked_count = BlockedDate.objects.filter(
            unit=unit,
            date__gte=check_in,
            date__lt=check_out
        ).count()
        return blocked_count == 0

    @staticmethod
    def get_blocked_dates(unit: BookableUnit, start_date: date, end_date: date) -> List[date]:
        """Get list of blocked dates in a range."""
        return list(BlockedDate.objects.filter(
            unit=unit,
            date__gte=start_date,
            date__lte=end_date
        ).values_list('date', flat=True))

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
            unit=unit,
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
            raise ValueError("Check-out deve essere dopo check-in")
        
        if nights < unit.min_nights:
            raise ValueError(f"Soggiorno minimo: {unit.min_nights} notti")
        
        if nights > unit.max_nights:
            raise ValueError(f"Soggiorno massimo: {unit.max_nights} notti")
        
        if num_guests > unit.max_guests:
            raise ValueError(f"Massimo {unit.max_guests} ospiti")
        
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
            raise ValueError("Le date selezionate non sono più disponibili")
        
        # Calculate pricing
        num_guests = guest_data.get('num_guests', 1)
        pricing = PricingService.calculate_booking_price(
            unit, check_in, check_out, num_guests
        )
        
        # Create booking
        booking = Booking.objects.create(
            unit=unit,
            user=user,
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
            raise ValueError("Le date non sono più disponibili")
        
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
