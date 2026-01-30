from django.contrib import admin
from django.utils.html import format_html
from .models import Payment, PaymentLog


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'booking_link', 'amount', 'currency', 'payment_type',
        'status_badge', 'created_at', 'completed_at'
    )
    list_filter = ('status', 'payment_type', 'created_at')
    search_fields = (
        'booking__booking_number', 'stripe_checkout_session_id',
        'stripe_payment_intent_id', 'customer_email'
    )
    readonly_fields = (
        'booking', 'stripe_checkout_session_id', 'stripe_payment_intent_id',
        'stripe_charge_id', 'receipt_url', 'created_at', 'updated_at',
        'completed_at', 'failed_at'
    )
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Prenotazione', {
            'fields': ('booking', 'customer_email')
        }),
        ('Pagamento', {
            'fields': ('amount', 'currency', 'payment_type', 'status')
        }),
        ('Stripe', {
            'fields': (
                'stripe_checkout_session_id', 'stripe_payment_intent_id',
                'stripe_charge_id', 'receipt_url'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at', 'failed_at'),
            'classes': ('collapse',)
        }),
        ('Errori', {
            'fields': ('failure_reason',),
            'classes': ('collapse',)
        }),
    )

    def booking_link(self, obj):
        from django.urls import reverse
        url = reverse('admin:booking_booking_change', args=[obj.booking.pk])
        return format_html('<a href="{}">{}</a>', url, obj.booking.booking_number)
    booking_link.short_description = 'Prenotazione'

    def status_badge(self, obj):
        colors = {
            'PENDING': 'orange',
            'PROCESSING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
            'REFUNDED': 'purple',
            'CANCELLED': 'gray'
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Stato'


@admin.register(PaymentLog)
class PaymentLogAdmin(admin.ModelAdmin):
    list_display = ('event_id', 'event_type', 'payment', 'processed', 'created_at')
    list_filter = ('event_type', 'processed', 'created_at')
    search_fields = ('event_id', 'event_type')
    readonly_fields = ('event_id', 'event_type', 'event_data', 'payment', 'created_at', 'processed_at')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
