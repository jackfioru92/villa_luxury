from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    # Main booking pages
    path('', views.BookingWizardView.as_view(), name='wizard'),
    path('cerca/', views.BookingSearchView.as_view(), name='search'),
    path('conferma/<str:booking_number>/', views.BookingConfirmationView.as_view(), name='confirmation'),
    
    # HTMX endpoints
    path('htmx/calendar/', views.HTMXAvailabilityCalendarView.as_view(), name='htmx_calendar'),
    path('htmx/price/', views.HTMXPriceCalculationView.as_view(), name='htmx_price'),
    path('htmx/step/<int:step>/', views.HTMXBookingStepView.as_view(), name='htmx_step'),
    path('htmx/units/', views.HTMXUnitSelectView.as_view(), name='htmx_units'),
]
