from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Booking


class BookingStep1Form(forms.Form):
    """Step 1: Select unit and dates."""
    unit = forms.UUIDField(widget=forms.HiddenInput())
    check_in = forms.DateField(
        label=_('Check-in'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        })
    )
    check_out = forms.DateField(
        label=_('Check-out'),
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input'
        })
    )
    num_guests = forms.IntegerField(
        label=_('Numero ospiti'),
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-input'
        })
    )


class BookingStep2Form(forms.Form):
    """Step 2: Guest information."""
    first_name = forms.CharField(
        label=_('Nome'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Mario'
        })
    )
    last_name = forms.CharField(
        label=_('Cognome'),
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Rossi'
        })
    )
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'mario.rossi@email.com'
        })
    )
    phone = forms.CharField(
        label=_('Telefono'),
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+39 333 1234567'
        })
    )
    country = forms.CharField(
        label=_('Paese'),
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Italia'
        })
    )
    notes = forms.CharField(
        label=_('Note o richieste speciali'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Eventuali richieste speciali...'
        })
    )
    arrival_time = forms.TimeField(
        label=_('Orario di arrivo previsto'),
        required=False,
        widget=forms.TimeInput(attrs={
            'type': 'time',
            'class': 'form-input'
        })
    )
    terms_accepted = forms.BooleanField(
        label=_('Accetto i termini e le condizioni'),
        required=True
    )
    privacy_accepted = forms.BooleanField(
        label=_('Accetto la privacy policy'),
        required=True
    )


class BookingSearchForm(forms.Form):
    """Form for searching a booking."""
    booking_number = forms.CharField(
        label=_('Numero prenotazione'),
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'VL-2026-XXXXX'
        })
    )
    email = forms.EmailField(
        label=_('Email'),
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'La tua email'
        })
    )
