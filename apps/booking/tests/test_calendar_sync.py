"""
Test della sincronizzazione calendari con i portali esterni.

Un errore qui si traduce in un overbooking su una struttura da 600-1300 €/notte,
quindi si testano esplicitamente i confini (check-out, DTEND esclusivo) e il
comportamento in caso di feed irraggiungibile.
"""
from datetime import date, timedelta
from unittest import mock

from django.test import TestCase

from apps.booking import calendar_sync
from apps.booking.models import BlockedDate, Booking, CalendarFeed
from apps.booking.services import AvailabilityService
from apps.villa.models import BookableUnit, Villa


def ics(events):
    body = ''.join(
        f'BEGIN:VEVENT\nUID:{uid}\n'
        f'DTSTART;VALUE=DATE:{start:%Y%m%d}\nDTEND;VALUE=DATE:{end:%Y%m%d}\n'
        f'SUMMARY:CLOSED - Not available\nEND:VEVENT\n'
        for uid, start, end in events
    )
    return f'BEGIN:VCALENDAR\nVERSION:2.0\nPRODID:-//Test//EN\n{body}END:VCALENDAR\n'


class CalendarSyncTests(TestCase):

    def setUp(self):
        villa = Villa.objects.create(
            name='Altesia', slug='altesia', description='x',
            address='x', city='Perugia', province='PG', postal_code='06134',
        )
        common = dict(villa=villa, description='x', min_nights=2)
        self.full = BookableUnit.objects.create(
            name='All Structure', slug='all-structure', unit_type='FULL',
            max_guests=8, base_price=640, sort_order=1, **common
        )
        self.aura = BookableUnit.objects.create(
            name='Suite Aura', slug='suite-aura', unit_type='ROOM',
            max_guests=4, base_price=275, sort_order=2, **common
        )
        self.silva = BookableUnit.objects.create(
            name='Suite Silva', slug='suite-silva', unit_type='ROOM',
            max_guests=4, base_price=275, sort_order=3, **common
        )
        self.full.conflicts_with.add(self.aura, self.silva)

        self.start = date.today() + timedelta(days=30)
        self.end = self.start + timedelta(days=4)

    def book(self, unit):
        booking = Booking.objects.create(
            unit=unit, guest_first_name='Mario', guest_last_name='Rossi',
            guest_email='mario@example.com', guest_phone='+39 000',
            check_in=self.start, check_out=self.end, num_guests=2, nights=4,
        )
        booking.confirm()
        return booking

    # -- disponibilità tra unità che condividono lo spazio -------------------

    def test_suite_booking_blocks_whole_villa_but_not_the_other_suite(self):
        self.book(self.aura)

        self.assertFalse(AvailabilityService.is_range_available(self.aura, self.start, self.end))
        self.assertFalse(AvailabilityService.is_range_available(self.full, self.start, self.end))
        self.assertTrue(AvailabilityService.is_range_available(self.silva, self.start, self.end))

    def test_whole_villa_booking_blocks_every_suite(self):
        self.book(self.full)

        self.assertFalse(AvailabilityService.is_range_available(self.aura, self.start, self.end))
        self.assertFalse(AvailabilityService.is_range_available(self.silva, self.start, self.end))

    def test_checkout_day_stays_available(self):
        self.book(self.full)
        self.assertTrue(AvailabilityService.is_date_available(self.full, self.end))

    def test_cancelling_frees_the_conflicting_units(self):
        booking = self.book(self.aura)
        booking.cancel('test')
        self.assertTrue(AvailabilityService.is_range_available(self.full, self.start, self.end))

    # -- export ---------------------------------------------------------------

    def test_export_uses_exclusive_dtend_and_includes_conflicts(self):
        self.book(self.aura)

        events = calendar_sync.parse_ical_events(calendar_sync.build_unit_calendar(self.full))

        self.assertEqual(len(events), 1)
        _, first_night, checkout = events[0]
        self.assertEqual(first_night, self.start)
        self.assertEqual(checkout, self.end)

    def test_export_contains_no_guest_data(self):
        self.book(self.aura)
        feed_body = calendar_sync.build_unit_calendar(self.full)
        self.assertNotIn('Mario', feed_body)
        self.assertNotIn('mario@example.com', feed_body)

    def test_feed_answers_head_requests(self):
        # i portali fanno un HEAD di verifica prima di accettare l'URL
        response = self.client.head(self.full.get_ical_path())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/calendar; charset=utf-8')

    def test_feed_keeps_working_after_the_slug_is_renamed(self):
        # il link pubblicato sui portali non deve mai rompersi
        published = self.full.get_ical_path()
        self.full.slug = 'nome-cambiato'
        self.full.save()

        self.assertEqual(self.client.get(published).status_code, 200)

    def test_feed_url_requires_the_token(self):
        self.assertEqual(self.client.get(self.full.get_ical_path()).status_code, 200)
        self.assertEqual(
            self.client.get(f'/calendario/{self.full.slug}/wrong-token.ics').status_code, 404
        )

    # -- import ---------------------------------------------------------------

    def make_feed(self):
        return CalendarFeed.objects.create(
            unit=self.full, name='Booking.com',
            url='https://ical.booking.com/v1/export?t=test',
        )

    def test_import_blocks_the_unit_and_everything_it_conflicts_with(self):
        feed = self.make_feed()
        body = ics([('b1@booking.com', self.start, self.end)])

        with mock.patch.object(calendar_sync, 'fetch_feed', return_value=body):
            nights, added, removed = calendar_sync.sync_feed(feed)

        self.assertEqual((nights, added, removed), (4, 4, 0))
        self.assertFalse(AvailabilityService.is_range_available(self.aura, self.start, self.end))
        self.assertFalse(AvailabilityService.is_range_available(self.silva, self.start, self.end))
        self.assertTrue(AvailabilityService.is_date_available(self.full, self.end))

    def test_import_releases_dates_dropped_from_the_feed(self):
        feed = self.make_feed()
        with mock.patch.object(calendar_sync, 'fetch_feed',
                               return_value=ics([('b1@booking.com', self.start, self.end)])):
            calendar_sync.sync_feed(feed)

        with mock.patch.object(calendar_sync, 'fetch_feed', return_value=ics([])):
            nights, added, removed = calendar_sync.sync_feed(feed)

        self.assertEqual((nights, removed), (0, 4))
        self.assertTrue(AvailabilityService.is_range_available(self.full, self.start, self.end))

    def test_import_never_touches_our_own_bookings(self):
        self.book(self.aura)
        feed = self.make_feed()

        with mock.patch.object(calendar_sync, 'fetch_feed', return_value=ics([])):
            calendar_sync.sync_feed(feed)

        self.assertFalse(AvailabilityService.is_range_available(self.aura, self.start, self.end))

    def test_unreachable_feed_keeps_existing_blocks(self):
        feed = self.make_feed()
        with mock.patch.object(calendar_sync, 'fetch_feed',
                               return_value=ics([('b1@booking.com', self.start, self.end)])):
            calendar_sync.sync_feed(feed)

        with mock.patch.object(calendar_sync, 'fetch_feed', side_effect=OSError('timeout')):
            results = calendar_sync.sync_all_feeds()

        feed.refresh_from_db()
        self.assertFalse(results[0]['ok'])
        self.assertTrue(feed.last_error)
        self.assertFalse(AvailabilityService.is_range_available(self.full, self.start, self.end))

    def test_import_marks_dates_as_external(self):
        feed = self.make_feed()
        with mock.patch.object(calendar_sync, 'fetch_feed',
                               return_value=ics([('b1@booking.com', self.start, self.end)])):
            calendar_sync.sync_feed(feed)

        block = BlockedDate.objects.get(unit=self.full, date=self.start)
        self.assertEqual(block.reason, BlockedDate.Reason.EXTERNAL)
        self.assertEqual(block.feed, feed)

    # -- parsing --------------------------------------------------------------

    def test_parses_date_time_values(self):
        events = calendar_sync.parse_ical_events(
            'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:x\n'
            'DTSTART:20260814T150000Z\nDTEND:20260818T100000Z\n'
            'END:VEVENT\nEND:VCALENDAR'
        )
        self.assertEqual(events[0][1:], (date(2026, 8, 14), date(2026, 8, 18)))
        self.assertEqual(len(calendar_sync.nights_from_events(events, today=date(2026, 1, 1))), 4)

    def test_parses_folded_lines(self):
        events = calendar_sync.parse_ical_events(
            'BEGIN:VCALENDAR\nBEGIN:VEVENT\nUID:very-long-uid-split-over\n two-lines\n'
            'DTSTART;VALUE=DATE:20260814\nDTEND;VALUE=DATE:20260816\n'
            'END:VEVENT\nEND:VCALENDAR'
        )
        self.assertEqual(events[0][0], 'very-long-uid-split-overtwo-lines')

    def test_long_lines_are_folded_within_75_octets(self):
        self.full.name = 'Altesia ' * 30
        self.full.save()

        body = calendar_sync.build_unit_calendar(self.full)

        for line in body.split('\r\n'):
            self.assertLessEqual(len(line.encode('utf-8')), 75, line)
        self.assertIn(f'X-WR-CALNAME:{self.full.name}', '\n'.join(calendar_sync._unfold(body)))

    def test_folding_keeps_multibyte_characters_intact(self):
        self.full.name = 'Altèsia àèìòù ' * 10
        self.full.save()

        body = calendar_sync.build_unit_calendar(self.full)

        self.assertIn(f'X-WR-CALNAME:{self.full.name}', '\n'.join(calendar_sync._unfold(body)))

    def test_escapes_ical_special_characters(self):
        self.full.name = 'Altesia; intera, villa'
        self.full.save()

        body = calendar_sync.build_unit_calendar(self.full)

        self.assertIn(r'X-WR-CALNAME:Altesia\; intera\, villa', body)

    def test_rejects_a_response_that_is_not_a_calendar(self):
        feed = self.make_feed()
        with mock.patch.object(calendar_sync, 'fetch_feed',
                               side_effect=ValueError('La risposta non è un calendario iCal')):
            results = calendar_sync.sync_all_feeds()
        self.assertFalse(results[0]['ok'])
