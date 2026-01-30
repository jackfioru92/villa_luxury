from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.DashboardOverviewView.as_view(), name='overview'),
    path('prenotazioni/', views.BookingListView.as_view(), name='booking_list'),
    path('prenotazioni/<uuid:pk>/', views.BookingDetailView.as_view(), name='booking_detail'),
    path('calendario/', views.CalendarView.as_view(), name='calendar'),
    path('calendario/events/', views.CalendarEventsAPIView.as_view(), name='calendar_events'),
    path('blocchi/', views.BlockDatesView.as_view(), name='block_dates'),
    path('report/', views.ReportsView.as_view(), name='reports'),
]
