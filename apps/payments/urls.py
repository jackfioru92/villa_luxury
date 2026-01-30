from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Checkout flow
    path('checkout/<uuid:booking_id>/', views.CreateCheckoutSessionView.as_view(), name='checkout'),
    path('success/', views.CheckoutSuccessView.as_view(), name='success'),
    path('cancel/', views.CheckoutCancelView.as_view(), name='cancel'),
    
    # Stripe webhook
    path('webhook/', views.StripeWebhookView.as_view(), name='webhook'),
    
    # Status check
    path('status/<str:booking_number>/', views.PaymentStatusView.as_view(), name='status'),
]
