from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Booking, BlockedDate, BookingPriceDetail


class BookingPriceDetailInline(admin.TabularInline):
    model = BookingPriceDetail
    extra = 0
    readonly_fields = ('date', 'price', 'season_name')
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'booking_number', 'guest_full_name', 'unit', 'check_in', 'check_out',
        'nights', 'total_amount', 'status_badge', 'payment_status_badge', 'created_at'
    )
    list_filter = ('status', 'payment_status', 'unit', 'check_in')
    search_fields = ('booking_number', 'guest_first_name', 'guest_last_name', 'guest_email')
    readonly_fields = (
        'booking_number', 'created_at', 'updated_at', 'confirmed_at', 'cancelled_at',
        'nights', 'price_per_night_avg', 'subtotal', 'total_amount', 'deposit_amount', 'balance_due'
    )
    inlines = [BookingPriceDetailInline]
    date_hierarchy = 'check_in'
    
    fieldsets = (
        ('Prenotazione', {
            'fields': ('booking_number', 'unit', 'user', 'status', 'payment_status')
        }),
        ('Ospite', {
            'fields': (
                'guest_first_name', 'guest_last_name', 'guest_email',
                'guest_phone', 'guest_country'
            )
        }),
        ('Date', {
            'fields': ('check_in', 'check_out', 'num_guests', 'arrival_time')
        }),
        ('Prezzi', {
            'fields': (
                'nights', 'price_per_night_avg', 'subtotal', 'cleaning_fee',
                'total_amount', 'deposit_amount', 'balance_due', 'currency'
            )
        }),
        ('Note', {
            'fields': ('guest_notes', 'admin_notes', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
            'classes': ('collapse',)
        }),
    )

    def guest_full_name(self, obj):
        return obj.guest_full_name
    guest_full_name.short_description = 'Ospite'

    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'CONFIRMED': 'green',
            'CANCELLED': 'red',
            'COMPLETED': 'blue',
            'NO_SHOW': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Stato'

    def payment_status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'DEPOSIT_PAID': 'blue',
            'FULLY_PAID': 'green',
            'REFUNDED': 'purple',
            'PARTIAL_REFUND': 'purple'
        }
        color = colors.get(obj.payment_status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_payment_status_display()
        )
    payment_status_badge.short_description = 'Pagamento'

    actions = ['mark_as_confirmed', 'mark_as_cancelled']

    def mark_as_confirmed(self, request, queryset):
        for booking in queryset.filter(status=Booking.Status.PENDING):
            booking.confirm()
        self.message_user(request, f'{queryset.count()} prenotazioni confermate.')
    mark_as_confirmed.short_description = 'Conferma prenotazioni selezionate'

    def mark_as_cancelled(self, request, queryset):
        for booking in queryset.exclude(status=Booking.Status.CANCELLED):
            booking.cancel('Cancellata da admin')
        self.message_user(request, f'{queryset.count()} prenotazioni cancellate.')
    mark_as_cancelled.short_description = 'Cancella prenotazioni selezionate'


@admin.register(BlockedDate)
class BlockedDateAdmin(admin.ModelAdmin):
    list_display = ('unit', 'date', 'reason', 'booking_link', 'note')
    list_filter = ('unit', 'reason', 'date')
    search_fields = ('note', 'booking__booking_number')
    date_hierarchy = 'date'
    raw_id_fields = ('booking',)

    def booking_link(self, obj):
        if obj.booking:
            url = reverse('admin:booking_booking_change', args=[obj.booking.pk])
            return format_html('<a href="{}">{}</a>', url, obj.booking.booking_number)
        return '-'
    booking_link.short_description = 'Prenotazione'
