from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View, UpdateView
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm
from .forms_phone import PhoneOnlyForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

# View per richiedere il telefono dopo login social
@method_decorator(login_required, name='dispatch')
class PhoneRequiredView(View):
    template_name = 'accounts/phone_required.html'

    def get(self, request):
        if request.user.phone:
            return redirect('core:home')
        form = PhoneOnlyForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = PhoneOnlyForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _('Numero di telefono salvato!'))
            return redirect('core:home')
        return render(request, self.template_name, {'form': form})


from django.utils.deprecation import MiddlewareMixin

# Middleware per forzare inserimento telefono dopo login social
class PhoneRequiredMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated and hasattr(request.user, 'phone') and not request.user.phone:
            if request.path not in [reverse_lazy('accounts:phone_required'), reverse_lazy('accounts:logout')]:
                if request.session.pop('phone_required', False):
                    return redirect('accounts:phone_required')

                # Se già autenticato ma manca il telefono, forza la pagina
                if request.path != reverse_lazy('accounts:phone_required'):
                    return redirect('accounts:phone_required')

        return None

class CustomLoginView(LoginView):
    """Custom login view."""
    template_name = 'accounts/login.html'
    form_class = CustomAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        next_url = self.request.GET.get('next')
        if next_url:
            return next_url
        return reverse_lazy('core:home')

    def form_valid(self, form):
        messages.success(self.request, _('Benvenuto!'))
        return super().form_valid(form)


class CustomLogoutView(LogoutView):
    """Custom logout view."""
    next_page = reverse_lazy('core:home')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, _('Logout effettuato con successo.'))
        return super().dispatch(request, *args, **kwargs)


class RegisterView(View):
    """User registration view."""
    template_name = 'accounts/register.html'

    def get(self, request):
        if request.user.is_authenticated:
            return redirect('core:home')
        form = CustomUserCreationForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                _('Account creato con successo! Benvenuto.')
            )
            return redirect('core:home')
        return render(request, self.template_name, {'form': form})


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view."""
    template_name = 'accounts/profile.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bookings'] = self.request.user.get_bookings()[:5]
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Edit user profile."""
    model = CustomUser
    form_class = UserProfileForm
    template_name = 'accounts/profile_edit.html'
    success_url = reverse_lazy('accounts:profile')

    def get_object(self):
        return self.request.user

    def form_valid(self, form):
        messages.success(self.request, _('Profilo aggiornato con successo.'))
        return super().form_valid(form)


class MyBookingsView(LoginRequiredMixin, TemplateView):
    """User's bookings list."""
    template_name = 'accounts/my_bookings.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        bookings = self.request.user.get_bookings()
        
        # Split by status
        context['upcoming'] = [b for b in bookings if b.is_upcoming]
        context['current'] = [b for b in bookings if b.is_current]
        context['past'] = [b for b in bookings if b.is_past]
        context['all_bookings'] = bookings
        
        return context
