# Deployment Guide - Altesia Suite

## 📋 Deployment sul Server

### Metodo 1: Pull Manuale (Attuale)

Dopo aver fatto il commit su GitHub, devi accedere al server e fare il pull:

```bash
# 1. Accedi al server via SSH
ssh debian@57.131.42.4

# 2. Vai nella directory dell'applicazione
cd /opt/altesiasuite/app

# 3. Attiva l'ambiente virtuale
source /opt/altesiasuite/venv/bin/activate

# 4. Fai il pull delle modifiche da GitHub
git pull origin main

# 5. Installa eventuali nuove dipendenze
pip install -r requirements/production.txt

# 6. Esegui le migrations (se necessario)
python manage.py migrate

# 7. Raccogli i file statici (se modificati)
python manage.py collectstatic --noinput

# 8. Riavvia Gunicorn
sudo systemctl restart altesiasuite
```

### Metodo 2: Script di Deploy Automatico (Consigliato)

Creare uno script sul server per automatizzare il processo:

```bash
# File: /opt/altesiasuite/deploy.sh
#!/bin/bash
set -e

echo "🚀 Deployment in corso..."

cd /opt/altesiasuite/app
source /opt/altesiasuite/venv/bin/activate

echo "📥 Pull da GitHub..."
git pull origin main

echo "📦 Installazione dipendenze..."
pip install -r requirements/production.txt

echo "🗄️  Esecuzione migrations..."
python manage.py migrate --noinput

echo "📦 Raccolta file statici..."
python manage.py collectstatic --noinput

echo "🔄 Riavvio Gunicorn..."
sudo systemctl restart altesiasuite

echo "✅ Deployment completato!"
```

Per usare lo script:
```bash
# Rendi eseguibile lo script
chmod +x /opt/altesiasuite/deploy.sh

# Esegui il deploy
/opt/altesiasuite/deploy.sh
```

### Metodo 3: Webhook GitHub (Automatico - Avanzato)

Setup per deployment automatico al push su GitHub:

1. Installa webhook server
2. Configura GitHub webhook
3. Il server reagisce automaticamente ai push

## 🔧 Modalità Manutenzione

Per attivare/disattivare la pagina di manutenzione:

```bash
# Nel file /opt/altesiasuite/app/.env
MAINTENANCE_MODE=True   # Attiva manutenzione
MAINTENANCE_MODE=False  # Disattiva manutenzione

# Dopo aver modificato, riavvia l'applicazione
sudo systemctl restart altesiasuite
```

**Nota**: Gli utenti admin possono accedere anche durante la manutenzione.

## 📝 Checklist Pre-Deployment

- [ ] Testato in locale
- [ ] Commit e push su GitHub
- [ ] Backup database
- [ ] Verificare variabili d'ambiente sul server
- [ ] Eseguire migrations
- [ ] Raccogliere file statici
- [ ] Riavviare servizi

## 🔐 SSL/HTTPS

Una volta che il DNS è propagato, configurare SSL:

```bash
sudo certbot --nginx -d altesiasuite.it -d www.altesiasuite.it -d altesiasuite.com -d www.altesiasuite.com
```

Il rinnovo automatico è già configurato da certbot.

## 📊 Monitoraggio

### Log Gunicorn
```bash
# Access log
tail -f /opt/altesiasuite/app/logs/gunicorn-access.log

# Error log
tail -f /opt/altesiasuite/app/logs/gunicorn-error.log
```

### Log Nginx
```bash
# Access log
sudo tail -f /var/log/nginx/access.log

# Error log
sudo tail -f /var/log/nginx/error.log
```

### Status servizi
```bash
# Gunicorn
sudo systemctl status altesiasuite

# Nginx
sudo systemctl status nginx

# PostgreSQL
sudo systemctl status postgresql
```

## 🔄 Rollback (ripristino versione precedente)

```bash
cd /opt/altesiasuite/app
git log --oneline  # Trova il commit precedente
git reset --hard COMMIT_ID
sudo systemctl restart altesiasuite
```

## 📌 Note Importanti

1. **Il push su GitHub NON aggiorna automaticamente il server** - devi fare il pull manualmente o configurare un webhook
2. Sempre fare backup del database prima di deployment importanti
3. Testare in locale prima di fare deployment in produzione
4. Controllare i log dopo ogni deployment
