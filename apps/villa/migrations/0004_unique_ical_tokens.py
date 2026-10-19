"""
Corregge i dati creati dalla 0002/0003 su un database già popolato.

1. Token iCal duplicati. `AddField` valuta il callable di default UNA sola
   volta per riempire le righe esistenti, quindi tutte le unità si sono
   ritrovate lo stesso token: l'unico segreto dell'URL pubblico era condiviso.
   Qui se ne genera uno nuovo per ogni unità coinvolta e si aggiunge il
   vincolo di unicità, così non può ricapitare.

2. Collegamenti verso unità disattivate. La 0003 collega l'intera struttura a
   ogni altra unità della villa, comprese quelle non più in vendita (resti dei
   dati demo): comparirebbero tra i conflitti e, se avessero date bloccate,
   renderebbero indisponibile la villa intera. Vengono scollegate; riattivando
   un'unità il collegamento si rifà dall'admin.
"""
import secrets

from django.db import migrations, models

import apps.villa.models


def fix_duplicate_tokens(apps, schema_editor):
    BookableUnit = apps.get_model('villa', 'BookableUnit')

    seen = set()
    for unit in BookableUnit.objects.all().order_by('sort_order', 'name'):
        if unit.ical_token and unit.ical_token not in seen:
            seen.add(unit.ical_token)
            continue
        while True:
            token = secrets.token_urlsafe(24)
            if token not in seen:
                break
        seen.add(token)
        unit.ical_token = token
        unit.save(update_fields=['ical_token'])


def unlink_inactive_units(apps, schema_editor):
    BookableUnit = apps.get_model('villa', 'BookableUnit')
    Through = BookableUnit.conflicts_with.through

    inactive = list(BookableUnit.objects.filter(is_active=False).values_list('pk', flat=True))
    if inactive:
        Through.objects.filter(from_bookableunit_id__in=inactive).delete()
        Through.objects.filter(to_bookableunit_id__in=inactive).delete()


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('villa', '0003_link_unit_conflicts'),
    ]

    operations = [
        migrations.RunPython(fix_duplicate_tokens, noop),
        migrations.RunPython(unlink_inactive_units, noop),
        migrations.AlterField(
            model_name='bookableunit',
            name='ical_token',
            field=models.CharField(
                default=apps.villa.models.generate_ical_token,
                help_text="Parte segreta dell'URL del feed .ics pubblico",
                max_length=64,
                unique=True,
                verbose_name='Token feed iCal',
            ),
        ),
    ]
