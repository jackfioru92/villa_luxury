#!/usr/bin/env python
"""Create demo data for Villa Luxury."""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
django.setup()

from datetime import date
from apps.villa.models import Villa, BookableUnit, SeasonPrice
from apps.core.models import SiteSettings

# Site Settings
settings_obj = SiteSettings.get_settings()
settings_obj.site_name = 'Altesia'
settings_obj.site_description = 'La vostra esperienza di lusso in Umbria'
settings_obj.email = 'info@altesia.it'
settings_obj.phone = '+39 347 6532405'
settings_obj.whatsapp = '+39 347 6532405'
settings_obj.address = 'Strada di Civitella Benazzone 20\n06134 Perugia (PG)\nUmbria, Italia'
settings_obj.save()
print(f'SiteSettings aggiornati: {settings_obj.site_name}')

# Villa
villa, created = Villa.objects.get_or_create(
    slug='altesia',
    defaults=dict(
        name='Altesia',
        tagline='La vostra esperienza di lusso in Umbria',
        description=(
            'Altesia è una villa di lusso immersa nel verde delle colline umbre, '
            'un rifugio esclusivo dove il lusso incontra la natura e la tradizione. '
            'Con i suoi ampi spazi, la piscina privata e i giardini curati, '
            'offre un\'esperienza indimenticabile per famiglie, coppie e gruppi di amici.'
        ),
        description_short='Villa di lusso con piscina privata nel cuore dell\'Umbria.',
        address='Strada di Civitella Benazzone 20',
        city='Perugia',
        province='Perugia',
        postal_code='06134',
        country='Italia',
        latitude=43.1480,
        longitude=12.3830,
        total_guests=16,
        total_bedrooms=7,
        total_bathrooms=6,
        is_active=True,
    )
)
print(f'Villa {"creata" if created else "esistente"}: {villa.name} (ID: {villa.id})')

# Bookable Units
units_data = [
    {
        'slug': 'intera-villa',
        'name': 'Intera Villa',
        'unit_type': 'FULL',
        'description': (
            'Prenota l\'intera villa Altesia per un\'esperienza esclusiva e privata. '
            '7 camere da letto, 6 bagni, piscina privata, giardino, cucina professionale '
            'e tutti i comfort di una residenza di lusso.'
        ),
        'description_short': 'L\'intera villa con piscina privata, 7 camere e 6 bagni.',
        'max_guests': 16,
        'bedrooms': 7,
        'bathrooms': 6,
        'beds_description': '4 matrimoniali, 2 doppie, 1 singola',
        'base_price': 850,
        'cleaning_fee': 250,
        'min_nights': 3,
        'sort_order': 1,
        'high_price': 1200,
        'xmas_price': 1500,
    },
    {
        'slug': 'appartamento-girasole',
        'name': 'Appartamento Girasole',
        'unit_type': 'APT',
        'description': (
            'Appartamento indipendente al primo piano con vista panoramica sulle colline. '
            'Ampio soggiorno con cucina, 2 camere matrimoniali e 2 bagni. '
            'Accesso alla piscina e ai giardini condivisi.'
        ),
        'description_short': 'Appartamento con vista colline, 2 camere e 2 bagni.',
        'max_guests': 4,
        'bedrooms': 2,
        'bathrooms': 2,
        'beds_description': '2 matrimoniali',
        'base_price': 280,
        'cleaning_fee': 80,
        'min_nights': 2,
        'sort_order': 2,
        'high_price': 380,
        'xmas_price': 450,
    },
    {
        'slug': 'suite-olivo',
        'name': 'Suite Olivo',
        'unit_type': 'ROOM',
        'description': (
            'Suite elegante al piano terra con ingresso indipendente, camera matrimoniale '
            'king-size, bagno privato con doccia a pioggia, e terrazza privata con vista '
            'sul giardino degli ulivi.'
        ),
        'description_short': 'Suite con terrazza privata, letto king-size e bagno en-suite.',
        'max_guests': 2,
        'bedrooms': 1,
        'bathrooms': 1,
        'beds_description': '1 king-size',
        'base_price': 180,
        'cleaning_fee': 50,
        'min_nights': 2,
        'sort_order': 3,
        'high_price': 250,
        'xmas_price': 300,
    },
]

for ud in units_data:
    high_price = ud.pop('high_price')
    xmas_price = ud.pop('xmas_price')
    slug = ud['slug']

    unit, created = BookableUnit.objects.get_or_create(
        villa=villa,
        slug=slug,
        defaults={**ud, 'max_nights': 30, 'is_active': True}
    )
    print(f'  Unità {"creata" if created else "esistente"}: {unit.name}')

    if created:
        # Alta Stagione (Giu-Set)
        SeasonPrice.objects.create(
            unit=unit,
            name='Alta Stagione',
            start_date=date(2026, 6, 1),
            end_date=date(2026, 9, 30),
            price_per_night=high_price,
            min_nights=unit.min_nights + 1 if unit.unit_type == 'FULL' else unit.min_nights,
        )
        # Natale/Capodanno
        SeasonPrice.objects.create(
            unit=unit,
            name='Natale e Capodanno',
            start_date=date(2026, 12, 20),
            end_date=date(2027, 1, 6),
            price_per_night=xmas_price,
            min_nights=5 if unit.unit_type == 'FULL' else 3,
        )

print()
print(f'=== Risultato ===')
print(f'Ville: {Villa.objects.count()}')
print(f'Unità attive: {BookableUnit.objects.filter(is_active=True).count()}')
print(f'Prezzi stagionali: {SeasonPrice.objects.count()}')
print('Done!')
