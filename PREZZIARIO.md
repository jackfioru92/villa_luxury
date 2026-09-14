# Prezziario Altèsia Suite

Tariffe a notte proposte per il primo anno. I valori applicati sul sito sono il
**punto medio** di ogni intervallo (`update_pricing --point mid`); si può
passare a `--point low` o `--point high` senza toccare il codice.

I prezzi vivono nel database (`villa.SeasonPrice`, modificabili anche
dall'admin Django). Il comando `update_pricing` li rigenera da zero a partire
dalle tabelle in `apps/villa/management/commands/update_pricing.py`.

## Struttura intera (8 ospiti) — unità di tipo "Intera Villa"

| Periodo                          | Intervallo proposto | Applicato |
|----------------------------------|--------------------:|----------:|
| Novembre – Marzo (esclusi festivi) | 590 – 690 €       |     640 € |
| Aprile – Maggio                  | 750 – 890 €         |     820 € |
| Giugno                           | 890 – 990 €         |     940 € |
| Luglio                           | 990 – 1.150 €       |   1.070 € |
| Agosto                           | 1.150 – 1.350 €     |   1.250 € |
| Settembre                        | 950 – 1.100 €       |   1.025 € |
| Ottobre                          | 790 – 950 €         |     870 € |
| Natale e Capodanno (20 dic – 6 gen) | 1.200 – 1.450 €  |   1.325 € |

Tariffa media reale attesa per il primo anno: 850–900 €/notte.

## Singola suite — unità di tipo "Camera" / "Appartamento"

Approccio prudente: non superare i 500 €/notte finché il marchio Altèsia non
sarà consolidato.

| Fascia          | Mesi                                   | Intervallo proposto | Applicato |
|-----------------|----------------------------------------|--------------------:|----------:|
| Bassa stagione  | Novembre – Marzo (esclusi festivi)     | 260 – 290 €         |     275 € |
| Media stagione  | Aprile, Maggio, Giugno, Ottobre        | 320 – 390 €         |     355 € |
| Alta stagione   | Luglio, Agosto, Settembre              | 420 – 490 €         |     455 € |
| Natale e Capodanno | 20 dic – 6 gen                      | 420 – 490 €         |     455 € |

## Note operative

- I periodi generati non si sovrappongono mai: la ricerca del prezzo prende il
  primo periodo per data di inizio, quindi Natale/Capodanno è "ritagliato"
  dall'inverno (1 nov – 19 dic, 20 dic – 6 gen, 7 gen – 31 mar).
- Il `base_price` di ogni unità (il prezzo "da €…" mostrato sul sito e usato
  come fallback per date senza periodo) viene impostato alla bassa stagione.
- Le notti minime restano quelle dell'unità; eventuali minimi per stagione
  (es. 5 notti a Capodanno) vanno impostati dall'admin sul singolo periodo.
- Le prenotazioni già confermate conservano i prezzi con cui sono state create.

## Aggiornare i prezzi sul server

```bash
cd /opt/altesiasuite/app && source /opt/altesiasuite/venv/bin/activate
python manage.py update_pricing --show      # situazione attuale
python manage.py update_pricing --dry-run   # anteprima
python manage.py update_pricing             # applica (anno corrente + successivo)
```
