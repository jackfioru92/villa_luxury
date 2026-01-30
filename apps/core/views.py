from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView, DetailView
from apps.villa.models import Villa, BookableUnit
from apps.core.models import Page, FAQ, Testimonial


class HomeView(TemplateView):
    """Home page view."""
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['villa'] = Villa.objects.filter(is_active=True).first()
        context['units'] = BookableUnit.objects.filter(is_active=True).order_by('sort_order')
        context['testimonials'] = Testimonial.objects.filter(is_active=True, is_featured=True)[:3]
        context['faqs'] = FAQ.objects.filter(is_active=True)[:5]
        return context


class PageDetailView(DetailView):
    """Generic page detail view."""
    model = Page
    template_name = 'core/page_detail.html'
    context_object_name = 'page'

    def get_queryset(self):
        return Page.objects.filter(is_published=True)


class ContactView(TemplateView):
    """Contact page view."""
    template_name = 'core/contact.html'


class PrivacyView(TemplateView):
    """Privacy policy page."""
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    """Terms and conditions page."""
    template_name = 'core/terms.html'
