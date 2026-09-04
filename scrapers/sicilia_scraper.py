from __future__ import annotations
"""
Scraper per i bandi/avvisi del portale della Regione Siciliana.

Il portale (regione.sicilia.it) è un sito Drupal che espone le voci come
"card" ripetute. Struttura reale (verificata):

  <article class="res-card-competition-announcement ...">
     <span class="res-card-competition-announcement__category">Avvisi pubblici</span>
     <h5 class="res-card-competition-announcement__title">
        <a href="/istituzioni/..." title="TITOLO COMPLETO">TITOLO ...</a>
     </h5>
     <p class="date">07/10/2026 - 23:59</p>   (preceduto da "Scade il:")
     ... eventuale badge "Scaduto"
  </article>

La pagina è paginata con ?page=0,1,2...  Se la struttura HTML cambia,
ispeziona la pagina con gli strumenti sviluppatore e aggiorna i selettori.
"""
import re
from bs4 import BeautifulSoup
from .utils import safe_get, parse_data_ita, stato_da_scadenza

BASE = "https://www.regione.sicilia.it"
BANDI_URL = f"{BASE}/istituzioni/servizi-informativi/bandi"

CARD_SEL = "article.res-card-competition-announcement, article"
TITLE_SEL = ".res-card-competition-announcement__title a, h5 a"
CATEGORY_SEL = ".res-card-competition-announcement__category"


def _parse_card(card) -> dict | None:
    link_tag = card.select_one(TITLE_SEL) or card.find("a", href=True)
    if not link_tag:
        return None

    # Il testo visibile è il titolo completo; l'attributo title ha spesso il
    # prefisso "Vai a ..." da ripulire come fallback.
    testo_visibile = link_tag.get_text(" ", strip=True)
    attr_title = re.sub(r"^\s*Vai a\s+", "", link_tag.get("title", ""), flags=re.IGNORECASE).strip()
    titolo = testo_visibile if len(testo_visibile) >= len(attr_title) else attr_title
    titolo = (titolo or attr_title or testo_visibile).strip()
    if not titolo:
        return None

    link = link_tag.get("href")
    if link and link.startswith("/"):
        link = BASE + link

    cat_tag = card.select_one(CATEGORY_SEL)
    categoria = cat_tag.get_text(strip=True) if cat_tag else None

    data_tag = card.select_one("p.date")
    scadenza_raw = data_tag.get_text(" ", strip=True) if data_tag else None
    scadenza_iso = parse_data_ita(scadenza_raw) if scadenza_raw else None

    testo = card.get_text(" ", strip=True)
    if "scaduto" in testo.lower():
        stato = "chiuso"
    else:
        stato = stato_da_scadenza(scadenza_iso) if scadenza_iso else "aperto"

    return {
        "titolo": titolo,
        "ente": "Regione Siciliana",
        "fonte": "Regionale Sicilia",
        "programma": None,
        "tipo_agevolazione": None,
        "settore": categoria,
        "beneficiari": None,
        "importo": None,
        "data_apertura": None,
        "data_scadenza": scadenza_iso,
        "scadenza_raw": scadenza_raw,
        "link": link,
        "stato": stato,
        "note": f"Categoria portale: {categoria}" if categoria else "Portale bandi Regione Siciliana",
    }


def scrape(max_pagine: int = 8, solo_aperti: bool = True) -> list[dict]:
    risultati = []
    visti = set()
    for pagina in range(max_pagine):
        url = f"{BANDI_URL}?page={pagina}"
        try:
            resp = safe_get(url)
        except Exception:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        cards = soup.select(CARD_SEL)
        if not cards:
            break

        nuovi = 0
        for card in cards:
            rec = _parse_card(card)
            if not rec:
                continue
            chiave = (rec["titolo"], rec.get("link"))
            if chiave in visti:
                continue
            visti.add(chiave)
            nuovi += 1
            risultati.append(rec)
        if nuovi == 0:
            break

    if solo_aperti:
        risultati = [r for r in risultati if r["stato"] != "chiuso"]

    if not risultati:
        raise RuntimeError(
            "Nessun bando estratto dal portale Regione Siciliana. La struttura "
            f"HTML potrebbe essere cambiata: verifica {BANDI_URL} e aggiorna i "
            "selettori in sicilia_scraper.py."
        )
    return risultati
