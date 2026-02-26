from django.shortcuts import render, redirect
from django.views.generic import TemplateView, View, UpdateView
from django.contrib.auth import login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
from .forms import CustomUserCreationForm, CustomAuthenticationForm, UserProfileForm
from .forms_phone import PhoneOnlyForm
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from allauth.account.models import EmailAddress

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
    """Redirect authenticated users without phone to phone_required page."""
    
    EXEMPT_URLS = [
        '/account/phone-required/',
        '/account/logout/',
        '/account/login/',
        '/account/register/',
        '/account/email/',    # email verification URLs
        '/accounts/',         # allauth URLs
        '/admin/',
        '/static/',
        '/media/',
    ]

    def process_request(self, request):
        if not request.user.is_authenticated:
            return None
        
        # Skip if user already has phone
        if getattr(request.user, 'phone', None):
            return None
        
        # Skip staff/admin users
        if request.user.is_staff:
            return None
        
        # Skip exempt URLs
        for url in self.EXEMPT_URLS:
            if request.path.startswith(url):
                return None
        
        return redirect('accounts:phone_required')

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
        user = form.get_user()
        # Controlla se l'email è verificata
        try:
            email_address = EmailAddress.objects.get(user=user, email=user.email)
            if not email_address.verified:
                messages.warning(
                    self.request,
                    _('Devi verificare la tua email prima di accedere. Controlla la tua casella di posta.')
                )
                return redirect('accounts:email_verification_sent')
        except EmailAddress.DoesNotExist:
            pass  # Utenti creati prima della verifica o admin
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
            # Crea EmailAddress e invia email di verifica tramite allauth
            email_address, created = EmailAddress.objects.get_or_create(
                user=user,
                email=user.email,
                defaults={'primary': True, 'verified': False}
            )
            email_address.send_confirmation(request, signup=True)
            messages.success(
                request,
                _('Account creato! Ti abbiamo inviato un\'email di verifica. Controlla la tua casella di posta.')
            )
            return redirect('accounts:email_verification_sent')
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


# ── Email Verification Views ──────────────────────────────────────

class EmailVerificationSentView(TemplateView):
    """Pagina mostrata dopo la registrazione: 'Controlla la tua email'."""
    template_name = 'accounts/email_verification_sent.html'


from allauth.account.views import ConfirmEmailView as AllauthConfirmEmailView

class CustomConfirmEmailView(AllauthConfirmEmailView):
    """Conferma email cliccando il link nella mail."""
    template_name = 'accounts/email_confirm.html'

    def get(self, *args, **kwargs):
        """Con ACCOUNT_CONFIRM_EMAIL_ON_GET=True, conferma automaticamente al click."""
        response = super().get(*args, **kwargs)
        return response

    def get_redirect_url(self):
        messages.success(self.request, _('Email verificata con successo! Ora puoi accedere.'))
        return reverse('accounts:login')


class ResendVerificationEmailView(View):
    """Rinvia l'email di verifica."""

    def post(self, request):
        email = request.POST.get('email', '').strip()
        if email:
            try:
                email_address = EmailAddress.objects.get(email=email, verified=False)
                email_address.send_confirmation(request, signup=False)
                messages.success(request, _('Email di verifica inviata! Controlla la tua casella di posta.'))
            except EmailAddress.DoesNotExist:
                # Non rivelare se l'email esiste o meno
                messages.success(request, _('Se l\'indirizzo è registrato, riceverai un\'email di verifica.'))
        else:
            messages.error(request, _('Inserisci un indirizzo email.'))
        return redirect('accounts:email_verification_sent')

    def get(self, request):
        return render(request, 'accounts/email_verification_sent.html', {'show_resend_form': True})
