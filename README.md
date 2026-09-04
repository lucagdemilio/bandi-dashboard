# Dashboard Bandi — Finanza Agevolata (UE / Nazionale / Invitalia / Sicilia / IRFIS)

Dashboard locale in Streamlit che raccoglie automaticamente i bandi di
finanza agevolata per le imprese da cinque fonti e li rende filtrabili,
ricercabili ed esportabili in un'unica interfaccia.

## 1. Installazione

```bash
cd bandi_dashboard
python3 -m venv venv
source venv/bin/activate      # su Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> Nota: il progetto è stato testato con Python 3.9. Tutti i moduli usano
> `from __future__ import annotations`, quindi funziona anche su 3.9+ senza
> problemi con i type hint moderni.

## 2. Avvio

```bash
streamlit run app.py
```

Si apre nel browser su `http://localhost:8501`.

Al primo avvio il database è vuoto: premi il pulsante **"🔄 Aggiorna"** in alto
a destra (accanto al titolo) per lanciare gli scraper e popolare i dati (~30-60s).
Sui dispositivi touch è disponibile anche il **pull-to-refresh** (swipe verso il
basso dall'inizio della pagina). La sidebar è nascosta: filtri e ricerca sono nel
pannello a tendina **"🔍 Filtri e ricerca"** in pagina.

## 3. Struttura del progetto

```
bandi_dashboard/
├── .streamlit/config.toml     # tema (palette istituzionale)
├── app.py                     # interfaccia Streamlit (layout, filtri, KPI)
├── ui.py                      # CSS + componenti (card bando, badge, KPI)
├── database.py                # SQLite: schema, upsert, query
├── scrapers/
│   ├── __init__.py            # orchestratore (esegue tutte le fonti)
│   ├── utils.py               # sessione HTTP, parsing date, pulizia testo
│   ├── eu_scraper.py          # UE — EU Funding & Tenders Portal (API SEDIA)
│   ├── nazionale_scraper.py   # Nazionale — incentivi.gov.it (indice Solr)
│   ├── invitalia_scraper.py   # Invitalia — catalogo incentivi e strumenti
│   ├── sicilia_scraper.py     # Regione Siciliana — portale bandi
│   └── irfis_scraper.py       # IRFIS-FinSicilia — misure Fondo Sicilia
└── data/
    └── bandi.db               # creato al primo avvio
```

## 4. Le cinque fonti (metodo e affidabilità)

Tutti gli scraper sono stati **testati dal vivo** e funzionanti a settembre 2026.

| Fonte | Metodo | Note di robustezza |
|-------|--------|--------------------|
| **UE** | API di ricerca SEDIA del portale F&T | Endpoint pubblico non ufficialmente documentato. Dettaglio critico: `query` e `languages` vanno inviati come **parti multipart `application/json`** (blob), `pageSize`/`pageNumber` nella query string. L'ultima risposta grezza è salvata in `data/_debug_eu_raw.json`. |
| **Nazionale** | Indice Solr di incentivi.gov.it | La fonte più ricca e stabile (stesso endpoint dei pulsanti "Scarica JSON/CSV" della sezione Open Data, licenza IODL 2.0). Usa l'host `www.incentivi.gov.it`. Filtrato su misure nazionali + quelle che includono la Sicilia. |
| **Invitalia** | Scraping HTML del catalogo | Pagina `/per-le-imprese/incentivi-e-strumenti`. Estrae titolo, link e stato dichiarato ("Aperto/In apertura/..."). |
| **Regione Sicilia** | Scraping HTML (Drupal) | Portale bandi istituzionale. Selettori `article.res-card-competition-announcement`, data in `p.date`. Mescola avvisi e gare: la categoria è nel campo *Settore*. |
| **IRFIS** | Scraping HTML della home | Estrae le misure "Fondo Sicilia" (dicitura *DOTAZIONE FINANZIARIA*) e gli avvisi datati recenti. |

Le tre fonti in **scraping HTML** (Invitalia, Sicilia, IRFIS) sono le più
fragili: se i siti vengono ridisegnati, i selettori/pattern nei rispettivi
file vanno aggiornati ispezionando la pagina con gli strumenti sviluppatore.
Ogni scraper solleva un'eccezione descrittiva se non estrae nulla, e l'errore
compare nel pannello laterale della dashboard.

## 5. Aggiornamento automatico giornaliero

Lo script `aggiorna_bandi.py` esegue tutti gli scraper senza aprire
l'interfaccia e scrive un log in `data/refresh.log`. Si lancia anche a mano:

```bash
venv/bin/python aggiorna_bandi.py
```

### macOS — LaunchAgent (già configurato)

L'aggiornamento gira **ogni giorno alle 07:00** tramite un LaunchAgent
installato in `~/Library/LaunchAgents/com.studiolc.bandi.refresh.plist`.
Se il Mac è spento/in sospensione, launchd recupera l'esecuzione al risveglio.

> ⚠️ **Cartella non protetta**: il progetto vive in `~/bandi_dashboard` (NON
> sul Desktop). Su macOS, Desktop/Documenti/Download sono protetti da TCC e i
> processi in background (launchd, cron) non possono leggerli → l'aggiornamento
> automatico fallirebbe con `Operation not permitted`. Sul Desktop c'è solo un
> collegamento ("Bandi Dashboard").

Comandi utili:
```bash
launchctl list | grep bandi                       # stato (0 = ultimo run OK)
launchctl kickstart -k gui/$(id -u)/com.studiolc.bandi.refresh   # esegui subito
launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.studiolc.bandi.refresh.plist  # disattiva
```
Per cambiare orario: modifica `Hour`/`Minute` nel `.plist`, poi `bootout` + `bootstrap`.

### Linux / deploy online — cron

Sul server dove verrà pubblicata la dashboard (contesto cross-platform), lo
stesso script si schedula con cron, senza i vincoli TCC di macOS:
```bash
0 7 * * * cd /percorso/bandi_dashboard && venv/bin/python aggiorna_bandi.py
```

La dashboard legge sempre l'ultimo stato del database, quindi non serve
riavviarla dopo un aggiornamento in background.

## 6. Personalizzazioni rapide

- **UE — tipo di bando**: in `eu_scraper.py`, `TYPES` (`"1"` = grants) e
  `STATUSES` (`31094501` = in arrivo, `31094502` = aperto). `max_pages`
  controlla quanti bandi scaricare (default 6 pagine × 100).
- **UE — focus imprese**: ogni bando UE è classificato per beneficiari in
  `classifica_beneficiari()` — *Imprese/PMI*, *Imprese in consorzio R&I*,
  *Ricerca/Università*. Nella dashboard il flag **"🏢 Solo pertinenti a
  imprese"** (attivo di default) nasconde la categoria *Ricerca/Università*
  (MSCA, ERC, borse, dottorati); il filtro **Beneficiari** permette di
  restringere ulteriormente (es. solo *Imprese/PMI*). Regole in `_PROG_IMPRESE`
  e `_RICERCA_RE`.
- **Nazionale — pertinenza territoriale**: in `nazionale_scraper.py`,
  `REGIONI_NAZIONALE` (soglia oltre cui un incentivo è considerato nazionale).
  Passa `solo_rilevanti=False` a `scrape()` per includere tutte le regioni.
- **IRFIS / Invitalia / Sicilia — parole chiave e selettori**: in cima ai
  rispettivi file (pattern regex e selettori CSS).
- **Intestazione / branding**: funzione `brand_title()` in `ui.py`
  (monogramma "SLC", nome studio, sottotitolo) e palette in `.streamlit/config.toml`.
- **Filtro ATECO**: nel pannello filtri in pagina, il campo *Codice ATECO
  azienda* incrocia il codice del cliente con i codici ATECO del bando
  (fonte nazionale). Un bando è compatibile se è "Tutti i settori" o se un
  codice combacia gerarchicamente (es. `56` ⊃ `56.10`). Il flag *Solo settore
  compatibile* nasconde i bandi privi di classificazione ATECO (UE/regionali).
  Logica in `scrapers/utils.py` → `ateco_status()`.
- **Macro-settori**: lista `SETTORI_MACRO` in `app.py` (filtro *Settore*).

## 7. Note sul database

- I record vengono aggiornati con *upsert* (chiave = hash di fonte+titolo+link),
  quindi rilanciare gli scraper non crea duplicati.
- I bandi che spariscono dalla fonte **restano** nel DB fino a nuova cancellazione
  manuale: per ripartire da uno stato pulito, elimina `data/bandi.db` e ri-aggiorna.

## 8. Deploy online — Streamlit Community Cloud (gratuito)

L'app può girare online, sempre disponibile e senza dipendere dal Mac, restando
gratuita. Architettura:

- **Streamlit Community Cloud** ospita l'app (repo GitHub privato).
- **GitHub Actions** (`.github/workflows/refresh.yml`) esegue `aggiorna_bandi.py`
  ogni giorno, committa `data/bandi.db` aggiornato → l'app si ricarica con i dati
  freschi. (Sostituisce il launchd del Mac; quello locale resta valido se usi
  anche la versione locale.)

### Passi (una tantum)

1. **Crea un repository GitHub privato** e caricaci questa cartella:
   ```bash
   cd ~/bandi_dashboard
   git init && git add -A && git commit -m "Dashboard bandi"
   git branch -M main
   git remote add origin https://github.com/<tuo-utente>/bandi-dashboard.git
   git push -u origin main
   ```
2. Vai su **share.streamlit.io** → *Create app* → seleziona il repo, branch `main`,
   file `app.py` → **Deploy**.
3. **Rendi l'app privata**: nelle impostazioni dell'app su Streamlit Cloud
   (*Settings → Sharing*) imposta *Who can view* su privato e aggiungi le email
   autorizzate (tu ed eventuali collaboratori).
4. **Abilita GitHub Actions**: nel repo, tab *Actions*, conferma l'attivazione dei
   workflow. Il refresh parte poi ogni giorno (o manualmente da *Run workflow*).

Nessun segreto/API key da configurare: tutte le fonti sono pubbliche.

> **Privacy**: oggi l'app contiene solo dati pubblici (bandi), quindi l'hosting è
> senza rischi. Quando aggiungeremo il *portafoglio clienti* (aziende + ATECO),
> valuteremo dove tenere quei dati (cifrati o su istanza privata).
