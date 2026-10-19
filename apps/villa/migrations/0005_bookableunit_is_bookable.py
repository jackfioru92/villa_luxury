from django.db import migrations, models


def only_full_villa_is_bookable(apps, schema_editor):
    """Le singole suite restano visibili ma si prenotano solo nell'intera struttura."""
    BookableUnit = apps.get_model('villa', 'BookableUnit')
    BookableUnit.objects.exclude(unit_type='FULL').update(is_bookable=False)


def all_bookable(apps, schema_editor):
    BookableUnit = apps.get_model('villa', 'BookableUnit')
    BookableUnit.objects.update(is_bookable=True)


class Migration(migrations.Migration):

    dependencies = [
        ('villa', '0004_unique_ical_tokens'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bookableunit',
            name='is_active',
            field=models.BooleanField(
                default=True,
                help_text="Se disattivata l'unità sparisce da tutto il sito",
                verbose_name='Visibile sul sito',
            ),
        ),
        migrations.AddField(
            model_name='bookableunit',
            name='is_bookable',
            field=models.BooleanField(
                default=True,
                help_text='Se disattivata resta visibile (foto e descrizione) ma non è prenotabile da sola',
                verbose_name='Prenotabile singolarmente',
            ),
        ),
        migrations.RunPython(only_full_villa_is_bookable, all_bookable),
    ]
