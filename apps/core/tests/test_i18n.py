"""Test del multilingua: prefissi URL, cambio lingua, endpoint esenti."""
from django.test import TestCase
from django.urls import reverse
from django.utils import translation


class LanguagePrefixTests(TestCase):
    """L'italiano resta sulle URL attuali, l'inglese vive sotto /en/."""

    def test_italian_urls_have_no_prefix(self):
        with translation.override('it'):
            self.assertEqual(reverse('core:home'), '/')
            self.assertEqual(reverse('villa:list'), '/villa/')
            self.assertEqual(reverse('booking:wizard'), '/prenota/')

    def test_english_urls_are_prefixed(self):
        with translation.override('en'):
            self.assertEqual(reverse('core:home'), '/en/')
            self.assertEqual(reverse('villa:list'), '/en/villa/')
            self.assertEqual(reverse('booking:wizard'), '/en/prenota/')

    def test_both_versions_of_the_public_pages_respond(self):
        for path in ('/', '/en/', '/villa/', '/en/villa/', '/contatti/', '/en/contatti/',
                     '/privacy/', '/en/privacy/', '/termini/', '/en/termini/',
                     '/cookie-policy/', '/en/cookie-policy/'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)

    def test_html_lang_attribute_follows_the_url(self):
        self.assertContains(self.client.get('/'), '<html lang="it"')
        self.assertContains(self.client.get('/en/'), '<html lang="en"')

    def test_english_page_is_actually_translated(self):
        response = self.client.get('/en/contatti/')
        self.assertContains(response, 'Send us a message')
        self.assertNotContains(response, 'Scrivici un messaggio')


class MachineEndpointsTests(TestCase):
    """Gli endpoint chiamati da sistemi esterni non prendono il prefisso."""

    def test_ical_feed_url_is_identical_in_every_language(self):
        kwargs = {'unit_slug': 'aura', 'token': 'abc123'}
        with translation.override('it'):
            italian = reverse('calendar_feed', kwargs=kwargs)
        with translation.override('en'):
            english = reverse('calendar_feed', kwargs=kwargs)
        self.assertEqual(italian, english)
        self.assertEqual(italian, '/calendario/aura/abc123.ics')

    def test_google_oauth_callback_is_identical_in_every_language(self):
        # Il redirect_uri è registrato sulla Google Cloud Console: non può cambiare.
        with translation.override('it'):
            italian = reverse('google_callback')
        with translation.override('en'):
            english = reverse('google_callback')
        self.assertEqual(italian, english)

    def test_email_verification_links_already_sent_keep_working(self):
        # I link nelle email partite prima del multilingua sono senza prefisso:
        # l'italiano non ne ha, quindi continuano a risolvere.
        self.assertEqual(self.client.get('/account/email/verify/abc/').status_code, 200)
        self.assertEqual(self.client.get('/account/email/verify/').status_code, 200)

    def test_email_verification_link_follows_the_language(self):
        with translation.override('en'):
            self.assertEqual(reverse('account_confirm_email', kwargs={'key': 'abc'}),
                             '/en/account/email/verify/abc/')
        with translation.override('it'):
            self.assertEqual(reverse('account_confirm_email', kwargs={'key': 'abc'}),
                             '/account/email/verify/abc/')

    def test_stripe_webhook_answers_on_the_unprefixed_url(self):
        # Stripe chiama l'URL configurato sul dashboard, senza prefisso.
        response = self.client.post('/payment/webhook/', data='{}',
                                    content_type='application/json')
        self.assertNotEqual(response.status_code, 404)


class SetLanguageTests(TestCase):
    """Il selettore con le bandierine porta sulla stessa pagina nell'altra lingua."""

    def test_switch_from_italian_to_english(self):
        response = self.client.post('/i18n/setlang/',
                                    {'language': 'en', 'next': '/contatti/'})
        self.assertRedirects(response, '/en/contatti/', fetch_redirect_response=False)

    def test_switch_from_english_back_to_italian(self):
        response = self.client.post('/en/i18n/setlang/',
                                    {'language': 'it', 'next': '/en/contatti/'})
        self.assertRedirects(response, '/contatti/', fetch_redirect_response=False)

    def test_switch_keeps_the_query_string(self):
        response = self.client.post('/i18n/setlang/',
                                    {'language': 'en', 'next': '/prenota/?unit=aura'})
        self.assertRedirects(response, '/en/prenota/?unit=aura',
                             fetch_redirect_response=False)

    def test_switcher_is_rendered_with_both_flags(self):
        response = self.client.get('/')
        self.assertContains(response, 'name="language" value="it"')
        self.assertContains(response, 'name="language" value="en"')
        self.assertContains(response, '#009246')  # verde della bandiera italiana
        self.assertContains(response, '#012169')  # blu della Union Jack

    def test_page_declares_the_alternate_language_versions(self):
        response = self.client.get('/')
        self.assertContains(response, 'hreflang="it"')
        self.assertContains(response, 'hreflang="en"')
        self.assertContains(response, 'hreflang="x-default"')


class BookingLanguageTests(TestCase):
    """La lingua dell'ospite va salvata: l'email di conferma parte dal webhook."""

    def setUp(self):
        from apps.villa.models import BookableUnit, Villa
        self.villa = Villa.objects.create(
            name='Altesia', slug='altesia', description='x',
            address='x', city='Perugia', province='PG', postal_code='06134',
        )
        self.unit = BookableUnit.objects.create(
            villa=self.villa, name='All Structure', slug='intera-villa',
            unit_type='FULL', description='x', max_guests=8,
            base_price=1000, min_nights=2, sort_order=1,
        )

    def create_booking(self, url):
        import json
        from datetime import date, timedelta
        check_in = date.today() + timedelta(days=30)
        payload = {
            'unit': str(self.unit.id),
            'check_in': check_in.isoformat(),
            'check_out': (check_in + timedelta(days=3)).isoformat(),
            'num_guests': 2,
            'first_name': 'John', 'last_name': 'Smith',
            'email': 'john@example.com', 'phone': '+44 7700 900000',
            'terms_accepted': True, 'privacy_accepted': True,
        }
        return self.client.post(url, data=json.dumps(payload),
                                content_type='application/json')

    def test_booking_from_the_italian_site_is_stored_as_italian(self):
        from apps.booking.models import Booking
        response = self.create_booking('/prenota/api/create/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Booking.objects.get().language, 'it')

    def test_booking_from_the_english_site_is_stored_as_english(self):
        from apps.booking.models import Booking
        response = self.create_booking('/en/prenota/api/create/')
        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Booking.objects.get().language, 'en')


class PhoneRequiredMiddlewareTests(TestCase):
    """Le URL esenti vanno riconosciute anche con il prefisso di lingua."""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.user = User.objects.create_user(email='no-phone@example.com',
                                             password='test-pass-123')
        self.user.phone = ''
        self.user.save()
        self.client.force_login(self.user)

    def test_italian_exempt_url_is_served(self):
        self.assertEqual(self.client.get('/account/phone-required/').status_code, 200)

    def test_english_exempt_url_is_served_without_a_redirect_loop(self):
        response = self.client.get('/en/account/phone-required/')
        self.assertEqual(response.status_code, 200)

    def test_other_english_pages_still_redirect_to_the_phone_form(self):
        response = self.client.get('/en/prenota/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('phone-required', response['Location'])
