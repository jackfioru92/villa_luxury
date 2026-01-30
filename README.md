# 🏛️ Villa Luxury

Sistema di prenotazione per villa di lusso con pagamenti Stripe.

## Stack Tecnologico

- **Backend**: Django 5.0 + PostgreSQL
- **Frontend**: Django Templates
- **CSS**: Tailwind CSS
- **UI Interattiva**: Alpine.js
- **Server-driven updates**: HTMX
- **Pagamenti**: Stripe Checkout + Webhooks

## Setup Sviluppo

### 1. Prerequisiti
- Python 3.11+
- Node.js 18+
- PostgreSQL (opzionale, usa SQLite in sviluppo)

### 2. Installazione

```bash
# Clona il repository
cd villa_luxury

# Crea virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o
.\venv\Scripts\activate  # Windows

# Installa dipendenze Python
pip install -r requirements/development.txt

# Copia e configura environment
cp .env.example .env
# Modifica .env con i tuoi settings

# Installa dipendenze Node (per Tailwind)
npm install

# Compila Tailwind CSS
npm run tailwind:build
```

### 3. Database

```bash
# Crea le migrazioni
python manage.py makemigrations

# Applica le migrazioni
python manage.py migrate

# Crea superuser
python manage.py createsuperuser
```

### 4. Avvia il server

```bash
# In un terminale - Django
python manage.py runserver

# In un altro terminale - Tailwind (watch mode)
npm run tailwind:watch
```

Visita http://localhost:8000

## Configurazione Stripe

1. Crea un account su [Stripe Dashboard](https://dashboard.stripe.com)
2. Ottieni le chiavi API (test mode)
3. Configura nel `.env`:
   ```
   STRIPE_PUBLIC_KEY=pk_test_...
   STRIPE_SECRET_KEY=sk_test_...
   ```

### Webhook Locale (sviluppo)

Per testare i webhook in locale:

```bash
# Installa Stripe CLI
brew install stripe/stripe-cli/stripe

# Login
stripe login

# Forward webhook
stripe listen --forward-to localhost:8000/payment/webhook/
```

Copia il webhook secret e aggiungilo al `.env`:
```
STRIPE_WEBHOOK_SECRET=whsec_...
```

## Struttura Progetto

```
villa_luxury/
├── apps/
│   ├── core/          # Home, pagine statiche
│   ├── villa/         # Villa e unità prenotabili
│   ├── booking/       # Sistema prenotazioni
│   ├── payments/      # Integrazione Stripe
│   ├── accounts/      # Autenticazione utenti
│   └── dashboard/     # Pannello admin
├── config/            # Settings Django
├── templates/         # Template globali
├── static/            # File statici
└── media/             # Upload utenti
```

## Deploy Produzione (VPS)

Vedi [ARCHITETTURA.md](ARCHITETTURA.md) per dettagli completi.

Quick start:
```bash
# Su VPS Ubuntu
sudo apt update && sudo apt install python3.11 postgresql nginx

# Setup virtual env e dipendenze
python3 -m venv venv
source venv/bin/activate
pip install -r requirements/production.txt

# Configura .env con DJANGO_ENV=production
# Configura PostgreSQL
# Configura Nginx + Gunicorn
# Configura SSL con Certbot
```

## Licenza

Proprietario - Tutti i diritti riservati.
