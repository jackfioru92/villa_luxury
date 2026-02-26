from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import TemplateView, View, DetailView
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from datetime import date, datetime, timedelta
import calendar as cal_module
import json

from apps.villa.models import BookableUnit
from .models import Booking
from .forms import BookingStep1Form, BookingStep2Form, BookingSearchForm
from .services import AvailabilityService, PricingService, BookingService


class BookingWizardView(TemplateView):
    """Main booking wizard page."""
    template_name = 'booking/booking_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = BookableUnit.objects.filter(is_active=True)
        
        # Pre-select unit if provided
        unit_slug = self.request.GET.get('unit')
        if unit_slug:
            context['selected_unit'] = BookableUnit.objects.filter(
                slug=unit_slug, is_active=True
            ).first()
        
        return context


class BookingConfirmationView(DetailView):
    """Booking confirmation page after payment."""
    model = Booking
    template_name = 'booking/booking_confirmation.html'
    context_object_name = 'booking'
    slug_field = 'booking_number'
    slug_url_kwarg = 'booking_number'


class BookingSearchView(View):
    """Search for existing booking."""
    template_name = 'booking/booking_search.html'

    def get(self, request):
        form = BookingSearchForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = BookingSearchForm(request.POST)
        if form.is_valid():
            booking = BookingService.get_booking_by_number(
                form.cleaned_data['booking_number'],
                form.cleaned_data['email']
            )
            if booking:
                return redirect('booking:confirmation', booking_number=booking.booking_number)
            else:
                messages.error(request, _('Prenotazione non trovata'))
        
        return render(request, self.template_name, {'form': form})


# ============= HTMX Partial Views =============

class HTMXAvailabilityCalendarView(View):
    """HTMX endpoint for availability calendar."""

    WEEKDAYS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
    MONTH_NAMES = [
        '', 'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
        'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre'
    ]

    def get(self, request):
        unit_id = request.GET.get('unit')
        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))

        if not unit_id:
            return HttpResponse('Unit required', status=400)

        unit = get_object_or_404(BookableUnit, pk=unit_id, is_active=True)
        calendar_data = AvailabilityService.get_availability_calendar(unit, year, month)

        # Build calendar days grid (including padding from prev/next month)
        first_day = date(year, month, 1)
        _, days_in_month = cal_module.monthrange(year, month)
        last_day = date(year, month, days_in_month)

        # Monday = 0, so first_day.weekday() gives padding needed
        start_weekday = first_day.weekday()
        today = date.today()

        calendar_days = []

        # Padding days from previous month
        if start_weekday > 0:
            prev_month_date = first_day - timedelta(days=start_weekday)
            for i in range(start_weekday):
                d = prev_month_date + timedelta(days=i)
                calendar_days.append({
                    'day': d.day,
                    'date': d.isoformat(),
                    'is_other_month': True,
                    'is_today': d == today,
                    'is_past': d < today,
                    'is_available': False,
                    'is_blocked': False,
                    'is_booked': False,
                })

        # Days of current month
        for day_num in range(1, days_in_month + 1):
            d = date(year, month, day_num)
            d_iso = d.isoformat()
            info = calendar_data.get(d_iso, {})
            calendar_days.append({
                'day': d.day,
                'date': d_iso,
                'is_other_month': False,
                'is_today': d == today,
                'is_past': info.get('is_past', d < today),
                'is_available': info.get('available', False),
                'is_blocked': info.get('is_blocked', False),
                'is_booked': False,
            })

        # Padding days from next month to fill last row
        remaining = 7 - (len(calendar_days) % 7)
        if remaining < 7:
            next_month_start = last_day + timedelta(days=1)
            for i in range(remaining):
                d = next_month_start + timedelta(days=i)
                calendar_days.append({
                    'day': d.day,
                    'date': d.isoformat(),
                    'is_other_month': True,
                    'is_today': d == today,
                    'is_past': d < today,
                    'is_available': False,
                    'is_blocked': False,
                    'is_booked': False,
                })

        # Previous / Next month
        if month == 1:
            prev_month, prev_year = 12, year - 1
        else:
            prev_month, prev_year = month - 1, year

        if month == 12:
            next_month, next_year = 1, year + 1
        else:
            next_month, next_year = month + 1, year

        return render(request, 'booking/partials/availability_calendar.html', {
            'calendar_days': calendar_days,
            'weekdays': self.WEEKDAYS,
            'unit': unit,
            'unit_id': unit_id,
            'year': year,
            'month': month,
            'month_name': self.MONTH_NAMES[month],
            'prev_month': prev_month,
            'prev_year': prev_year,
            'next_month': next_month,
            'next_year': next_year,
        })


class HTMXPriceCalculationView(View):
    """HTMX endpoint for price calculation."""

    def get(self, request):
        unit_id = request.GET.get('unit')
        check_in_str = request.GET.get('check_in')
        check_out_str = request.GET.get('check_out')
        num_guests = int(request.GET.get('num_guests', 1))

        if not all([unit_id, check_in_str, check_out_str]):
            return HttpResponse('', status=200)

        try:
            unit = get_object_or_404(BookableUnit, pk=unit_id, is_active=True)
            check_in = datetime.strptime(check_in_str, '%Y-%m-%d').date()
            check_out = datetime.strptime(check_out_str, '%Y-%m-%d').date()

            # Check availability
            if not AvailabilityService.is_range_available(unit, check_in, check_out):
                return render(request, 'booking/partials/price_summary.html', {
                    'error': _('Le date selezionate non sono disponibili'),
                    'unit': unit
                })

            # Calculate pricing
            pricing = PricingService.calculate_booking_price(
                unit, check_in, check_out, num_guests
            )

            return render(request, 'booking/partials/price_summary.html', {
                'pricing': pricing,
                'unit': unit,
                'check_in': check_in,
                'check_out': check_out,
                'num_guests': num_guests
            })

        except ValueError as e:
            return render(request, 'booking/partials/price_summary.html', {
                'error': str(e),
                'unit': unit if 'unit' in dir() else None
            })


class HTMXBookingStepView(View):
    """HTMX endpoint for booking wizard steps."""

    def get(self, request, step):
        """Render a specific step of the booking wizard."""
        context = {'step': step}

        if step == 1:
            # Unit selection
            context['units'] = BookableUnit.objects.filter(is_active=True)
            unit_id = request.GET.get('unit')
            if unit_id:
                context['selected_unit'] = BookableUnit.objects.filter(
                    pk=unit_id, is_active=True
                ).first()

        elif step == 2:
            # Date selection
            unit_id = request.session.get('booking_unit')
            if unit_id:
                context['unit'] = get_object_or_404(BookableUnit, pk=unit_id)

        elif step == 3:
            # Guest info form
            context['form'] = BookingStep2Form()
            if request.user.is_authenticated:
                context['form'] = BookingStep2Form(initial={
                    'first_name': request.user.first_name,
                    'last_name': request.user.last_name,
                    'email': request.user.email,
                    'phone': getattr(request.user, 'phone', ''),
                })

        elif step == 4:
            # Summary before payment
            booking_data = request.session.get('booking_data', {})
            context['booking_data'] = booking_data

        return render(request, f'booking/partials/step_{step}.html', context)

    def post(self, request, step):
        """Process step submission."""
        if step == 1:
            # Save selected unit
            unit_id = request.POST.get('unit')
            if unit_id:
                request.session['booking_unit'] = unit_id
                return HttpResponse(
                    status=200,
                    headers={'HX-Trigger': 'stepCompleted'}
                )

        elif step == 2:
            # Save dates
            check_in = request.POST.get('check_in')
            check_out = request.POST.get('check_out')
            num_guests = request.POST.get('num_guests', 1)

            request.session['booking_dates'] = {
                'check_in': check_in,
                'check_out': check_out,
                'num_guests': int(num_guests)
            }
            return HttpResponse(
                status=200,
                headers={'HX-Trigger': 'stepCompleted'}
            )

        elif step == 3:
            # Save guest info and create booking
            form = BookingStep2Form(request.POST)
            if form.is_valid():
                request.session['booking_guest'] = form.cleaned_data
                
                # Create the booking
                try:
                    unit = get_object_or_404(
                        BookableUnit,
                        pk=request.session.get('booking_unit')
                    )
                    dates = request.session.get('booking_dates', {})
                    guest_data = form.cleaned_data
                    guest_data['num_guests'] = dates.get('num_guests', 1)
                    
                    check_in = datetime.strptime(dates['check_in'], '%Y-%m-%d').date()
                    check_out = datetime.strptime(dates['check_out'], '%Y-%m-%d').date()
                    
                    booking = BookingService.create_booking(
                        unit=unit,
                        check_in=check_in,
                        check_out=check_out,
                        guest_data=guest_data,
                        user=request.user if request.user.is_authenticated else None
                    )
                    
                    request.session['pending_booking_id'] = str(booking.id)
                    
                    return HttpResponse(
                        status=200,
                        headers={'HX-Trigger': 'stepCompleted'}
                    )

                except ValueError as e:
                    return render(request, 'booking/partials/step_3.html', {
                        'form': form,
                        'error': str(e)
                    })

            return render(request, 'booking/partials/step_3.html', {'form': form})

        return HttpResponse(status=400)


class HTMXUnitSelectView(View):
    """HTMX endpoint for unit selection cards."""

    def get(self, request):
        units = BookableUnit.objects.filter(is_active=True).order_by('sort_order')
        return render(request, 'booking/partials/unit_cards.html', {
            'units': units
        })


class BookingCreateAPIView(View):
    """
    API endpoint to create a booking and return the payment redirect URL.
    Accepts JSON POST with all booking data from the wizard.
    """

    def post(self, request):
        import json as json_module
        from django.urls import reverse

        try:
            data = json_module.loads(request.body)
        except (json_module.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Dati non validi.'}, status=400)

        # Validate required fields
        required_fields = ['unit', 'check_in', 'check_out', 'first_name', 'last_name', 'email', 'phone']
        missing = [f for f in required_fields if not data.get(f)]
        if missing:
            return JsonResponse(
                {'error': f'Campi obbligatori mancanti: {", ".join(missing)}'},
                status=400
            )

        # Validate terms acceptance
        if not data.get('terms_accepted') or not data.get('privacy_accepted'):
            return JsonResponse(
                {'error': 'Devi accettare i Termini e la Privacy Policy.'},
                status=400
            )

        try:
            unit = get_object_or_404(BookableUnit, pk=data['unit'], is_active=True)
            check_in = datetime.strptime(data['check_in'], '%Y-%m-%d').date()
            check_out = datetime.strptime(data['check_out'], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Date non valide.'}, status=400)

        # Validate dates
        if check_in >= check_out:
            return JsonResponse({'error': 'Il check-out deve essere dopo il check-in.'}, status=400)

        if check_in <= date.today():
            return JsonResponse({'error': 'Il check-in deve essere una data futura.'}, status=400)

        num_guests = int(data.get('num_guests', 1))

        # Parse arrival_time
        arrival_time = None
        if data.get('arrival_time'):
            try:
                arrival_time = datetime.strptime(data['arrival_time'], '%H:%M').time()
            except ValueError:
                pass

        guest_data = {
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'email': data['email'],
            'phone': data['phone'],
            'country': data.get('country', ''),
            'notes': data.get('notes', ''),
            'arrival_time': arrival_time,
            'num_guests': num_guests,
        }

        try:
            booking = BookingService.create_booking(
                unit=unit,
                check_in=check_in,
                check_out=check_out,
                guest_data=guest_data,
                user=request.user if request.user.is_authenticated else None
            )
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)

        # Store booking in session
        request.session['pending_booking_id'] = str(booking.id)

        # Build payment URL
        payment_url = reverse('payments:checkout', kwargs={'booking_id': booking.id})

        return JsonResponse({
            'success': True,
            'booking_number': booking.booking_number,
            'booking_id': str(booking.id),
            'payment_url': payment_url,
            'total_amount': str(booking.total_amount),
            'deposit_amount': str(booking.deposit_amount),
        })
