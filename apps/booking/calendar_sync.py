"""
Sincronizzazione calendari con i portali esterni (Booking.com, Airbnb, ...)
tramite feed iCal.

Due direzioni, indipendenti:

* EXPORT - `build_unit_calendar()` genera il .ics delle nostre notti occupate.
  L'URL pubblico (token segreto) va incollato nel portale, che lo rilegge
  periodicamente e chiude quelle date.

* IMPORT - `sync_feed()` scarica il .ics del portale e crea BlockedDate con
  reason=EXTERNAL. In caso di errore NON tocca i blocchi esistenti: meglio
  tenere chiuse date che potrebbero essere libere che rischiare un overbooking.

Convenzione iCal: DTEND è ESCLUSIVO. Un soggiorno 10 -> 14 occupa le notti
10, 11, 12 e 13, esattamente come i nostri BlockedDate (check_in .. check_out-1).
"""
from datetime import date, datetime, timedelta
from urllib.request import Request, urlopen

from django.utils import timezone

from apps.booking.models import BlockedDate, CalendarFeed

PRODID = '-//Altesia Suite//Calendario disponibilita//IT'
USER_AGENT = 'AltesiaSuite-CalendarSync/1.0'
FETCH_TIMEOUT = 30
MAX_FEED_BYTES = 5 * 1024 * 1024

# Quanto indietro/avanti esportiamo. Booking.com apre la disponibilità fino a
# 365 giorni, teniamo un margine.
EXPORT_PAST_DAYS = 7
EXPORT_FUTURE_DAYS = 730


# ---------------------------------------------------------------- export

def _ics_escape(value):
    return (
        str(value)
        .replace('\\', '\\\\')
        .replace(';', '\;')
        .replace(',', '\\,')
        .replace('\n', '\\n')
    )


def _fold(line):
    """RFC 5545: righe max 75 ottetti, le successive iniziano con uno spazio."""
    raw = line.encode('utf-8')
    if len(raw) <= 75:
        return line
    chunks, start = [], 0
    while start < len(raw):
        end = min(start + 75, len(raw))
        # non spezzare a metà di un carattere multibyte
        while end > start and end < len(raw) and (raw[end] & 0xC0) == 0x80:
            end -= 1
        chunks.append(raw[start:end].decode('utf-8'))
        start = end
        if start < len(raw):
            raw = b' ' + raw[start:]
            start = 0
    return '\r\n '.join(chunks)


def blocked_dates_for_unit(unit, start, end):
    """Notti occupate per l'unità, incluse quelle delle unità in conflitto."""
    return set(
        BlockedDate.objects.filter(
            unit__in=unit.blocking_units(),
            date__gte=start,
            date__lte=end,
        ).values_list('date', flat=True)
    )


def group_consecutive(dates):
    """[d1, d2, d4] -> [(d1, d2), (d4, d4)] (estremi inclusivi)."""
    ranges = []
    for current in sorted(dates):
        if ranges and current == ranges[-1][1] + timedelta(days=1):
            ranges[-1][1] = current
        else:
            ranges.append([current, current])
    return [(a, b) for a, b in ranges]


def build_unit_calendar(unit, today=None):
    """Genera il contenuto .ics delle notti occupate di un'unità."""
    today = today or date.today()
    start = today - timedelta(days=EXPORT_PAST_DAYS)
    end = today + timedelta(days=EXPORT_FUTURE_DAYS)

    stamp = timezone.now().strftime('%Y%m%dT%H%M%SZ')

    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        f'PRODID:{PRODID}',
        'CALSCALE:GREGORIAN',
        'METHOD:PUBLISH',
        f'X-WR-CALNAME:{_ics_escape(unit.name)}',
    ]

    for first_night, last_night in group_consecutive(blocked_dates_for_unit(unit, start, end)):
        # DTEND esclusivo: giorno di check-out = ultima notte + 1
        checkout = last_night + timedelta(days=1)
        uid = f'{unit.slug}-{first_night:%Y%m%d}-{checkout:%Y%m%d}@altesiasuite.com'
        lines += [
            'BEGIN:VEVENT',
            f'UID:{uid}',
            f'DTSTAMP:{stamp}',
            f'DTSTART;VALUE=DATE:{first_night:%Y%m%d}',
            f'DTEND;VALUE=DATE:{checkout:%Y%m%d}',
            'SUMMARY:Occupato',
            'TRANSP:OPAQUE',
            'END:VEVENT',
        ]

    lines.append('END:VCALENDAR')
    return '\r\n'.join(_fold(line) for line in lines) + '\r\n'


# ---------------------------------------------------------------- import

def _unfold(text):
    """Ricompone le righe continuate (quelle che iniziano con spazio o tab)."""
    out = []
    for raw_line in text.replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if raw_line[:1] in (' ', '\t') and out:
            out[-1] += raw_line[1:]
        else:
            out.append(raw_line)
    return out


def _parse_dt(value):
    """Accetta 20260814, 20260814T120000Z, 20260814T120000. Ritorna una date."""
    value = value.strip()
    if 'T' in value:
        value = value.split('T')[0]
    if len(value) != 8 or not value.isdigit():
        raise ValueError(f'Data iCal non riconosciuta: {value!r}')
    return datetime.strptime(value, '%Y%m%d').date()


def parse_ical_events(text):
    """Estrae [(uid, first_night, checkout_escluso), ...] dal contenuto .ics."""
    events, current = [], None

    for line in _unfold(text):
        upper = line.upper()
        if upper.startswith('BEGIN:VEVENT'):
            current = {}
            continue
        if upper.startswith('END:VEVENT'):
            if current and current.get('start') and current.get('end'):
                events.append((current.get('uid', ''), current['start'], current['end']))
            current = None
            continue
        if current is None or ':' not in line:
            continue

        prop, _, value = line.partition(':')
        name = prop.split(';')[0].strip().upper()
        if name == 'UID':
            current['uid'] = value.strip()[:255]
        elif name == 'DTSTART':
            current['start'] = _parse_dt(value)
        elif name == 'DTEND':
            current['end'] = _parse_dt(value)

    return events


def fetch_feed(url):
    request = Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'text/calendar, */*'})
    with urlopen(request, timeout=FETCH_TIMEOUT) as response:
        payload = response.read(MAX_FEED_BYTES + 1)
    if len(payload) > MAX_FEED_BYTES:
        raise ValueError('Feed troppo grande')
    text = payload.decode('utf-8', errors='replace')
    if 'BEGIN:VCALENDAR' not in text.upper():
        raise ValueError('La risposta non è un calendario iCal')
    return text


def nights_from_events(events, today=None):
    """Espande gli eventi nelle singole notti, scartando il passato remoto."""
    today = today or date.today()
    floor = today - timedelta(days=EXPORT_PAST_DAYS)
    nights = {}
    for uid, start, end in events:
        # DTEND esclusivo; un evento di un solo giorno (start == end) vale 1 notte
        last_night = max(end - timedelta(days=1), start)
        current = start
        while current <= last_night:
            if current >= floor:
                nights.setdefault(current, uid)
            current += timedelta(days=1)
    return nights


def sync_feed(feed, today=None):
    """
    Scarica e applica un feed. Ritorna (notti_bloccate, aggiunte, rimosse).
    Solleva eccezione in caso di errore di rete/parsing, senza toccare i blocchi.
    """
    text = fetch_feed(feed.url)
    nights = nights_from_events(parse_ical_events(text), today=today)

    # Si blocca solo l'unità del feed: le unità in conflitto risultano occupate
    # in lettura (BookableUnit.blocking_units), senza propagare righe nel DB.
    existing = {block.date: block for block in BlockedDate.objects.filter(feed=feed)}

    to_create = [
        BlockedDate(
            unit=feed.unit,
            date=night,
            reason=BlockedDate.Reason.EXTERNAL,
            feed=feed,
            external_uid=uid,
            note=feed.name[:200],
        )
        for night, uid in nights.items()
        if night not in existing
    ]

    # ignore_conflicts: la notte può essere già bloccata da una prenotazione
    # nostra o da un altro feed (unique_together unit+date)
    BlockedDate.objects.bulk_create(to_create, ignore_conflicts=True)

    stale = [night for night in existing if night not in nights]
    removed = 0
    if stale:
        removed = BlockedDate.objects.filter(
            feed=feed,
            id__in=[existing[night].id for night in stale],
        ).delete()[0]

    return len(nights), len(to_create), removed


def sync_all_feeds(today=None):
    """Sincronizza tutti i feed attivi. Ritorna la lista dei risultati."""
    results = []
    for feed in CalendarFeed.objects.filter(is_active=True).select_related('unit'):
        now = timezone.now()
        try:
            nights, added, removed = sync_feed(feed, today=today)
        except Exception as exc:
            feed.last_sync_at = now
            feed.last_error = f'{type(exc).__name__}: {exc}'[:1000]
            feed.save(update_fields=['last_sync_at', 'last_error', 'updated_at'])
            results.append({'feed': feed, 'ok': False, 'error': str(exc)})
        else:
            feed.last_sync_at = now
            feed.last_success_at = now
            feed.last_error = ''
            feed.last_blocked_count = nights
            feed.save(update_fields=[
                'last_sync_at', 'last_success_at', 'last_error',
                'last_blocked_count', 'updated_at',
            ])
            results.append({
                'feed': feed, 'ok': True,
                'nights': nights, 'added': added, 'removed': removed,
            })
    return results
