"""
Rimuove le unità prenotabili disattivate e inutilizzate (resti dei dati demo).

Di default non cancella nulla: mostra cosa verrebbe rimosso. Un'unità con
prenotazioni collegate non viene mai toccata, nemmeno con --delete: lo storico
delle prenotazioni deve restare consultabile (il FK è PROTECT, quindi il
database rifiuterebbe comunque la cancellazione).

Uso:
  python manage.py cleanup_units            # anteprima
  python manage.py cleanup_units --delete   # esegue
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.booking.models import BlockedDate, Booking, CalendarFeed
from apps.villa.models import BookableUnit


class Command(BaseCommand):
    help = 'Rimuove le unità disattivate che non hanno prenotazioni collegate'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete', action='store_true',
            help='Esegue la cancellazione (senza, mostra solo l\'anteprima)',
        )

    def handle(self, *args, **options):
        candidates = BookableUnit.objects.filter(is_active=False).order_by('sort_order', 'name')

        if not candidates:
            self.stdout.write('Nessuna unità disattivata. Niente da fare.')
            return

        removable, protected = [], []
        for unit in candidates:
            bookings = Booking.objects.filter(unit=unit)
            if bookings.exists():
                protected.append((unit, bookings.count()))
            else:
                removable.append(unit)

        for unit, count in protected:
            self.stdout.write(self.style.WARNING(
                f'SALTATA  {unit.name} ({unit.slug}): ha {count} prenotazioni, va conservata'
            ))

        if not removable:
            self.stdout.write('Nessuna unità rimovibile.')
            return

        for unit in removable:
            self.stdout.write(f'\n{unit.name}  ({unit.slug}, {unit.get_unit_type_display()})')
            self.stdout.write(f'  prezzi stagionali : {unit.season_prices.count()}')
            self.stdout.write(f'  date bloccate     : {BlockedDate.objects.filter(unit=unit).count()}')
            self.stdout.write(f'  feed calendario   : {CalendarFeed.objects.filter(unit=unit).count()}')
            self.stdout.write(f'  immagini galleria : {unit.gallery_images.count()}')
            self.stdout.write(f'  amenities         : {unit.unit_amenities.count()}')
            self.stdout.write(f'  conflitti         : {[c.name for c in unit.conflicts_with.all()] or "nessuno"}')

        self.stdout.write('')
        if not options['delete']:
            self.stdout.write(self.style.WARNING(
                f'Anteprima: {len(removable)} unità da rimuovere. '
                'Rilancia con --delete per eseguire.'
            ))
            return

        with transaction.atomic():
            for unit in removable:
                name = unit.name
                unit.delete()
                self.stdout.write(self.style.SUCCESS(f'Rimossa: {name}'))

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'{len(removable)} unità rimosse.'))
