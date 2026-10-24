"""Settings module - sceglie development o production in base a DJANGO_ENV."""
import os
from pathlib import Path

import environ

# DJANGO_ENV sta nel .env, non nell'ambiente del processo: systemd passa solo
# PATH e il cron di sync_calendars.sh non passa nulla. base.py legge il .env,
# ma a quel punto il modulo e' gia' stato scelto, quindi lo leggiamo qui prima
# di decidere. read_env usa setdefault: le variabili che arrivano davvero
# dall'ambiente vincono sempre su quelle del file.
environ.Env.read_env(os.path.join(Path(__file__).resolve().parent.parent.parent, '.env'))

environment = os.environ.get('DJANGO_ENV', 'development')

if environment == 'production':
    from .production import *
else:
    from .development import *
