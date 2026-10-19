# Prezziario Altèsia

Tariffe a notte della **struttura intera**, pernottamento con **colazione
inclusa**. Definite dalla proprietà il 19 ottobre 2026.

Le singole suite non si prenotano separatamente: restano visibili sul sito con
foto e descrizione, ma la struttura si vende solo per intero.

## Tariffe

| Periodo | €/notte |
|---------|--------:|
| Novembre – Marzo (esclusi i festivi) | 1.000 |
| **8 dicembre – 6 gennaio** | 1.600 |
| **Settimana di Pasqua** | 1.500 |
| Aprile – Maggio | 1.200 |
| Giugno | 1.200 |
| Luglio | 1.500 |
| Agosto | 1.500 |
| **Settimana di Ferragosto (9 – 15 agosto)** | 1.700 |
| Settembre | 1.200 |
| Ottobre | 1.000 |

### Periodi speciali

- **Natale e Capodanno**: dall'8 dicembre al 6 gennaio compreso.
- **Settimana di Pasqua**: le 7 notti che terminano con il lunedì dell'Angelo
  (dal martedì precedente la Pasqua a Pasquetta compresa). La data è mobile e
  viene calcolata ogni anno: nel 2027 Pasqua cade il 28 marzo, quindi la
  settimana ricade dentro la fascia Novembre–Marzo e viene ritagliata da
  quella; nel 2028 cade il 16 aprile e viene ritagliata da Aprile–Maggio.
- **Settimana di Ferragosto**: notti dal 9 al 15 agosto, check-out il 16.
  Il resto di agosto resta a 1.500 €.

## Note operative

- I periodi generati non si sovrappongono mai e non lasciano buchi: la ricerca
  del prezzo prende il primo periodo per data di inizio, quindi un periodo
  contenuto in un altro non verrebbe mai applicato e un buco farebbe ricadere
  la notte sul `base_price`.
- Il `base_price` (il prezzo "da €…" mostrato sul sito) viene allineato alla
  tariffa più bassa, cioè 1.000 €.
- Le notti minime restano quelle dell'unità; eventuali minimi per stagione
  (es. 5 notti a Capodanno) si impostano dall'admin sul singolo periodo.
- Le prenotazioni già confermate conservano i prezzi con cui sono state create.
- Le unità non prenotabili singolarmente non hanno prezzi stagionali: il
  comando rimuove quelli eventualmente rimasti.

## Aggiornare i prezzi

Si modificano le costanti e le tabelle in cima a
`apps/villa/management/commands/update_pricing.py`, poi si rilancia il comando
sul server: rigenera l'intero listino fino al 2030.

```bash
cd /opt/altesiasuite/app && source /opt/altesiasuite/venv/bin/activate
python manage.py update_pricing --show      # situazione attuale
python manage.py update_pricing --dry-run   # anteprima
python manage.py update_pricing             # applica (anno corrente -> 2030)
python manage.py update_pricing --until 2032  # orizzonte più lungo
```

## Test

```bash
python manage.py test apps.villa.tests.test_pricing
```
