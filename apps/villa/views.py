from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, ListView, TemplateView
from .models import Villa, BookableUnit, GalleryImage


class VillaListView(ListView):
    """Villa list/overview page."""
    model = Villa
    template_name = 'villa/villa_list.html'
    context_object_name = 'villas'

    def get_queryset(self):
        return Villa.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Se c'è una sola villa, mostra tutte le unità
        villas = self.get_queryset()
        if villas.count() == 1:
            villa = villas.first()
            context['villa'] = villa
            context['units'] = villa.units.filter(is_active=True)
            context['gallery'] = villa.gallery_images.all()[:12]
        return context


class VillaDetailView(DetailView):
    """Villa detail page."""
    model = Villa
    template_name = 'villa/villa_detail.html'
    context_object_name = 'villa'

    def get_queryset(self):
        return Villa.objects.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['units'] = self.object.units.filter(is_active=True)
        context['gallery'] = self.object.gallery_images.all()[:12]
        return context


class UnitDetailView(DetailView):
    """Bookable unit detail page."""
    model = BookableUnit
    template_name = 'villa/unit_detail.html'
    context_object_name = 'unit'
    slug_url_kwarg = 'unit_slug'

    def get_queryset(self):
        return BookableUnit.objects.filter(
            is_active=True,
            villa__slug=self.kwargs['villa_slug']
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['gallery'] = self.object.gallery_images.all()[:12]
        context['other_units'] = self.object.villa.units.filter(
            is_active=True
        ).exclude(pk=self.object.pk)
        return context


class GalleryView(ListView):
    """Full gallery page."""
    model = GalleryImage
    template_name = 'villa/gallery.html'
    context_object_name = 'images'
    paginate_by = 24

    def get_queryset(self):
        return GalleryImage.objects.filter(villa__is_active=True)
