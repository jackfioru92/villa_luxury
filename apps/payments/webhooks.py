"""
Stripe webhook handlers.
"""
import logging
from django.utils import timezone
from apps.booking.models import Booking
from apps.booking.services import BookingService
from .models import Payment, PaymentLog

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handler for Stripe webhook events."""

    @staticmethod
    def handle_event(event) -> bool:
        """
        Process a Stripe webhook event.
        Returns True if handled successfully.
        """
        event_type = event['type']
        event_id = event['id']
        event_data = event['data']['object']

        # Check for idempotency (prevent double processing)
        if PaymentLog.objects.filter(event_id=event_id, processed=True).exists():
            logger.info(f"Event {event_id} already processed, skipping")
            return True

        # Create log entry
        log = PaymentLog.objects.create(
            event_id=event_id,
            event_type=event_type,
            event_data=event,
            processed=False
        )

        try:
            # Route to appropriate handler
            handler_map = {
                'checkout.session.completed': WebhookHandler._handle_checkout_completed,
                'checkout.session.expired': WebhookHandler._handle_checkout_expired,
                'payment_intent.succeeded': WebhookHandler._handle_payment_succeeded,
                'payment_intent.payment_failed': WebhookHandler._handle_payment_failed,
                'charge.refunded': WebhookHandler._handle_refund,
            }

            handler = handler_map.get(event_type)
            if handler:
                handler(event_data, log)
            else:
                logger.info(f"Unhandled event type: {event_type}")

            # Mark as processed
            log.processed = True
            log.processed_at = timezone.now()
            log.save()
            return True

        except Exception as e:
            logger.error(f"Error processing webhook {event_id}: {str(e)}")
            log.error_message = str(e)
            log.save()
            return False

    @staticmethod
    def _handle_checkout_completed(session_data: dict, log: PaymentLog):
        """
        Handle checkout.session.completed event.
        This is the PRIMARY confirmation point for bookings.
        """
        session_id = session_data['id']
        payment_intent_id = session_data.get('payment_intent')
        booking_id = session_data.get('metadata', {}).get('booking_id')
        payment_type = session_data.get('metadata', {}).get('payment_type', 'DEPOSIT')

        # Find the payment record
        payment = Payment.objects.filter(
            stripe_checkout_session_id=session_id
        ).first()

        if not payment:
            logger.error(f"Payment not found for session {session_id}")
            raise ValueError(f"Payment not found for session {session_id}")

        # Update payment record
        payment.stripe_payment_intent_id = payment_intent_id
        payment.status = Payment.Status.COMPLETED
        payment.completed_at = timezone.now()
        payment.save()

        # Link log to payment
        log.payment = payment
        log.save()

        # Get booking
        booking = payment.booking

        # Update booking payment status
        if payment_type == 'DEPOSIT':
            booking.payment_status = Booking.PaymentStatus.DEPOSIT_PAID
        elif payment_type == 'BALANCE':
            booking.payment_status = Booking.PaymentStatus.FULLY_PAID
        else:
            booking.payment_status = Booking.PaymentStatus.FULLY_PAID

        booking.save()

        # CONFIRM THE BOOKING - This is critical!
        # This creates the blocked dates and makes the reservation official
        if booking.status == Booking.Status.PENDING:
            try:
                BookingService.confirm_booking(booking)
                logger.info(f"Booking {booking.booking_number} confirmed successfully")
            except ValueError as e:
                # Date no longer available - this shouldn't happen but handle it
                logger.error(f"Could not confirm booking {booking.booking_number}: {str(e)}")
                # TODO: Trigger refund and notification
                raise

        # TODO: Send confirmation email
        logger.info(f"Payment completed for booking {booking.booking_number}")

    @staticmethod
    def _handle_checkout_expired(session_data: dict, log: PaymentLog):
        """Handle expired checkout session."""
        session_id = session_data['id']

        payment = Payment.objects.filter(
            stripe_checkout_session_id=session_id
        ).first()

        if payment:
            payment.status = Payment.Status.CANCELLED
            payment.save()
            log.payment = payment
            log.save()

            # Optionally cancel the pending booking
            booking = payment.booking
            if booking.status == Booking.Status.PENDING:
                # Don't auto-cancel, just leave as pending
                # The user might try again
                pass

            logger.info(f"Checkout expired for booking {booking.booking_number}")

    @staticmethod
    def _handle_payment_succeeded(intent_data: dict, log: PaymentLog):
        """Handle payment_intent.succeeded event."""
        payment_intent_id = intent_data['id']
        charge_id = intent_data.get('latest_charge')

        payment = Payment.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()

        if payment:
            payment.stripe_charge_id = charge_id or ''
            
            # Get receipt URL if available
            if charge_id:
                import stripe
                try:
                    charge = stripe.Charge.retrieve(charge_id)
                    payment.receipt_url = charge.receipt_url or ''
                except Exception:
                    pass
            
            payment.save()
            log.payment = payment
            log.save()

    @staticmethod
    def _handle_payment_failed(intent_data: dict, log: PaymentLog):
        """Handle payment_intent.payment_failed event."""
        payment_intent_id = intent_data['id']
        error = intent_data.get('last_payment_error', {})
        error_message = error.get('message', 'Pagamento fallito')

        payment = Payment.objects.filter(
            stripe_payment_intent_id=payment_intent_id
        ).first()

        if payment:
            payment.status = Payment.Status.FAILED
            payment.failed_at = timezone.now()
            payment.failure_reason = error_message
            payment.save()
            log.payment = payment
            log.save()

            logger.warning(
                f"Payment failed for booking {payment.booking.booking_number}: {error_message}"
            )

    @staticmethod
    def _handle_refund(charge_data: dict, log: PaymentLog):
        """Handle charge.refunded event."""
        charge_id = charge_data['id']
        refund_amount = charge_data.get('amount_refunded', 0)
        
        payment = Payment.objects.filter(
            stripe_charge_id=charge_id
        ).first()

        if payment:
            # Check if fully or partially refunded
            refund_decimal = refund_amount / 100
            if refund_decimal >= payment.amount:
                payment.status = Payment.Status.REFUNDED
                payment.booking.payment_status = Booking.PaymentStatus.REFUNDED
            else:
                payment.booking.payment_status = Booking.PaymentStatus.PARTIALLY_REFUNDED
            
            payment.save()
            payment.booking.save()
            log.payment = payment
            log.save()

            logger.info(f"Refund processed for booking {payment.booking.booking_number}")
