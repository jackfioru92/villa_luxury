"""Feed iCal pubblico delle disponibilità, uno per unità prenotabile."""
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_safe

from apps.booking.calendar_sync import build_unit_calendar
from apps.villa.models import BookableUnit


@require_safe
def calendar_feed(request, unit_slug, token):
    """
    Espone le notti occupate di un'unità in formato iCal.

    L'URL è pubblico ma non indovinabile (token). Non contiene dati personali:
    solo intervalli di date con SUMMARY "Occupato".
    """
    unit = get_object_or_404(BookableUnit, slug=unit_slug, ical_token=token)

    response = HttpResponse(
        build_unit_calendar(unit),
        content_type='text/calendar; charset=utf-8',
    )
    response['Content-Disposition'] = f'inline; filename="{unit.slug}.ics"'
    response['Cache-Control'] = 'no-cache, max-age=0'
    response['X-Robots-Tag'] = 'noindex, nofollow'
    return response
