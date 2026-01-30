"""
Stripe payment services.
"""
import stripe
from decimal import Decimal
from django.conf import settings
from django.urls import reverse
from apps.booking.models import Booking
from .models import Payment

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service for Stripe payment operations."""

    @staticmethod
    def create_checkout_session(
        booking: Booking,
        success_url: str,
        cancel_url: str,
        payment_type: str = Payment.PaymentType.DEPOSIT
    ) -> dict:
        """
        Create a Stripe Checkout Session for a booking.
        Returns the session object with URL for redirect.
        """
        # Determine amount to charge
        if payment_type == Payment.PaymentType.DEPOSIT:
            amount = booking.deposit_amount
            description = f"Acconto prenotazione {booking.booking_number}"
        elif payment_type == Payment.PaymentType.BALANCE:
            amount = booking.balance_due
            description = f"Saldo prenotazione {booking.booking_number}"
        else:
            amount = booking.total_amount
            description = f"Pagamento prenotazione {booking.booking_number}"

        # Convert to cents for Stripe
        amount_cents = int(amount * 100)

        # Create the checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': booking.currency.lower(),
                    'unit_amount': amount_cents,
                    'product_data': {
                        'name': f"{booking.unit.villa.name} - {booking.unit.name}",
                        'description': description,
                        'metadata': {
                            'booking_number': booking.booking_number,
                            'check_in': booking.check_in.isoformat(),
                            'check_out': booking.check_out.isoformat(),
                        }
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=cancel_url,
            customer_email=booking.guest_email,
            metadata={
                'booking_id': str(booking.id),
                'booking_number': booking.booking_number,
                'payment_type': payment_type,
            },
            # Billing address collection
            billing_address_collection='required',
            # Locale
            locale='it',
            # Expiration (30 minutes)
            expires_at=int((Decimal(30) * 60) + Decimal(stripe.time.time())),
        )

        # Create Payment record
        payment = Payment.objects.create(
            booking=booking,
            amount=amount,
            currency=booking.currency,
            payment_type=payment_type,
            status=Payment.Status.PENDING,
            stripe_checkout_session_id=session.id,
            customer_email=booking.guest_email
        )

        return {
            'session_id': session.id,
            'url': session.url,
            'payment_id': str(payment.id)
        }

    @staticmethod
    def retrieve_session(session_id: str) -> dict:
        """Retrieve a Checkout Session from Stripe."""
        return stripe.checkout.Session.retrieve(session_id)

    @staticmethod
    def retrieve_payment_intent(payment_intent_id: str) -> dict:
        """Retrieve a Payment Intent from Stripe."""
        return stripe.PaymentIntent.retrieve(payment_intent_id)

    @staticmethod
    def create_refund(payment: Payment, amount: Decimal = None, reason: str = '') -> dict:
        """
        Create a refund for a payment.
        If amount is None, refunds the full amount.
        """
        if not payment.stripe_payment_intent_id:
            raise ValueError("Payment has no associated Stripe Payment Intent")

        refund_params = {
            'payment_intent': payment.stripe_payment_intent_id,
            'reason': 'requested_by_customer',
            'metadata': {
                'booking_number': payment.booking.booking_number,
                'reason': reason
            }
        }

        if amount:
            refund_params['amount'] = int(amount * 100)

        refund = stripe.Refund.create(**refund_params)

        # Update payment status
        if amount and amount < payment.amount:
            payment.status = Payment.Status.REFUNDED
        else:
            payment.status = Payment.Status.REFUNDED
        payment.save()

        return {
            'refund_id': refund.id,
            'amount': Decimal(refund.amount) / 100,
            'status': refund.status
        }

    @staticmethod
    def construct_webhook_event(payload: bytes, sig_header: str) -> stripe.Event:
        """
        Construct and verify a webhook event from Stripe.
        Raises ValueError if verification fails.
        """
        webhook_secret = settings.STRIPE_WEBHOOK_SECRET

        if not webhook_secret:
            raise ValueError("Stripe webhook secret not configured")

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            raise ValueError(f"Invalid signature: {str(e)}")
        except Exception as e:
            raise ValueError(f"Webhook error: {str(e)}")
