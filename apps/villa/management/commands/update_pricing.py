"""
Aggiorna il prezziario stagionale (SeasonPrice) di tutte le unità attive.

Le tariffe sono definite nelle tabelle in cima a questo file come intervalli
(min, max) €/notte, così come proposte al cliente. Il punto dell'intervallo
da applicare si sceglie con --point (low | mid | high), default: mid.

L'unità di tipo FULL (intera struttura, 8 ospiti) usa la tabella
FULL_STRUCTURE_PRICES; tutte le altre unità (suite/appartamenti) usano
SUITE_PRICES, con i mesi raggruppati in bassa / media / alta stagione
secondo SUITE_TIER_BY_PERIOD.

I periodi generati NON si sovrappongono mai: la ricerca del prezzo usa
`.first()` ordinato per start_date, quindi un periodo "Natale" contenuto in
"Novembre-Marzo" non verrebbe mai applicato. Per questo l'inverno è spezzato
in Nov-19 Dic / Natale-Capodanno / 7 Gen-Mar.

Uso:
  python manage.py update_pricing --show             # prezzi attuali, nessuna modifica
  python manage.py update_pricing --dry-run          # mostra il piano, nessuna modifica
  python manage.py update_pricing                    # applica (anno corrente + successivo)
  python manage.py update_pricing --years 2026 2027  # anni espliciti
  python manage.py update_pricing --point low        # estremo basso degli intervalli
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.villa.models import BookableUnit, SeasonPrice


# --------------------------------------------------------------------------
# TARIFFE (min, max) €/notte — modificare qui per cambiare il prezziario
# --------------------------------------------------------------------------

# Struttura intera (8 ospiti)
FULL_STRUCTURE_PRICES = {
    'gen_mar': ('Novembre - Marzo', (590, 690)),
    'apr_mag': ('Aprile - Maggio', (750, 890)),
    'giu':     ('Giugno', (890, 990)),
    'lug':     ('Luglio', (990, 1150)),
    'ago':     ('Agosto', (1150, 1350)),
    'set':     ('Settembre', (950, 1100)),
    'ott':     ('Ottobre', (790, 950)),
    'nov_dic': ('Novembre - Marzo', (590, 690)),
    'natale':  ('Natale e Capodanno', (1200, 1450)),
}

# Singola suite — tetto iniziale prudente, non oltre 500 €/notte
SUITE_PRICES = {
    'bassa':  ('Bassa stagione', (260, 290)),
    'media':  ('Media stagione', (320, 390)),
    'alta':   ('Alta stagione', (420, 490)),
    'natale': ('Natale e Capodanno', (420, 490)),
}

# Mappa mese -> fascia per le suite
SUITE_TIER_BY_PERIOD = {
    'gen_mar': 'bassa',
    'nov_dic': 'bassa',
    'apr_mag': 'media',
    'giu':     'media',
    'ott':     'media',
    'lug':     'alta',
    'ago':     'alta',
    'set':     'alta',
    'natale':  'natale',
}

# Periodo Natale/Capodanno: 20 dicembre -> 6 gennaio (Epifania inclusa)
XMAS_START = (12, 20)
XMAS_END = (1, 6)


def build_periods(year):
    """Periodi (chiave, start, end) per un anno solare, non sovrapposti."""
    return [
        ('gen_mar', date(year, 1, XMAS_END[1] + 1), date(year, 3, 31)),
        ('apr_mag', date(year, 4, 1), date(year, 5, 31)),
        ('giu',     date(year, 6, 1), date(year, 6, 30)),
        ('lug',     date(year, 7, 1), date(year, 7, 31)),
        ('ago',     date(year, 8, 1), date(year, 8, 31)),
        ('set',     date(year, 9, 1), date(year, 9, 30)),
        ('ott',     date(year, 10, 1), date(year, 10, 31)),
        ('nov_dic', date(year, 11, 1), date(year, XMAS_START[0], XMAS_START[1] - 1)),
        ('natale',  date(year, *XMAS_START), date(year + 1, *XMAS_END)),
    ]


def pick_price(price_range, point):
    lo, hi = price_range
    if point == 'low':
        return lo
    if point == 'high':
        return hi
    return (lo + hi) // 2


def tariff_for_unit(unit, period_key, point):
    """Ritorna (nome_stagione, prezzo) per unità e periodo."""
    if unit.unit_type == BookableUnit.UnitType.FULL_VILLA:
        label, price_range = FULL_STRUCTURE_PRICES[period_key]
    else:
        label, price_range = SUITE_PRICES[SUITE_TIER_BY_PERIOD[period_key]]
    return label, pick_price(price_range, point)


def low_season_price(unit, point):
    """Prezzo "da" mostrato sul sito (= bassa stagione)."""
    if unit.unit_type == BookableUnit.UnitType.FULL_VILLA:
        return pick_price(FULL_STRUCTURE_PRICES['nov_dic'][1], point)
    return pick_price(SUITE_PRICES['bassa'][1], point)


class Command(BaseCommand):
    help = 'Aggiorna il prezziario stagionale di tutte le unità attive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--years', nargs='+', type=int,
            help='Anni da generare (default: anno corrente e successivo)',
        )
        parser.add_argument(
            '--point', choices=['low', 'mid', 'high'], default='mid',
            help='Punto dell\'intervallo di prezzo da applicare (default: mid)',
        )
        parser.add_argument(
            '--dry-run', action='store_true',
            help='Mostra il piano senza scrivere nulla',
        )
        parser.add_argument(
            '--show', action='store_true',
            help='Mostra i prezzi stagionali attuali ed esce',
        )
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
        years = options['years'] or [today.year, today.year + 1]
        point = options['point']
        dry_run = options['dry_run']

        # Piano: solo periodi non ancora conclusi
        periods = [
            p for y in sorted(set(years)) for p in build_periods(y)
            if p[2] >= today
        ]
        if not periods:
            raise CommandError('Nessun periodo futuro negli anni indicati.')

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Prezziario: anni {sorted(set(years))}, punto intervallo = {point}'
            f'{"  [DRY RUN]" if dry_run else ""}'
        ))

        with transaction.atomic():
            for unit in units:
                kind = 'STRUTTURA INTERA' if unit.unit_type == BookableUnit.UnitType.FULL_VILLA else 'SUITE'
                self.stdout.write(f'\n{unit.name}  [{unit.get_unit_type_display()} -> tariffa {kind}, {unit.max_guests} ospiti]')

                existing = unit.season_prices.all()
                n_existing = existing.count()
                if n_existing:
                    self.stdout.write(f'  - rimuovo {n_existing} prezzi stagionali esistenti')
                    for s in existing:
                        self.stdout.write(f'      x {s.name}: {s.start_date} -> {s.end_date} = {s.price_per_night} €')
                    if not dry_run:
                        existing.delete()

                for key, start, end in periods:
                    label, price = tariff_for_unit(unit, key, point)
                    self.stdout.write(f'  + {label:<22} {start} -> {end}  {price:>5} €/notte')
                    if not dry_run:
                        SeasonPrice.objects.create(
                            unit=unit, name=label,
                            start_date=start, end_date=end,
                            price_per_night=price,
                        )

                if not options['keep_base_price']:
                    new_base = low_season_price(unit, point)
                    self.stdout.write(f'  = base_price (prezzo "da"): {unit.base_price} -> {new_base} €')
                    if not dry_run:
                        unit.base_price = new_base
                        unit.save(update_fields=['base_price', 'updated_at'])

            if dry_run:
                transaction.set_rollback(True)

        self.stdout.write('')
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run: nessuna modifica scritta.'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Fatto: {len(units)} unità, {len(periods)} periodi ciascuna.'
            ))

    def show_current(self, units):
        for unit in units:
            self.stdout.write(
                f'\n{unit.name}  [{unit.get_unit_type_display()}, {unit.max_guests} ospiti, '
                f'base {unit.base_price} €, pulizie {unit.cleaning_fee} €, min {unit.min_nights} notti]'
            )
            seasons = unit.season_prices.all()
            if not seasons:
                self.stdout.write('  (nessun prezzo stagionale)')
            for s in seasons:
                extra = f', min {s.min_nights} notti' if s.min_nights else ''
                self.stdout.write(f'  {s.name:<22} {s.start_date} -> {s.end_date}  {s.price_per_night:>8} €{extra}')
