from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('contatti/', views.ContactView.as_view(), name='contact'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('termini/', views.TermsView.as_view(), name='terms'),
    path('cookie-policy/', views.CookiePolicyView.as_view(), name='cookie_policy'),
    path('newsletter/subscribe/', views.NewsletterSubscribeView.as_view(), name='newsletter_subscribe'),
    path('pagina/<slug:slug>/', views.PageDetailView.as_view(), name='page_detail'),
    path('manutenzione/', views.MaintenanceView.as_view(), name='maintenance'),
]
