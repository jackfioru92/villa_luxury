"""
Test del prezziario: i periodi non devono mai sovrapporsi né lasciare buchi,
perché il prezzo di una data si risolve prendendo il primo periodo per data di
inizio. Un periodo speciale contenuto in una fascia di base non verrebbe mai
applicato, e un buco farebbe ricadere la notte sul base_price.
"""
from datetime import date, timedelta

from django.core.management import call_command
from django.test import TestCase

from apps.booking.services import PricingService
from apps.villa.management.commands.update_pricing import build_periods, easter_week
from apps.villa.models import BookableUnit, Villa


class PeriodBuildingTests(TestCase):

    def test_periods_never_overlap_or_leave_gaps(self):
        for year in range(2026, 2036):
            periods = build_periods(year)
            for (_, _, end, _), (_, start, _, _) in zip(periods, periods[1:]):
                self.assertEqual(
                    (start - end).days, 1,
                    f'{year}: discontinuità tra {end} e {start}',
                )

    def test_year_is_covered_from_january_7_to_january_6(self):
        periods = build_periods(2027)
        self.assertEqual(periods[0][1], date(2027, 1, 7))
        self.assertEqual(periods[-1][2], date(2028, 1, 6))

    def test_easter_week_is_seven_nights_ending_on_easter_monday(self):
        for year, sunday in [(2026, date(2026, 4, 5)), (2027, date(2027, 3, 28)),
                             (2029, date(2029, 4, 1)), (2030, date(2030, 4, 21))]:
            start, end = easter_week(year)
            self.assertEqual(end, sunday + timedelta(days=1), f'{year}: pasquetta')
            self.assertEqual((end - start).days + 1, 7, f'{year}: notti')

    def test_easter_week_is_carved_out_whatever_month_it_falls_in(self):
        # 2027 Pasqua è il 28 marzo (dentro la fascia Novembre-Marzo),
        # 2028 il 16 aprile (dentro Aprile-Maggio)
        for year in (2027, 2028, 2029, 2030):
            start, end = easter_week(year)
            labels = {
                label for label, p_start, p_end, _ in build_periods(year)
                if p_start <= start and p_end >= end
            }
            self.assertEqual(labels, {'Settimana di Pasqua'}, year)

    def test_ferragosto_week_runs_from_the_9th_to_the_15th(self):
        periods = {label: (start, end) for label, start, end, _ in build_periods(2027)
                   if label == 'Settimana di Ferragosto'}
        self.assertEqual(periods['Settimana di Ferragosto'], (date(2027, 8, 9), date(2027, 8, 15)))

    def test_christmas_period_spans_the_year_boundary(self):
        xmas = [p for p in build_periods(2027) if p[0] == 'Natale e Capodanno']
        self.assertEqual(len(xmas), 1)
        self.assertEqual(xmas[0][1], date(2027, 12, 8))
        self.assertEqual(xmas[0][2], date(2028, 1, 6))


class AppliedPricingTests(TestCase):

    def setUp(self):
        villa = Villa.objects.create(
            name='Altesia', slug='altesia', description='x',
            address='x', city='Perugia', province='PG', postal_code='06134',
        )
        common = dict(villa=villa, description='x', min_nights=2)
        self.full = BookableUnit.objects.create(
            name='All Structure', slug='intera-villa', unit_type='FULL',
            max_guests=8, base_price=640, sort_order=1, **common
        )
        self.suite = BookableUnit.objects.create(
            name='Suite Aura', slug='suite-aura', unit_type='ROOM',
            max_guests=4, base_price=275, sort_order=2, is_bookable=False, **common
        )
        self.suite.season_prices.create(
            name='Vecchia tariffa', start_date=date(2027, 7, 1),
            end_date=date(2027, 7, 31), price_per_night=450,
        )
        call_command('update_pricing', years=[2027], verbosity=0)
        self.full.refresh_from_db()

    def price_on(self, day):
        return int(PricingService.get_price_for_date(self.full, day))

    def season_on(self, day):
        return PricingService.get_season_for_date(self.full, day)

    def test_boundaries_switch_on_the_right_night(self):
        cases = [
            (date(2027, 1, 6), 1600, 'Natale e Capodanno'),
            (date(2027, 1, 7), 1000, 'Novembre - Marzo'),
            (date(2027, 3, 22), 1000, 'Novembre - Marzo'),
            (date(2027, 3, 23), 1500, 'Settimana di Pasqua'),
            (date(2027, 3, 29), 1500, 'Settimana di Pasqua'),
            (date(2027, 3, 30), 1000, 'Novembre - Marzo'),
            (date(2027, 8, 8), 1500, 'Agosto'),
            (date(2027, 8, 9), 1700, 'Settimana di Ferragosto'),
            (date(2027, 8, 15), 1700, 'Settimana di Ferragosto'),
            (date(2027, 8, 16), 1500, 'Agosto'),
            (date(2027, 12, 7), 1000, 'Novembre - Marzo'),
            (date(2027, 12, 8), 1600, 'Natale e Capodanno'),
        ]
        for day, price, season in cases:
            self.assertEqual((self.price_on(day), self.season_on(day)), (price, season), day)

    def test_stay_across_ferragosto_is_billed_night_by_night(self):
        pricing = PricingService.calculate_booking_price(
            self.full, date(2027, 8, 13), date(2027, 8, 17), 8
        )
        self.assertEqual(pricing['subtotal'], 1700 * 3 + 1500)

    def test_base_price_follows_the_lowest_tariff(self):
        self.assertEqual(int(self.full.base_price), 1000)

    def test_new_year_nights_keep_the_holiday_tariff(self):
        # il periodo festivo nasce l'8 dicembre dell'anno prima: generando solo
        # il 2027 le notti fino al 6 gennaio devono restare a tariffa festiva
        for day in (date(2027, 1, 1), date(2027, 1, 6)):
            self.assertEqual((self.price_on(day), self.season_on(day)),
                             (1600, 'Natale e Capodanno'), day)

    def test_non_bookable_units_lose_their_prices(self):
        self.assertEqual(self.suite.season_prices.count(), 0)
