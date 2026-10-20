"""
Le pagine pubbliche non devono mostrare tariffe: il prezzo si vede solo nel
riepilogo finale della prenotazione, dopo aver scelto le date. Le tariffe
variano molto per periodo (1.000-1.700 €/notte) e un "da 1.000 €" in vetrina
è fuorviante.
"""
from django.test import TestCase
from django.urls import reverse

from apps.villa.models import BookableUnit, Villa


class NoPricesOnPublicPagesTests(TestCase):

    def setUp(self):
        self.villa = Villa.objects.create(
            name='Altèsia', slug='altesia', description='Villa di lusso',
            description_short='Villa', address='x', city='Perugia',
            province='PG', postal_code='06134',
        )
        common = dict(villa=self.villa, description='Descrizione',
                      description_short='Breve', min_nights=3, bedrooms=2, bathrooms=2)
        self.full = BookableUnit.objects.create(
            name='All Structure', slug='intera-villa', unit_type='FULL',
            max_guests=8, base_price=1000, sort_order=1, **common
        )
        self.suite = BookableUnit.objects.create(
            name='Suite Aura', slug='suite-aura', unit_type='ROOM',
            max_guests=4, base_price=275, sort_order=2, is_bookable=False, **common
        )

    def pages(self):
        return {
            'home': reverse('core:home'),
            'elenco ville': reverse('villa:list'),
            'dettaglio villa': self.villa.get_absolute_url(),
            'unità prenotabile': self.full.get_absolute_url(),
            'suite non prenotabile': self.suite.get_absolute_url(),
        }

    def test_no_page_shows_a_nightly_rate(self):
        for label, url in self.pages().items():
            with self.subTest(pagina=label):
                body = self.client.get(url).content.decode()
                self.assertNotIn('€', body, f'{label} mostra una tariffa')
                self.assertNotIn('1000', body, f'{label} mostra il prezzo base')

    def test_breakfast_is_still_mentioned(self):
        for label, url in self.pages().items():
            with self.subTest(pagina=label):
                body = self.client.get(url).content.decode().lower()
                self.assertIn('colazione inclusa', body, label)

    def test_unit_pages_still_lead_to_the_booking_flow(self):
        for unit in (self.full, self.suite):
            with self.subTest(unita=unit.name):
                body = self.client.get(unit.get_absolute_url()).content.decode()
                self.assertIn(reverse('booking:wizard'), body)
                self.assertIn('Verifica Disponibilità', body)
