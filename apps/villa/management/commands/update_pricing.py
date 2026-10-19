"""
Aggiorna il prezziario stagionale (SeasonPrice) delle unità prenotabili.

Le tariffe sono quelle definite dalla proprietà: struttura intera,
pernottamento con colazione inclusa. Si modificano nelle tabelle qui sotto e
si riapplicano rilanciando il comando.

Le singole suite non sono prenotabili separatamente (`is_bookable=False`):
restano visibili sul sito ma non hanno un prezzo proprio, e il comando
rimuove eventuali prezzi stagionali rimasti.

Periodi speciali: Natale/Capodanno, settimana di Pasqua (data mobile,
calcolata ogni anno) e settimana di Ferragosto vengono "ritagliati" dalle
fasce di base, così i periodi non si sovrappongono mai. Serve perché la
ricerca del prezzo prende il primo periodo per data di inizio: un periodo
contenuto in un altro non verrebbe mai applicato.

Uso:
  python manage.py update_pricing --show       # prezzi attuali, nessuna modifica
  python manage.py update_pricing --dry-run    # mostra il piano
  python manage.py update_pricing              # applica (anno corrente -> 2030)
  python manage.py update_pricing --until 2032 # orizzonte più lungo
"""
from datetime import date, timedelta

from dateutil.easter import easter
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.villa.models import BookableUnit

# --------------------------------------------------------------------------
# TARIFFE €/notte - struttura intera, colazione inclusa
# --------------------------------------------------------------------------

LOW = 1000          # novembre-marzo e ottobre
MID = 1200          # aprile, maggio, giugno, settembre
HIGH = 1500         # luglio e agosto
XMAS = 1600         # 8 dicembre - 6 gennaio
EASTER = 1500       # settimana di Pasqua
FERRAGOSTO = 1700   # 9 - 15 agosto

# Fasce di base, (etichetta, (mese, giorno) inizio, (mese, giorno) fine, prezzo).
# L'inverno è spezzato attorno al periodo natalizio, che scavalca l'anno.
BASE_PERIODS = [
    ('Novembre - Marzo', (1, 7), (3, 31), LOW),
    ('Aprile - Maggio', (4, 1), (5, 31), MID),
    ('Giugno', (6, 1), (6, 30), MID),
    ('Luglio', (7, 1), (7, 31), HIGH),
    ('Agosto', (8, 1), (8, 31), HIGH),
    ('Settembre', (9, 1), (9, 30), MID),
    ('Ottobre', (10, 1), (10, 31), LOW),
    ('Novembre - Marzo', (11, 1), (12, 7), LOW),
]

# Periodo natalizio: 8 dicembre -> 6 gennaio dell'anno successivo
XMAS_START = (12, 8)
XMAS_END = (1, 6)

# Settimana di Ferragosto: notti dal 9 al 15 agosto (check-out il 16)
FERRAGOSTO_START = (8, 9)
FERRAGOSTO_END = (8, 15)

# Settimana di Pasqua: le 7 notti che terminano con il lunedì dell'Angelo,
# cioè da 5 giorni prima della domenica di Pasqua al giorno dopo.
EASTER_NIGHTS_BEFORE = 5
EASTER_NIGHTS_AFTER = 1

# Ultimo anno generato di default (dall'anno corrente incluso)
DEFAULT_UNTIL_YEAR = 2030


def easter_week(year):
    """(inizio, fine) della settimana di Pasqua: data mobile, va calcolata."""
    sunday = easter(year)
    return (
        sunday - timedelta(days=EASTER_NIGHTS_BEFORE),
        sunday + timedelta(days=EASTER_NIGHTS_AFTER),
    )


def special_periods(year):
    """Periodi che hanno la precedenza sulle fasce di base."""
    easter_start, easter_end = easter_week(year)
    return [
        ('Settimana di Pasqua', easter_start, easter_end, EASTER),
        ('Settimana di Ferragosto', date(year, *FERRAGOSTO_START),
         date(year, *FERRAGOSTO_END), FERRAGOSTO),
        ('Natale e Capodanno', date(year, *XMAS_START),
         date(year + 1, *XMAS_END), XMAS),
    ]


def subtract(span, cuts):
    """Frammenti di `span` non coperti da nessuno dei `cuts`."""
    fragments = [span]
    for cut_start, cut_end in cuts:
        remaining = []
        for start, end in fragments:
            if cut_end < start or cut_start > end:
                remaining.append((start, end))
                continue
            if start < cut_start:
                remaining.append((start, cut_start - timedelta(days=1)))
            if end > cut_end:
                remaining.append((cut_end + timedelta(days=1), end))
        fragments = remaining
    return fragments


def build_periods(year):
    """Periodi tariffari dell'anno, ordinati e senza sovrapposizioni."""
    specials = special_periods(year)
    cuts = [(start, end) for _, start, end, _ in specials]

    periods = [(label, start, end, price) for label, start, end, price in specials]
    for label, (m1, d1), (m2, d2), price in BASE_PERIODS:
        span = (date(year, m1, d1), date(year, m2, d2))
        for start, end in subtract(span, cuts):
            periods.append((label, start, end, price))

    return sorted(periods, key=lambda p: p[1])


class Command(BaseCommand):
    help = 'Aggiorna il prezziario stagionale delle unità prenotabili'

    def add_arguments(self, parser):
        parser.add_argument(
            '--years', nargs='+', type=int,
            help="Anni da generare (default: dall'anno corrente a --until)",
        )
        parser.add_argument(
            '--until', type=int, default=DEFAULT_UNTIL_YEAR,
            help=f'Ultimo anno da generare (default: {DEFAULT_UNTIL_YEAR})',
        )
        parser.add_argument('--dry-run', action='store_true', help='Mostra il piano senza scrivere')
        parser.add_argument('--show', action='store_true', help='Mostra i prezzi attuali ed esce')
        parser.add_argument(
            '--keep-base-price', action='store_true',
            help='Non aggiornare base_price delle unità',
        )

    def handle(self, *args, **options):
        units = list(BookableUnit.objects.filter(is_active=True).order_by('sort_order', 'name'))
        if not units:
            raise CommandError('Nessuna unità attiva trovata.')

        if options['show']:
            self.show_current(units)
            return

        today = date.today()
        years = options['years'] or list(range(today.year, options['until'] + 1))
        if not years:
            raise CommandError(f"--until {options['until']} è precedente all'anno corrente.")

        dry_run = options['dry_run']
        # Si costruisce anche l'anno precedente: il periodo natalizio nasce a
        # dicembre e arriva al 6 gennaio, quindi senza di esso le notti di
        # inizio gennaio resterebbero scoperte e verrebbero vendute a tariffa
        # base invece che a tariffa festiva.
        first_year = min(years)
        periods = [
            period
            for year in range(first_year - 1, max(years) + 1)
            for period in build_periods(year)
            if period[2] >= today and period[2].year >= first_year
        ]
        if not periods:
            raise CommandError('Nessun periodo futuro negli anni indicati.')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Prezziario struttura intera, anni {sorted(set(years))}'
            f'{"  [DRY RUN]" if dry_run else ""}'
        ))

        with transaction.atomic():
            for unit in units:
                if unit.is_bookable:
                    self.apply_tariffs(unit, periods, dry_run, options['keep_base_price'])
                else:
                    self.clear_tariffs(unit, dry_run)

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: nessuna modifica scritta.'))
        else:
            bookable = sum(1 for u in units if u.is_bookable)
            self.stdout.write(self.style.SUCCESS(
                f'Fatto: {bookable} unità prenotabili, {len(periods)} periodi ciascuna.'
            ))

    def apply_tariffs(self, unit, periods, dry_run, keep_base_price):
        from apps.villa.models import SeasonPrice

        self.stdout.write(f'\n{unit.name}  [{unit.get_unit_type_display()}, {unit.max_guests} ospiti]')

        existing = unit.season_prices.all()
        count = existing.count()
        if count:
            self.stdout.write(f'  - rimuovo {count} prezzi stagionali esistenti')
            if not dry_run:
                existing.delete()

        for label, start, end, price in periods:
            self.stdout.write(f'  + {label:<24} {start} -> {end}  {price:>5} €/notte')
            if not dry_run:
                SeasonPrice.objects.create(
                    unit=unit, name=label,
                    start_date=start, end_date=end,
                    price_per_night=price,
                )

        if not keep_base_price:
            lowest = min(price for _, _, _, price in periods)
            self.stdout.write(f'  = base_price (prezzo "da"): {unit.base_price} -> {lowest} €')
            if not dry_run:
                unit.base_price = lowest
                unit.save(update_fields=['base_price', 'updated_at'])

    def clear_tariffs(self, unit, dry_run):
        count = unit.season_prices.count()
        self.stdout.write(
            f'\n{unit.name}  [non prenotabile singolarmente]'
        )
        if count:
            self.stdout.write(f'  - rimuovo {count} prezzi stagionali non più applicabili')
            if not dry_run:
                unit.season_prices.all().delete()
        else:
            self.stdout.write('  (nessun prezzo da rimuovere)')

    def show_current(self, units):
        for unit in units:
            flag = '' if unit.is_bookable else '  [NON prenotabile singolarmente]'
            self.stdout.write(
                f'\n{unit.name}{flag}  [{unit.get_unit_type_display()}, {unit.max_guests} ospiti, '
                f'base {unit.base_price} €, pulizie {unit.cleaning_fee} €, min {unit.min_nights} notti]'
            )
            seasons = unit.season_prices.all()
            if not seasons:
                self.stdout.write('  (nessun prezzo stagionale)')
            for season in seasons:
                extra = f', min {season.min_nights} notti' if season.min_nights else ''
                self.stdout.write(
                    f'  {season.name:<24} {season.start_date} -> {season.end_date}'
                    f'  {season.price_per_night:>8} €{extra}'
                )
