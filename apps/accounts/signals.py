from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from django.shortcuts import redirect
from django.urls import reverse

@receiver(user_logged_in)
def check_phone_on_login(request, user, **kwargs):
    if not user.phone:
        request.session['phone_required'] = True
