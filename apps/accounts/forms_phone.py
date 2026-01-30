from django import forms
from .models import CustomUser

class PhoneOnlyForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['phone']
        widgets = {
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '+39 333 1234567',
                'autocomplete': 'tel',
            })
        }
        labels = {
            'phone': 'Numero di telefono',
        }