"""Valori condivisi tra più app."""
from django.utils.translation import gettext_lazy as _

# Esperienze proposte agli ospiti. Elenco unico, usato sia dal form contatti
# sia dal wizard di prenotazione: tenerli allineati a mano porterebbe le due
# liste a divergere.
#
# Ogni voce è (valore, etichetta): il valore è quello che viene inviato dal
# form e salvato su Booking.experiences, e resta in italiano in tutte le
# lingue, perché finisce nelle email allo staff e nella dashboard. Solo
# l'etichetta mostrata all'ospite viene tradotta.
EXPERIENCES = [
    ('Chef Privato', _('Chef Privato')),
    ('Colazione Privata', _('Colazione Privata')),
    ('Aperitivi & Cene Esclusive', _('Aperitivi & Cene Esclusive')),
    ('Massaggi & Benessere', _('Massaggi & Benessere')),
    ('Passeggiate a Cavallo', _('Passeggiate a Cavallo')),
    ('Golf & Tennis', _('Golf & Tennis')),
]
