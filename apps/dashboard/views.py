from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, DetailView, View
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from datetime import date, timedelta
from decimal import Decimal

from apps.booking.models import Booking, BlockedDate
from apps.booking.services import send_booking_confirmation_to_guest
from apps.villa.models import BookableUnit
from apps.payments.models import Payment


@method_decorator(staff_member_required, name='dispatch')
class DashboardOverviewView(TemplateView):
    """Main dashboard overview."""
    template_name = 'dashboard/overview.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        today = date.today()
        
        # Date ranges
        start_of_month = today.replace(day=1)
        start_of_week = today - timedelta(days=today.weekday())
        
        # Booking stats
        all_bookings = Booking.objects.all()
        context['total_bookings'] = all_bookings.count()
        context['pending_bookings'] = all_bookings.filter(status=Booking.Status.PENDING).count()
        context['confirmed_bookings'] = all_bookings.filter(status=Booking.Status.CONFIRMED).count()
        
        # Today's arrivals and departures
        context['arrivals_today'] = all_bookings.filter(
            check_in=today, status=Booking.Status.CONFIRMED
        )
        context['departures_today'] = all_bookings.filter(
            check_out=today, status=Booking.Status.CONFIRMED
        )
        
        # Current guests
        context['current_guests'] = all_bookings.filter(
            check_in__lte=today,
            check_out__gt=today,
            status=Booking.Status.CONFIRMED
        )
        
        # Upcoming bookings (next 7 days)
        context['upcoming_bookings'] = all_bookings.filter(
            check_in__gt=today,
            check_in__lte=today + timedelta(days=7),
            status=Booking.Status.CONFIRMED
        ).order_by('check_in')[:10]
        
        # Revenue stats
        context['revenue_month'] = Payment.objects.filter(
            status=Payment.Status.COMPLETED,
            completed_at__gte=start_of_month
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        context['revenue_total'] = Payment.objects.filter(
            status=Payment.Status.COMPLETED
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        # Recent bookings
        context['recent_bookings'] = all_bookings.order_by('-created_at')[:10]
        
        # Units
        context['units'] = BookableUnit.objects.filter(is_active=True)
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class BookingListView(ListView):
    """List all bookings with filters."""
    model = Booking
    template_name = 'dashboard/booking_list.html'
    context_object_name = 'bookings'
    paginate_by = 25

    def get_queryset(self):
        queryset = Booking.objects.all().order_by('-created_at')
        
        # Filters
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        payment_status = self.request.GET.get('payment_status')
        if payment_status:
            queryset = queryset.filter(payment_status=payment_status)
        
        unit = self.request.GET.get('unit')
        if unit:
            queryset = queryset.filter(unit_id=unit)
        
        # Date filters
        check_in_from = self.request.GET.get('check_in_from')
        if check_in_from:
            queryset = queryset.filter(check_in__gte=check_in_from)
        
        check_in_to = self.request.GET.get('check_in_to')
        if check_in_to:
            queryset = queryset.filter(check_in__lte=check_in_to)
        
        # Search
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(booking_number__icontains=search) |
                Q(guest_first_name__icontains=search) |
                Q(guest_last_name__icontains=search) |
                Q(guest_email__icontains=search)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = BookableUnit.objects.filter(is_active=True)
        context['statuses'] = Booking.Status.choices
        context['payment_statuses'] = Booking.PaymentStatus.choices
        
        # Current filters
        context['current_filters'] = {
            'status': self.request.GET.get('status', ''),
            'payment_status': self.request.GET.get('payment_status', ''),
            'unit': self.request.GET.get('unit', ''),
            'search': self.request.GET.get('search', ''),
        }
        return context


@method_decorator(staff_member_required, name='dispatch')
class BookingDetailView(DetailView):
    """Detailed view of a single booking."""
    model = Booking
    template_name = 'dashboard/booking_detail.html'
    context_object_name = 'booking'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['payments'] = self.object.payments.all()
        context['price_details'] = self.object.price_details.all()
        return context


@method_decorator(staff_member_required, name='dispatch')
class CalendarView(TemplateView):
    """Calendar view of all bookings."""
    template_name = 'dashboard/calendar.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = BookableUnit.objects.filter(is_active=True)
        return context


@method_decorator(staff_member_required, name='dispatch')
class CalendarEventsAPIView(View):
    """API endpoint for calendar events."""

    def get(self, request):
        start = request.GET.get('start')
        end = request.GET.get('end')
        unit_id = request.GET.get('unit')

        filters = {
            'check_in__lte': end,
            'check_out__gte': start,
            'status__in': [Booking.Status.CONFIRMED, Booking.Status.PENDING]
        }

        if unit_id:
            filters['unit_id'] = unit_id

        bookings = Booking.objects.filter(**filters)

        events = []
        for booking in bookings:
            color = '#22c55e' if booking.status == Booking.Status.CONFIRMED else '#f97316'
            events.append({
                'id': str(booking.id),
                'title': f'{booking.guest_full_name} ({booking.unit.name})',
                'start': booking.check_in.isoformat(),
                'end': booking.check_out.isoformat(),
                'color': color,
                'url': f'/dashboard/prenotazioni/{booking.pk}/',
                'extendedProps': {
                    'booking_number': booking.booking_number,
                    'unit': booking.unit.name,
                    'guests': booking.num_guests,
                    'status': booking.status
                }
            })

        # Add blocked dates (all non-booking blocks)
        blocked_filters = {
            'date__gte': start,
            'date__lte': end,
            'booking__isnull': True  # Only manual blocks, not booking-related
        }
        if unit_id:
            blocked_filters['unit_id'] = unit_id

        blocked_dates = BlockedDate.objects.filter(**blocked_filters)
        for blocked in blocked_dates:
            events.append({
                'id': f'blocked-{blocked.id}',
                'title': f'Bloccato: {blocked.reason}',
                'start': blocked.date.isoformat(),
                'allDay': True,
                'color': '#6b7280',
                'extendedProps': {
                    'type': 'blocked',
                    'reason': blocked.reason
                }
            })

        return JsonResponse(events, safe=False)


@method_decorator(staff_member_required, name='dispatch')
class BlockDatesView(TemplateView):
    """Manage blocked dates."""
    template_name = 'dashboard/block_dates.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = BookableUnit.objects.filter(is_active=True)
        context['reasons'] = BlockedDate.Reason.choices
        
        # Get all manual blocks (non-booking) and group consecutive dates
        blocked_dates = BlockedDate.objects.filter(
            booking__isnull=True,
            date__gte=date.today()
        ).order_by('unit', 'date').select_related('unit')
        
        # Group consecutive dates by unit and reason
        grouped_blocks = []
        current_block = None
        
        for blocked in blocked_dates:
            if (current_block is None or 
                current_block['unit'] != blocked.unit or
                current_block['reason'] != blocked.reason or
                (blocked.date - current_block['end_date']).days > 1):
                # Start new block
                if current_block:
                    grouped_blocks.append(current_block)
                current_block = {
                    'id': blocked.id,
                    'unit': blocked.unit,
                    'start_date': blocked.date,
                    'end_date': blocked.date,
                    'reason': blocked.reason,
                }
            else:
                # Extend current block
                current_block['end_date'] = blocked.date
        
        if current_block:
            grouped_blocks.append(current_block)
        
        context['blocked_dates'] = grouped_blocks
        
        return context

    def post(self, request):
        """Create new blocked dates."""
        unit_id = request.POST.get('unit')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        reason = request.POST.get('reason')
        note = request.POST.get('note', '')

        if not all([unit_id, start_date, end_date, reason]):
            messages.error(request, 'Compila tutti i campi obbligatori.')
            return redirect('dashboard:block_dates')

        from datetime import datetime
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        unit = get_object_or_404(BookableUnit, pk=unit_id)

        created = 0
        current = start
        while current <= end:
            _, is_new = BlockedDate.objects.get_or_create(
                unit=unit,
                date=current,
                defaults={'reason': reason, 'note': note}
            )
            if is_new:
                created += 1
            current += timedelta(days=1)

        messages.success(request, f'{created} date bloccate con successo.')
        return redirect('dashboard:block_dates')


@method_decorator(staff_member_required, name='dispatch')
class ReportsView(TemplateView):
    """Reports and statistics."""
    template_name = 'dashboard/reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Monthly revenue (last 12 months)
        twelve_months_ago = date.today() - timedelta(days=365)
        monthly_revenue = Payment.objects.filter(
            status=Payment.Status.COMPLETED,
            completed_at__gte=twelve_months_ago
        ).annotate(
            month=TruncMonth('completed_at')
        ).values('month').annotate(
            total=Sum('amount'),
            count=Count('id')
        ).order_by('month')
        
        context['monthly_revenue'] = list(monthly_revenue)
        
        # Bookings by unit
        bookings_by_unit = Booking.objects.filter(
            status=Booking.Status.CONFIRMED
        ).values(
            'unit__name'
        ).annotate(
            count=Count('id'),
            revenue=Sum('total_amount')
        ).order_by('-count')
        
        context['bookings_by_unit'] = list(bookings_by_unit)
        
        # Average booking value
        context['avg_booking_value'] = Booking.objects.filter(
            status=Booking.Status.CONFIRMED
        ).aggregate(avg=Sum('total_amount') / Count('id'))['avg'] or 0
        
        # Occupancy rate (simplified)
        total_days = 365
        booked_days = BlockedDate.objects.filter(
            reason=BlockedDate.Reason.BOOKING,
            date__gte=date.today() - timedelta(days=365),
            date__lte=date.today()
        ).count()
        
        units_count = BookableUnit.objects.filter(is_active=True).count()
        if units_count > 0:
            context['occupancy_rate'] = (booked_days / (total_days * units_count)) * 100
        else:
            context['occupancy_rate'] = 0
        
        return context


@method_decorator(staff_member_required, name='dispatch')
class BookingActionView(View):
    """Handle booking actions: confirm, reject/cancel, update notes."""

    def post(self, request, pk):
        booking = get_object_or_404(Booking, pk=pk)
        action = request.POST.get('action')

        if action == 'confirm' and booking.status == Booking.Status.PENDING:
            booking.confirm()
            send_booking_confirmation_to_guest(booking)
            messages.success(request, f'Prenotazione #{booking.booking_number} confermata con successo. Email inviata all\'ospite.')

        elif action == 'reject' and booking.status == Booking.Status.PENDING:
            reason = request.POST.get('reason', 'Rifiutata dall\'amministratore')
            booking.cancel(reason=reason or 'Rifiutata dall\'amministratore')
            messages.warning(request, f'Prenotazione #{booking.booking_number} rifiutata.')

        elif action == 'cancel' and booking.status == Booking.Status.CONFIRMED:
            booking.cancel(reason='Cancellata dall\'amministratore')
            messages.warning(request, f'Prenotazione #{booking.booking_number} cancellata.')

        elif action == 'update_notes':
            booking.admin_notes = request.POST.get('admin_notes', '')
            booking.save(update_fields=['admin_notes'])
            messages.success(request, 'Note aggiornate.')

        else:
            messages.error(request, 'Azione non valida.')

        return redirect('dashboard:booking_detail', pk=booking.pk)


@method_decorator(staff_member_required, name='dispatch')
class DeleteBlockView(View):
    """Delete blocked dates for a specific block range."""

    def post(self, request, pk):
        # Get the block to find its unit, reason, and date
        block = get_object_or_404(BlockedDate, pk=pk)
        unit = block.unit
        reason = block.reason
        start_date = block.date
        
        # Find all consecutive dates with same unit and reason
        dates_to_delete = [block]
        
        # Look forward
        current_date = start_date + timedelta(days=1)
        while True:
            next_block = BlockedDate.objects.filter(
                unit=unit,
                reason=reason,
                date=current_date,
                booking__isnull=True
            ).first()
            if next_block:
                dates_to_delete.append(next_block)
                current_date += timedelta(days=1)
            else:
                break
        
        # Look backward
        current_date = start_date - timedelta(days=1)
        while True:
            prev_block = BlockedDate.objects.filter(
                unit=unit,
                reason=reason,
                date=current_date,
                booking__isnull=True
            ).first()
            if prev_block:
                dates_to_delete.append(prev_block)
                current_date -= timedelta(days=1)
            else:
                break
        
        # Delete all
        count = len(dates_to_delete)
        for b in dates_to_delete:
            b.delete()
        
        messages.success(request, f'{count} date sbloccate con successo.')
        return redirect('dashboard:block_dates')
