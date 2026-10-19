"""
Collega l'unità "intera villa" alle singole unità della stessa villa.

Occupano lo stesso spazio fisico: prenotandone una, le altre non sono più
disponibili. Senza questo collegamento il sito accetterebbe contemporaneamente
una prenotazione dell'intera struttura e una delle singole suite.

Le righe vengono scritte in ENTRAMBE le direzioni passando dal modello
through: sui modelli storici di una migrazione la simmetria del
ManyToManyField non viene applicata automaticamente, e una relazione
registrata in un solo verso lascerebbe l'altra unità prenotabile.
"""
from django.db import migrations


def link_conflicts(apps, schema_editor):
    BookableUnit = apps.get_model('villa', 'BookableUnit')
    Through = BookableUnit.conflicts_with.through

    rows = []
    for full in BookableUnit.objects.filter(unit_type='FULL'):
        others = BookableUnit.objects.filter(villa_id=full.villa_id).exclude(pk=full.pk)
        for other in others:
            rows.append(Through(from_bookableunit_id=full.pk, to_bookableunit_id=other.pk))
            rows.append(Through(from_bookableunit_id=other.pk, to_bookableunit_id=full.pk))

    Through.objects.bulk_create(rows, ignore_conflicts=True)


def unlink_conflicts(apps, schema_editor):
    BookableUnit = apps.get_model('villa', 'BookableUnit')
    Through = BookableUnit.conflicts_with.through

    full_ids = list(BookableUnit.objects.filter(unit_type='FULL').values_list('pk', flat=True))
    Through.objects.filter(from_bookableunit_id__in=full_ids).delete()
    Through.objects.filter(to_bookableunit_id__in=full_ids).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('villa', '0002_bookableunit_conflicts_with_bookableunit_ical_token'),
    ]

    operations = [
        migrations.RunPython(link_conflicts, unlink_conflicts),
    ]
