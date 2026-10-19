# Sincronizzazione calendari con i portali

Il sito e i portali (Booking.com, in futuro Airbnb) si scambiano le date
occupate via **iCal**: due flussi indipendenti, entrambi necessari.

```
   sito  ──── feed .ics (export) ────►  Booking.com
   sito  ◄─── feed .ics (import) ─────  Booking.com
```

iCal trasferisce **solo le date occupate**. Prezzi, soggiorno minimo e numero
ospiti restano da impostare a mano nell'Extranet di Booking (vedi
[PREZZIARIO.md](PREZZIARIO.md)); la propagazione non è istantanea, in genere
va dalla mezz'ora a qualche ora.

## Unità che condividono lo spazio

`All Structure` è fisicamente composta da `Suite Aura` e `Suite Silva`. Il
campo **Unità in conflitto** (admin → Unità prenotabili) le collega, così:

| Prenotata | Diventa occupata |
|-----------|------------------|
| Suite Aura | Suite Aura + All Structure (Silva resta libera) |
| Suite Silva | Suite Silva + All Structure (Aura resta libera) |
| All Structure | tutte e tre |

Vale sia per le prenotazioni dal sito sia per quelle importate dai portali, e
si riflette nei feed esportati: il calendario di `All Structure` contiene anche
le notti vendute sulle singole suite.

## 1. Export — dare il nostro calendario a Booking.com

Ogni unità ha un feed pubblico con token segreto. Per vedere gli URL:

```bash
cd /opt/altesiasuite/app && source /opt/altesiasuite/venv/bin/activate
python manage.py sync_calendars --show
```

L'URL ha questa forma (termina in `.ics`, requisito di Booking.com):

```
https://altesiasuite.com/calendario/all-structure/<token>.ics
```

Nell'Extranet: **Tariffe e disponibilità → Sincronizza calendari → Importa il
calendario della disponibilità**, incollare l'URL e confermare.

Il feed copre da 7 giorni fa a 2 anni avanti, non contiene dati personali
(solo intervalli con `SUMMARY:Occupato`) e non è indicizzabile. Se il token
dovesse trapelare, basta cambiarlo dall'admin: il vecchio URL smette di
funzionare e va reinserito nel portale.

## 2. Import — leggere il calendario di Booking.com

Nella stessa pagina dell'Extranet, Booking espone il **proprio** link `.ics`.
Va registrato dall'admin del sito:

**Django admin → Booking → Feed calendario → Aggiungi**
- *Unità*: All Structure
- *Canale*: Booking.com
- *URL feed .ics*: il link copiato dall'Extranet

Da lì in poi il cron lo rilegge ogni 15 minuti.

### Cron sul server

```bash
chmod +x /opt/altesiasuite/app/scripts/sync_calendars.sh
crontab -e
# aggiungere:
*/15 * * * * /opt/altesiasuite/app/scripts/sync_calendars.sh
```

Log in `/opt/altesiasuite/app/logs/calendar-sync.log`. Esecuzione manuale:

```bash
python manage.py sync_calendars          # sincronizza
python manage.py sync_calendars --show   # stato dei feed e URL da pubblicare
```

Lo stato di ogni feed (ultimo sync riuscito, errore, notti bloccate) è visibile
anche in admin nella lista **Feed calendario**.

## Comportamento in caso di problemi

- **Feed irraggiungibile**: le date già bloccate **restano bloccate**, l'errore
  viene registrato sul feed. Si preferisce perdere una prenotazione che
  incassarne due sulla stessa notte.
- **Prenotazione cancellata sul portale**: sparisce dal loro feed e il sync
  successivo riapre le date.
- **L'import non tocca mai le prenotazioni del sito**: cancella solo i blocchi
  con motivo *Canale esterno* appartenenti a quel feed.

## Limite noto

Le date si bloccano alla **conferma** della prenotazione (pagamento riuscito),
non all'avvio del checkout. Tra l'inizio di un pagamento sul sito e la
conferma la stessa notte resta esposta sul portale. Con la latenza iCal la
finestra di rischio reale è comunque dominata dai tempi di Booking.com.

Se in futuro si vendono anche le **singole suite** su più portali, conviene
passare a un channel manager (API, quasi in tempo reale, sincronizza anche i
prezzi): la sincronizzazione iCal di Booking.com va in quel caso disattivata.

## Test

```bash
python manage.py test apps.booking.tests.test_calendar_sync
```
