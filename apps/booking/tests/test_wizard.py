"""
Test del wizard di prenotazione.

Con una sola sistemazione prenotabile il passo di scelta non ha senso e va
saltato; il prezzo si vede solo nel riepilogo finale; le esperienze scelte
devono arrivare fino alla prenotazione salvata.
"""
import json
import re
from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse

from apps.booking.models import Booking
from apps.villa.models import BookableUnit, Villa


class WizardStepsTests(TestCase):

    def setUp(self):
        self.villa = Villa.objects.create(
            name='Altesia', slug='altesia', description='x',
            address='x', city='Perugia', province='PG', postal_code='06134',
        )
        self.full = BookableUnit.objects.create(
            villa=self.villa, name='All Structure', slug='intera-villa',
            unit_type='FULL', description='x', max_guests=8,
            base_price=1000, min_nights=2, sort_order=1,
        )
        self.suite = BookableUnit.objects.create(
            villa=self.villa, name='Suite Aura', slug='suite-aura',
            unit_type='ROOM', description='x', max_guests=4,
            base_price=275, min_nights=2, sort_order=2, is_bookable=False,
        )

    def wizard(self):
        return self.client.get(reverse('booking:wizard'))

    def test_single_unit_is_preselected_and_choice_step_removed(self):
        response = self.wizard()

        self.assertFalse(response.context['multiple_units'])
        self.assertEqual(response.context['selected_unit'], self.full)
        body = response.content.decode()
        self.assertNotIn('Seleziona la Sistemazione', body)
        self.assertIn("firstStep: 2", body)
        self.assertIn("currentStep: 2", body)

    def test_choice_step_comes_back_with_more_bookable_units(self):
        self.suite.is_bookable = True
        self.suite.save()

        response = self.wizard()

        self.assertTrue(response.context['multiple_units'])
        self.assertIn('Seleziona la Sistemazione', response.content.decode())

    def test_non_bookable_units_never_reach_the_wizard(self):
        body = self.wizard().content.decode()
        self.assertNotIn('Suite Aura', body)

    def test_price_block_lives_in_the_final_step_only(self):
        body = self.wizard().content.decode()

        self.assertEqual(body.count('id="price-summary"'), 1)
        # il riquadro sta dopo l'intestazione del riepilogo, non nello step date
        self.assertLess(body.index('Riepilogo e Pagamento'), body.index('id="price-summary"'))
        self.assertNotIn('Seleziona le date per vedere il prezzo', body)

    def test_alpine_state_contains_only_valid_js_numbers(self):
        """
        Con LANGUAGE_CODE='it' Django scrive i decimali con la virgola:
        `basePrice: 1000,00` è un SyntaxError che azzera tutto il wizard,
        bottone di prenotazione compreso.
        """
        body = self.wizard().content.decode()
        script = body[body.index('function bookingWizard'):]
        script = script[:script.index('</script>')]

        for name in ('basePrice', 'minNights', 'maxGuests', 'firstStep', 'currentStep'):
            line = re.search(rf'^\s*{name}:\s*(.*)$', script, re.MULTILINE).group(1)
            value = line.rstrip(',').strip()
            self.assertRegex(
                value, r'^\d+(\.\d+)?$',
                f'{name} non è un numero JS valido: {value!r}',
            )

    def test_unit_name_is_escaped_for_javascript(self):
        self.full.name = "L'Intera Struttura"
        self.full.save()

        body = self.wizard().content.decode()
        line = re.search(r'^\s*selectedUnitName:\s*(.*)$', body, re.MULTILINE).group(1)

        self.assertNotIn("'L'Intera", line)

    def test_experience_checkboxes_follow_the_notes_field(self):
        body = self.wizard().content.decode()

        self.assertLess(body.index('name="notes"'), body.index('selectedExperiences'))
        for experience in ('Chef Privato', 'Massaggi &amp; Benessere', 'Golf &amp; Tennis'):
            self.assertIn(experience, body)


class BookingCreationTests(TestCase):

    def setUp(self):
        villa = Villa.objects.create(
            name='Altesia', slug='altesia', description='x',
            address='x', city='Perugia', province='PG', postal_code='06134',
        )
        self.full = BookableUnit.objects.create(
            villa=villa, name='All Structure', slug='intera-villa',
            unit_type='FULL', description='x', max_guests=8,
            base_price=1000, min_nights=2, sort_order=1,
        )
        self.full.season_prices.create(
            name='Test', start_date=date.today(),
            end_date=date.today() + timedelta(days=365), price_per_night=1000,
        )

    def payload(self, **overrides):
        check_in = date.today() + timedelta(days=30)
        data = {
            'unit': str(self.full.id),
            'check_in': check_in.isoformat(),
            'check_out': (check_in + timedelta(days=3)).isoformat(),
            'num_guests': 6,
            'first_name': 'Mario', 'last_name': 'Rossi',
            'email': 'mario@example.com', 'phone': '+39 333 1234567',
            'notes': 'Arriviamo tardi',
            'terms_accepted': True, 'privacy_accepted': True,
        }
        data.update(overrides)
        return data

    def create(self, **overrides):
        return self.client.post(
            reverse('booking:api_create'),
            data=json.dumps(self.payload(**overrides)),
            content_type='application/json',
        )

    def test_selected_experiences_are_stored_on_the_booking(self):
        response = self.create(experiences=['Chef Privato', 'Golf & Tennis'])

        self.assertEqual(response.status_code, 200, response.content)
        booking = Booking.objects.get()
        self.assertEqual(booking.experiences, 'Chef Privato, Golf & Tennis')
        self.assertEqual(booking.experiences_list, ['Chef Privato', 'Golf & Tennis'])

    def test_experiences_are_optional(self):
        self.assertEqual(self.create().status_code, 200)
        self.assertEqual(Booking.objects.get().experiences, '')
        self.assertEqual(Booking.objects.get().experiences_list, [])

    def test_notes_still_saved_alongside_experiences(self):
        self.create(experiences=['Chef Privato'])
        booking = Booking.objects.get()
        self.assertEqual(booking.guest_notes, 'Arriviamo tardi')


class PriceSummaryTests(TestCase):
    """
    Il riquadro prezzo è HTMX: la vista deve passare al partial le chiavi che
    il partial legge davvero, altrimenti il riepilogo finale mostra "Acconto
    €0" pur avendo calcolato il prezzo correttamente.
    """

    def setUp(self):
        villa = Villa.objects.create(
            name='Altesia', slug='altesia', description='x',
            address='x', city='Perugia', province='PG', postal_code='06134',
        )
        self.full = BookableUnit.objects.create(
            villa=villa, name='All Structure', slug='intera-villa',
            unit_type='FULL', description='x', max_guests=8,
            base_price=1000, cleaning_fee=0, min_nights=3, sort_order=1,
        )
        self.check_in = date.today() + timedelta(days=60)
        self.check_out = self.check_in + timedelta(days=4)
        self.full.season_prices.create(
            name='Test', start_date=self.check_in,
            end_date=self.check_out, price_per_night=1000,
        )

    def price_summary(self, **overrides):
        params = {
            'unit': str(self.full.id),
            'check_in': self.check_in.isoformat(),
            'check_out': self.check_out.isoformat(),
            'num_guests': 4,
        }
        params.update(overrides)
        return self.client.get(reverse('booking:htmx_price'), params)

    def test_valid_dates_return_the_actual_price(self):
        body = self.price_summary().content.decode()

        self.assertIn('Riepilogo Prezzo', body)
        self.assertNotIn('Seleziona le date per vedere il prezzo', body)
        self.assertIn('4 notti', body)
        self.assertIn('€4000', body)       # 4 notti x 1000
        self.assertIn('€1200', body)       # acconto 30%

    def test_alpine_state_is_updated_on_the_wizard_not_the_navbar(self):
        body = self.price_summary().content.decode()

        self.assertIn("getElementById('booking-wizard')", body)
        self.assertNotIn("querySelector('[x-data]')", body)

    def test_amounts_written_into_javascript_are_valid_numbers(self):
        body = self.price_summary().content.decode()

        for name in ('totalAmount', 'depositAmount'):
            value = re.search(rf'{name} = (.*);', body).group(1)
            self.assertRegex(value, r'^\d+(\.\d+)?$', f'{name}: {value!r}')

    def test_wizard_page_exposes_the_id_the_partial_targets(self):
        body = self.client.get(reverse('booking:wizard')).content.decode()
        self.assertIn('id="booking-wizard"', body)

    def test_blocked_dates_are_reported_instead_of_a_price(self):
        from apps.booking.models import BlockedDate
        BlockedDate.objects.create(unit=self.full, date=self.check_in)

        body = self.price_summary().content.decode()

        self.assertIn('non sono disponibili', body)
        self.assertNotIn('Riepilogo Prezzo', body)

    def test_too_short_a_stay_is_reported(self):
        body = self.price_summary(
            check_out=(self.check_in + timedelta(days=1)).isoformat()
        ).content.decode()

        self.assertIn('minimo', body.lower())
