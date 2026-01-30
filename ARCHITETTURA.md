# 🏛️ Villa Luxury - Architettura del Progetto

## Panoramica
Sistema di prenotazione per villa di lusso con pagamenti Stripe, sincronizzazione calendari e pannello admin.

---

## 📁 Struttura del Progetto

```
villa_luxury/
├── config/                      # Configurazione Django principale
│   ├── __init__.py
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py              # Settings comuni
│   │   ├── development.py       # Settings sviluppo
│   │   └── production.py        # Settings produzione
│   ├── urls.py                  # URL principale
│   ├── wsgi.py
│   └── asgi.py
│
├── apps/                        # Applicazioni Django
│   ├── core/                    # App principale (home, pagine statiche)
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── templates/core/
│   │
│   ├── villa/                   # Gestione villa e unità prenotabili
│   │   ├── models.py            # Villa, Unit, Amenity, Gallery
│   │   ├── views.py
│   │   ├── admin.py
│   │   ├── urls.py
│   │   └── templates/villa/
│   │
│   ├── booking/                 # Sistema prenotazioni
│   │   ├── models.py            # Booking, BlockedDate, Pricing
│   │   ├── views.py
│   │   ├── services.py          # Logica business (disponibilità, prezzi)
│   │   ├── forms.py
│   │   ├── admin.py
│   │   ├── urls.py
│   │   └── templates/booking/
│   │       ├── partials/        # Frammenti HTMX
│   │       │   ├── availability_calendar.html
│   │       │   ├── price_summary.html
│   │       │   └── booking_steps.html
│   │       ├── booking_form.html
│   │       └── booking_confirmation.html
│   │
│   ├── payments/                # Integrazione Stripe
│   │   ├── models.py            # Payment, PaymentLog
│   │   ├── views.py             # Checkout, webhooks
│   │   ├── services.py          # Stripe logic
│   │   ├── webhooks.py          # Webhook handlers
│   │   └── urls.py
│   │
│   ├── accounts/                # Autenticazione utenti
│   │   ├── models.py            # CustomUser, GuestProfile
│   │   ├── views.py             # Login, Register, Profile
│   │   ├── forms.py
│   │   ├── urls.py
│   │   └── templates/accounts/
│   │
│   └── dashboard/               # Pannello Admin personalizzato
│       ├── views.py             # Dashboard prenotazioni
│       ├── urls.py
│       └── templates/dashboard/
│
├── templates/                   # Templates globali
│   ├── base.html                # Layout principale
│   ├── components/              # Componenti riutilizzabili
│   │   ├── navbar.html
│   │   ├── footer.html
│   │   ├── hero.html
│   │   ├── modal.html
│   │   └── gallery.html
│   └── partials/                # Frammenti HTMX globali
│
├── static/                      # File statici
│   ├── css/
│   │   ├── input.css            # Tailwind input
│   │   └── output.css           # Tailwind compilato
│   ├── js/
│   │   ├── alpine-components.js
│   │   └── htmx-config.js
│   └── images/
│
├── media/                       # Upload utenti
│   ├── villa/
│   └── gallery/
│
├── requirements/
│   ├── base.txt
│   ├── development.txt
│   └── production.txt
│
├── docker/                      # Configurazione Docker (opzionale)
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── scripts/                     # Script utility
│   └── deploy.sh
│
├── manage.py
├── package.json                 # Per Tailwind
├── tailwind.config.js
├── .env.example
└── README.md
```

---

## 🗄️ Modelli Database (Schema)

### Core Models

```
┌─────────────────────────────────────────────────────────────────────┐
│                           VILLA                                      │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ name            │ VARCHAR(200)                                       │
│ slug            │ VARCHAR(200) UNIQUE                                │
│ description     │ TEXT                                               │
│ description_en  │ TEXT                                               │
│ address         │ TEXT                                               │
│ coordinates     │ POINT (lat, lng)                                   │
│ max_guests      │ INTEGER                                            │
│ bedrooms        │ INTEGER                                            │
│ bathrooms       │ INTEGER                                            │
│ is_active       │ BOOLEAN                                            │
│ created_at      │ TIMESTAMP                                          │
│ updated_at      │ TIMESTAMP                                          │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BOOKABLE_UNIT                                │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ villa           │ FK → Villa                                         │
│ name            │ VARCHAR(200) (es: "Intera Villa", "Suite Nord")    │
│ slug            │ VARCHAR(200)                                       │
│ description     │ TEXT                                               │
│ unit_type       │ ENUM (FULL_VILLA, APARTMENT, ROOM)                 │
│ base_price      │ DECIMAL(10,2) - prezzo/notte base                  │
│ max_guests      │ INTEGER                                            │
│ min_nights      │ INTEGER DEFAULT 2                                  │
│ is_active       │ BOOLEAN                                            │
│ sort_order      │ INTEGER                                            │
└─────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ 1:N
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          SEASON_PRICE                                │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ unit            │ FK → BookableUnit                                  │
│ name            │ VARCHAR(100) (es: "Alta Stagione")                 │
│ start_date      │ DATE                                               │
│ end_date        │ DATE                                               │
│ price_per_night │ DECIMAL(10,2)                                      │
│ min_nights      │ INTEGER                                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                           AMENITY                                    │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ name            │ VARCHAR(100)                                       │
│ icon            │ VARCHAR(50) - classe icona                         │
│ category        │ ENUM (COMFORT, OUTDOOR, SERVICES)                  │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                          GALLERY_IMAGE                               │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ villa           │ FK → Villa (nullable)                              │
│ unit            │ FK → BookableUnit (nullable)                       │
│ image           │ ImageField                                         │
│ alt_text        │ VARCHAR(200)                                       │
│ is_hero         │ BOOLEAN                                            │
│ sort_order      │ INTEGER                                            │
└─────────────────────────────────────────────────────────────────────┘
```

### Booking Models

```
┌─────────────────────────────────────────────────────────────────────┐
│                            BOOKING                                   │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ booking_number  │ VARCHAR(20) UNIQUE (es: VL-2026-00001)             │
│ unit            │ FK → BookableUnit                                  │
│ user            │ FK → User (nullable per guest)                     │
│                 │                                                    │
│ # Guest Info (se non loggato)                                        │
│ guest_name      │ VARCHAR(200)                                       │
│ guest_email     │ VARCHAR(254)                                       │
│ guest_phone     │ VARCHAR(20)                                        │
│                 │                                                    │
│ # Date                                                               │
│ check_in        │ DATE                                               │
│ check_out       │ DATE                                               │
│ num_guests      │ INTEGER                                            │
│                 │                                                    │
│ # Pricing                                                            │
│ subtotal        │ DECIMAL(10,2)                                      │
│ deposit_amount  │ DECIMAL(10,2) - acconto richiesto                  │
│ total_amount    │ DECIMAL(10,2)                                      │
│                 │                                                    │
│ # Status                                                             │
│ status          │ ENUM (PENDING, CONFIRMED, CANCELLED, COMPLETED)    │
│ payment_status  │ ENUM (PENDING, DEPOSIT_PAID, FULLY_PAID, REFUNDED) │
│                 │                                                    │
│ # Notes                                                              │
│ guest_notes     │ TEXT                                               │
│ admin_notes     │ TEXT                                               │
│                 │                                                    │
│ # Timestamps                                                         │
│ created_at      │ TIMESTAMP                                          │
│ updated_at      │ TIMESTAMP                                          │
│ confirmed_at    │ TIMESTAMP (nullable)                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                         BLOCKED_DATE                                 │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ unit            │ FK → BookableUnit                                  │
│ date            │ DATE                                               │
│ reason          │ ENUM (BOOKING, MAINTENANCE, OWNER, OTHER)          │
│ booking         │ FK → Booking (nullable)                            │
│ note            │ VARCHAR(200)                                       │
│                 │                                                    │
│ UNIQUE(unit, date)                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Payment Models

```
┌─────────────────────────────────────────────────────────────────────┐
│                           PAYMENT                                    │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ booking         │ FK → Booking                                       │
│ amount          │ DECIMAL(10,2)                                      │
│ payment_type    │ ENUM (DEPOSIT, BALANCE, FULL)                      │
│ status          │ ENUM (PENDING, COMPLETED, FAILED, REFUNDED)        │
│                 │                                                    │
│ # Stripe                                                             │
│ stripe_session_id      │ VARCHAR(200)                                │
│ stripe_payment_intent  │ VARCHAR(200)                                │
│ stripe_charge_id       │ VARCHAR(200)                                │
│                 │                                                    │
│ created_at      │ TIMESTAMP                                          │
│ completed_at    │ TIMESTAMP (nullable)                               │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        PAYMENT_LOG                                   │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ payment         │ FK → Payment                                       │
│ event_type      │ VARCHAR(100)                                       │
│ event_data      │ JSONB                                              │
│ created_at      │ TIMESTAMP                                          │
└─────────────────────────────────────────────────────────────────────┘
```

### User Models

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CUSTOM_USER                                  │
├─────────────────────────────────────────────────────────────────────┤
│ id              │ UUID PRIMARY KEY                                   │
│ email           │ VARCHAR(254) UNIQUE - username principale          │
│ first_name      │ VARCHAR(150)                                       │
│ last_name       │ VARCHAR(150)                                       │
│ phone           │ VARCHAR(20)                                        │
│ is_active       │ BOOLEAN                                            │
│ is_staff        │ BOOLEAN                                            │
│ date_joined     │ TIMESTAMP                                          │
│                 │                                                    │
│ # Per login semplificato                                             │
│ last_booking    │ FK → Booking (nullable)                            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Flusso Prenotazione

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                           FLUSSO PRENOTAZIONE                                 │
└──────────────────────────────────────────────────────────────────────────────┘

    ┌─────────────┐
    │  HOME PAGE  │
    └──────┬──────┘
           │
           ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  1. SELEZIONA UNITÀ                                         │
    │  - Mostra tutte le unità disponibili                        │
    │  - Card con immagini, descrizione, prezzo da               │
    │  [HTMX: carica preview disponibilità al hover]             │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  2. SELEZIONA DATE (HTMX)                                   │
    │  - Calendario interattivo                                   │
    │  - Date bloccate in grigio                                  │
    │  - Min nights enforcement                                   │
    │  [HTMX: aggiorna prezzi in tempo reale]                    │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  3. RIEPILOGO PREZZO (HTMX)                                 │
    │  - Calcolo notti x prezzo stagione                          │
    │  - Eventuali extra                                          │
    │  - Acconto richiesto (es: 30%)                              │
    │  - Saldo dovuto                                             │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  4. DATI OSPITE                                             │
    │  - Se loggato: dati precompilati                           │
    │  - Se guest: form nome, email, telefono                    │
    │  - Note speciali                                           │
    │  [Alpine: validazione client-side]                         │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  5. PAGAMENTO ACCONTO (Stripe Checkout)                     │
    │  - Redirect a Stripe Checkout                               │
    │  - Pagamento sicuro                                         │
    └──────────────────────────┬──────────────────────────────────┘
                               │
           ┌───────────────────┴───────────────────┐
           │                                       │
           ▼                                       ▼
    ┌─────────────┐                        ┌─────────────┐
    │   SUCCESS   │                        │   CANCEL    │
    └──────┬──────┘                        └──────┬──────┘
           │                                      │
           ▼                                      ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  WEBHOOK STRIPE                                             │
    │  - checkout.session.completed                               │
    │  - Crea BlockedDates per il periodo                        │
    │  - Aggiorna Booking.status = CONFIRMED                     │
    │  - Invia email conferma                                    │
    └──────────────────────────┬──────────────────────────────────┘
                               │
                               ▼
    ┌─────────────────────────────────────────────────────────────┐
    │  6. CONFERMA                                                │
    │  - Riepilogo prenotazione                                   │
    │  - PDF scaricabile                                          │
    │  - Istruzioni check-in                                      │
    │  - Email automatica con tutti i dettagli                   │
    └─────────────────────────────────────────────────────────────┘
```

---

## 🔗 Endpoint API / URLs

### Public URLs
```
/                               → Home page
/villa/                         → Dettaglio villa
/villa/<slug>/                  → Dettaglio unità
/prenota/                       → Wizard prenotazione
/prenota/conferma/<booking_id>/ → Pagina conferma
/contatti/                      → Pagina contatti
/servizi/                       → Servizi aggiuntivi
/gallery/                       → Galleria fotografica
/privacy/                       → Privacy policy
/termini/                       → Termini e condizioni
```

### HTMX Partials
```
/htmx/availability/             → Calendario disponibilità
/htmx/price-calc/               → Calcolo prezzo
/htmx/booking-step/<step>/      → Step wizard
```

### Auth URLs
```
/account/login/                 → Login (email + magic link opzionale)
/account/logout/                → Logout
/account/register/              → Registrazione
/account/profile/               → Profilo utente
/account/prenotazioni/          → Lista prenotazioni utente
```

### Payment URLs
```
/payment/checkout/<booking_id>/ → Crea sessione Stripe
/payment/success/               → Redirect success
/payment/cancel/                → Redirect cancel
/payment/webhook/               → Webhook Stripe
```

### Admin Dashboard
```
/dashboard/                     → Overview
/dashboard/prenotazioni/        → Lista prenotazioni
/dashboard/prenotazioni/<id>/   → Dettaglio prenotazione
/dashboard/calendario/          → Vista calendario
/dashboard/blocchi/             → Gestione blocchi manuali
/dashboard/report/              → Report e statistiche
```

---

## ⚡ Stack Tecnologico Dettagliato

### Backend
```
Django==5.0.x
psycopg[binary]==3.1.x          # PostgreSQL adapter
django-environ==0.11.x          # Environment variables
django-extensions==3.2.x        # Utilities
Pillow==10.x                    # Image processing
django-htmx==1.17.x             # HTMX integration
stripe==7.x                     # Stripe SDK
python-dateutil==2.8.x          # Date utilities
django-crispy-forms==2.1        # Form styling
crispy-tailwind==0.5.0          # Crispy + Tailwind
whitenoise==6.6.x               # Static files
gunicorn==21.x                  # WSGI server
```

### Frontend
```
Tailwind CSS 3.4.x
Alpine.js 3.x
HTMX 1.9.x
Flatpickr (calendar)
Swiper.js (gallery/slider)
```

### Database
```
PostgreSQL 15+
```

### Produzione VPS
```
Nginx (reverse proxy + static)
Gunicorn (WSGI)
Supervisor / systemd (process manager)
Certbot (SSL)
```

---

## 🎨 Tailwind Theme - Look Luxury

```javascript
// tailwind.config.js
module.exports = {
  theme: {
    extend: {
      colors: {
        // Palette luxury
        'villa': {
          50: '#faf9f7',
          100: '#f5f3ef',
          200: '#e8e4dc',
          300: '#d4cdc0',
          400: '#b8ad9a',
          500: '#9c8e78',
          600: '#8a7d69',
          700: '#736858',
          800: '#5f564a',
          900: '#4e473e',
          950: '#2a2521',
        },
        'gold': {
          400: '#d4af37',
          500: '#c5a028',
          600: '#a68523',
        },
      },
      fontFamily: {
        'serif': ['Cormorant Garamond', 'Georgia', 'serif'],
        'sans': ['Inter', 'system-ui', 'sans-serif'],
      },
      spacing: {
        '128': '32rem',
        '144': '36rem',
      },
    },
  },
}
```

---

## 📧 Email Templates

- `booking_confirmation.html` - Conferma prenotazione
- `booking_reminder.html` - Reminder check-in (3 giorni prima)
- `payment_receipt.html` - Ricevuta pagamento
- `welcome.html` - Benvenuto nuovo utente

---

## 🔒 Sicurezza

1. **CSRF Protection** - Django built-in
2. **XSS Protection** - Template escaping
3. **SQL Injection** - Django ORM
4. **Stripe Webhook Verification** - Signature check
5. **Rate Limiting** - django-ratelimit
6. **HTTPS Only** - In produzione
7. **Environment Variables** - Secrets fuori dal codice

---

## 📊 Admin Dashboard Features

1. **Overview**
   - Prenotazioni oggi/settimana/mese
   - Revenue totale
   - Occupancy rate

2. **Gestione Prenotazioni**
   - Filtri per stato, data, unità
   - Azioni: conferma, cancella, modifica
   - Note admin

3. **Calendario**
   - Vista mensile tutte le unità
   - Drag & drop blocchi
   - Colori per stato

4. **Blocchi Manuali**
   - Manutenzione
   - Uso proprietario
   - Eventi speciali

---

## 🚀 Deployment Checklist

```bash
# VPS Setup
□ Ubuntu 22.04 LTS
□ PostgreSQL 15
□ Python 3.11+
□ Nginx
□ Certbot SSL
□ Supervisor

# Django
□ DEBUG = False
□ ALLOWED_HOSTS configurato
□ SECRET_KEY sicuro
□ Database production
□ Static files collectstatic
□ Media storage configurato

# Stripe
□ Live API keys
□ Webhook endpoint registrato
□ Webhook secret configurato

# Monitoring
□ Error logging (Sentry opzionale)
□ Backup database automatico
```

---

## 📝 Note Implementazione

### Sincronizzazione Disponibilità
- La tabella `BlockedDate` è la **source of truth**
- Quando una prenotazione è CONFIRMED, crea i BlockedDate
- Quando cancellata, rimuove i BlockedDate
- Query disponibilità: `NOT EXISTS in BlockedDate for date range`

### Calcolo Prezzi
1. Trova SeasonPrice applicabile per ogni notte
2. Se non esiste, usa `BookableUnit.base_price`
3. Somma tutte le notti
4. Applica acconto (configurable, default 30%)

### Webhook Stripe (CRITICO)
- **Mai** confermare prenotazione senza webhook
- Idempotenza: controlla se già processato
- Log tutti gli eventi
- Retry automatico Stripe su failure

---

Questo documento serve come riferimento per tutto lo sviluppo.
Procediamo con l'implementazione modulo per modulo! 🚀
