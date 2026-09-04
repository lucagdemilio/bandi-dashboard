from __future__ import annotations
"""
Scraper per IRFIS - FinSicilia S.p.A. (finanziaria della Regione Siciliana),
gestore del "Fondo Sicilia" e di misure agevolate per le imprese siciliane.

Dalla home (https://www.irfis.it/) si ricavano due cose:
  1) le "schede prodotto"/misure attive, riconoscibili dalla dicitura
     "DOTAZIONE FINANZIARIA <importo>" (es. FARE IMPRESA IN SICILIA,
     CONTRIBUTI MUTUI IMPRESE, EDICOLE, CLUSTER...);
  2) gli avvisi/notizie recenti, che in home hanno un prefisso data
     gg/mm/aaaa (es. "10/06/2026 Finanziamenti agevolati per...").

Se la home viene ridisegnata, aggiorna i pattern qui sotto.
"""
import re
from bs4 import BeautifulSoup
from .utils import safe_get, parse_data_ita

BASE = "https://www.irfis.it"
HOME_URL = f"{BASE}/"

DOTAZIONE_RE = re.compile(r"(.*?)DOTAZIONE FINANZIARIA\s*(.*)", re.IGNORECASE | re.DOTALL)
DATA_PREFIX_RE = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s+(.*)", re.DOTALL)


def _scrape_misure(soup) -> list[dict]:
    risultati = []
    visti = set()
    for a in soup.find_all("a", href=True):
        testo = a.get_text(" ", strip=True)
        if "DOTAZIONE FINANZIARIA" not in testo.upper():
            continue
        href = a["href"]
        if href in visti:
            continue
        visti.add(href)

        m = DOTAZIONE_RE.search(testo)
        titolo = (m.group(1).strip() if m else testo).strip(" -–")
        dotazione = m.group(2).strip() if m else ""
        # normalizza "38,6 milioni" -> importo leggibile
        dot_match = re.search(r"[\d.,]+\s*(?:mln|milion[ie]|mila|€|euro)?", dotazione, re.IGNORECASE)
        importo = ("Dotazione: " + dot_match.group(0).strip()) if dot_match else None

        if not titolo:
            continue
        risultati.append({
            "titolo": titolo.title() if titolo.isupper() else titolo,
            "ente": "IRFIS - FinSicilia",
            "fonte": "IRFIS",
            "programma": "Fondo Sicilia",
            "tipo_agevolazione": "Finanziamento agevolato / Contributo",
            "settore": None,
            "beneficiari": "Imprese siciliane",
            "importo": importo,
            "data_apertura": None,
            "data_scadenza": None,
            "scadenza_raw": None,
            "link": href if href.startswith("http") else BASE + href,
            "stato": "aperto",
            "note": "Misura IRFIS attiva - verifica termini e requisiti sulla scheda.",
        })
    return risultati


def _scrape_avvisi(soup) -> list[dict]:
    risultati = []
    visti = set()
    for a in soup.find_all("a", href=True):
        testo = a.get_text(" ", strip=True)
        m = DATA_PREFIX_RE.match(testo)
        if not m:
            continue
        data_pub = parse_data_ita(m.group(1))
        titolo = re.sub(r"\s+", " ", m.group(2)).strip()
        href = a["href"]
        if not titolo or len(titolo) < 8:
            continue
        chiave = (titolo[:60], href)
        if chiave in visti:
            continue
        visti.add(chiave)

        # Tieni solo gli avvisi rilevanti per le imprese/finanza agevolata.
        if not any(k in titolo.lower() for k in
                   ["finanz", "impres", "bando", "avviso", "misura", "fondo",
                    "contribut", "credito", "agevol", "editori", "edicol", "povert"]):
            continue

        risultati.append({
            "titolo": titolo,
            "ente": "IRFIS - FinSicilia",
            "fonte": "IRFIS",
            "programma": "Fondo Sicilia",
            "tipo_agevolazione": None,
            "settore": None,
            "beneficiari": "Imprese siciliane",
            "importo": None,
            "data_apertura": None,
            "data_scadenza": None,
            "scadenza_raw": None,
            "link": href if href.startswith("http") else BASE + href,
            "stato": "sconosciuto",
            "note": f"Avviso pubblicato il {data_pub or m.group(1)} - verifica scadenza sulla scheda.",
        })
    return risultati


def scrape() -> list[dict]:
    resp = safe_get(HOME_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    risultati = _scrape_misure(soup) + _scrape_avvisi(soup)

    # dedup finale per (titolo, link)
    visti, unici = set(), []
    for r in risultati:
        k = (r["titolo"].lower()[:60], r.get("link"))
        if k in visti:
            continue
        visti.add(k)
        unici.append(r)

    if not unici:
        raise RuntimeError(
            "Nessuna misura/avviso estratto da IRFIS. La home potrebbe essere "
            f"cambiata: verifica {HOME_URL} e aggiorna i pattern in irfis_scraper.py."
        )
    return unici
