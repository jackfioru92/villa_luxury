from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import View
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.urls import reverse
import json
import logging

from apps.booking.models import Booking
from .models import Payment
from .services import StripeService
from .webhooks import WebhookHandler

logger = logging.getLogger(__name__)


class CreateCheckoutSessionView(View):
    """Create Stripe Checkout session and redirect."""

    def get(self, request, booking_id):
        """
        Create checkout session for a booking.
        Optionally accepts payment_type query param (deposit/balance/full).
        """
        booking = get_object_or_404(Booking, pk=booking_id)

        # Verify booking is in correct state
        if booking.status not in [Booking.Status.PENDING, Booking.Status.CONFIRMED]:
            messages.error(request, 'Questa prenotazione non può essere pagata.')
            return redirect('core:home')

        # Determine payment type
        payment_type = request.GET.get('type', Payment.PaymentType.DEPOSIT)
        if payment_type not in [Payment.PaymentType.DEPOSIT, Payment.PaymentType.BALANCE, Payment.PaymentType.FULL]:
            payment_type = Payment.PaymentType.DEPOSIT

        # Build URLs
        success_url = request.build_absolute_uri(
            reverse('payments:success')
        )
        cancel_url = request.build_absolute_uri(
            reverse('payments:cancel') + f'?booking={booking.booking_number}'
        )

        try:
            result = StripeService.create_checkout_session(
                booking=booking,
                success_url=success_url,
                cancel_url=cancel_url,
                payment_type=payment_type
            )
            return redirect(result['url'])

        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            messages.error(request, f'Errore nella creazione del pagamento: {str(e)}')
            return redirect('booking:wizard')


class CheckoutSuccessView(View):
    """Handle successful checkout redirect."""

    def get(self, request):
        session_id = request.GET.get('session_id')
        booking = None

        if session_id:
            try:
                session = StripeService.retrieve_session(session_id)
                booking_number = session.metadata.get('booking_number')
                if booking_number:
                    booking = Booking.objects.filter(booking_number=booking_number).first()
            except Exception as e:
                logger.error(f"Error retrieving checkout session: {str(e)}")

        return render(request, 'payments/success.html', {'booking': booking})


class CheckoutCancelView(View):
    """Handle cancelled checkout."""

    def get(self, request):
        booking_number = request.GET.get('booking')
        booking = (
            Booking.objects.filter(booking_number=booking_number).first()
            if booking_number else None
        )
        return render(request, 'payments/cancel.html', {'booking': booking})


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(View):
    """
    Stripe webhook endpoint.
    This is CRITICAL for booking confirmation.
    """

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not sig_header:
            logger.warning("Webhook received without signature")
            return HttpResponse(status=400)

        try:
            event = StripeService.construct_webhook_event(payload, sig_header)
        except ValueError as e:
            logger.error(f"Webhook signature verification failed: {str(e)}")
            return HttpResponse(status=400)

        # Process the event
        try:
            success = WebhookHandler.handle_event(event)
            if success:
                return HttpResponse(status=200)
            else:
                return HttpResponse(status=500)

        except Exception as e:
            logger.error(f"Webhook processing error: {str(e)}")
            # Return 200 to prevent Stripe from retrying
            # (we've logged the error and can handle manually)
            return HttpResponse(status=200)


class PaymentStatusView(View):
    """API endpoint to check payment status."""

    def get(self, request, booking_number):
        booking = get_object_or_404(Booking, booking_number=booking_number)

        # Verify access (user owns booking or knows the email)
        email = request.GET.get('email')
        if not request.user.is_authenticated:
            if not email or email.lower() != booking.guest_email.lower():
                return JsonResponse({'error': 'Unauthorized'}, status=403)

        latest_payment = booking.payments.order_by('-created_at').first()

        return JsonResponse({
            'booking_number': booking.booking_number,
            'booking_status': booking.status,
            'payment_status': booking.payment_status,
            'total_amount': str(booking.total_amount),
            'deposit_amount': str(booking.deposit_amount),
            'balance_due': str(booking.balance_due),
            'latest_payment': {
                'status': latest_payment.status if latest_payment else None,
                'amount': str(latest_payment.amount) if latest_payment else None,
                'type': latest_payment.payment_type if latest_payment else None,
            } if latest_payment else None
        })
