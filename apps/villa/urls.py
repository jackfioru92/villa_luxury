from django.urls import path
from . import views

app_name = 'villa'

urlpatterns = [
    path('', views.VillaListView.as_view(), name='list'),
    path('gallery/', views.GalleryView.as_view(), name='gallery'),
    path('<slug:slug>/', views.VillaDetailView.as_view(), name='detail'),
    path('<slug:villa_slug>/<slug:unit_slug>/', views.UnitDetailView.as_view(), name='unit_detail'),
]
