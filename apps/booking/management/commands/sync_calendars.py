"""
Sincronizza i calendari dei portali esterni (Booking.com, Airbnb, ...).

Pensato per girare da cron ogni 10-15 minuti:
    */15 * * * * /opt/altesiasuite/sync_calendars.sh

In caso di errore su un feed gli altri proseguono e i blocchi già presenti
restano: non si rischia di riaprire date vendute su un portale.
"""
from django.core.management.base import BaseCommand

from apps.booking.calendar_sync import sync_all_feeds
from apps.booking.models import CalendarFeed
from apps.villa.models import BookableUnit


class Command(BaseCommand):
    help = 'Importa i feed iCal dei portali esterni e aggiorna le date bloccate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--show', action='store_true',
            help='Mostra i feed configurati e gli URL da pubblicare, senza sincronizzare',
        )

    def handle(self, *args, **options):
        if options['show']:
            self.show()
            return

        results = sync_all_feeds()
        if not results:
            self.stdout.write(self.style.WARNING(
                'Nessun feed attivo. Aggiungine uno da /admin/booking/calendarfeed/'
            ))
            return

        failed = 0
        for result in results:
            feed = result['feed']
            if result['ok']:
                self.stdout.write(
                    f"OK  {feed.unit.name} / {feed.name}: {result['nights']} notti "
                    f"(+{result['added']} / -{result['removed']})"
                )
            else:
                failed += 1
                self.stderr.write(self.style.ERROR(
                    f"ERR {feed.unit.name} / {feed.name}: {result['error']}"
                ))

        if failed:
            self.stderr.write(self.style.ERROR(f'{failed} feed su {len(results)} in errore'))
        else:
            self.stdout.write(self.style.SUCCESS(f'{len(results)} feed sincronizzati'))

    def show(self):
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Feed da pubblicare sui portali (export, il nostro calendario):'
        ))
        for unit in BookableUnit.objects.filter(is_active=True).order_by('sort_order'):
            conflicts = ', '.join(u.name for u in unit.conflicts_with.all()) or 'nessuna'
            self.stdout.write(f'\n  {unit.name}')
            self.stdout.write(f'    URL      https://altesiasuite.com{unit.get_ical_path()}')
            self.stdout.write(f'    conflitti con: {conflicts}')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(
            'Feed importati dai portali (import, il loro calendario):'
        ))
        feeds = CalendarFeed.objects.select_related('unit').all()
        if not feeds:
            self.stdout.write('  (nessuno configurato)')
        for feed in feeds:
            state = 'attivo' if feed.is_active else 'disattivato'
            self.stdout.write(f'\n  {feed.unit.name} / {feed.name} [{state}]')
            self.stdout.write(f'    {feed.url}')
            self.stdout.write(
                f'    ultimo sync: {feed.last_sync_at or "mai"}'
                f'{"  ERRORE: " + feed.last_error if feed.last_error else ""}'
            )
