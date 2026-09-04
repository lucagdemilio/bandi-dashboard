from __future__ import annotations
"""
Scraper per il catalogo incentivi di Invitalia (Agenzia nazionale per lo
sviluppo d'impresa).

Pagina catalogo:
  https://www.invitalia.it/per-le-imprese/incentivi-e-strumenti

Ogni incentivo è una card con un link a /incentivi-e-strumenti/<slug>, un
titolo, un breve testo e un'etichetta di stato ("Aperto", "In apertura",
"In arrivo", "Chiuso", "Sempre attivo"). Non essendoci una data di scadenza
strutturata nel catalogo, lo stato deriva da quell'etichetta; il link porta
alla scheda dove trovare i termini esatti.
"""
import re
from bs4 import BeautifulSoup
from .utils import safe_get

BASE = "https://www.invitalia.it"
CATALOGO_URL = f"{BASE}/per-le-imprese/incentivi-e-strumenti"

SLUG_RE = re.compile(r"^/incentivi-e-strumenti/[a-z0-9-]+$", re.IGNORECASE)

# Etichetta di stato (minuscolo) -> stato normalizzato.
STATO_MAP = {
    "aperto": "aperto",
    "aperta": "aperto",
    "in corso": "aperto",
    "in apertura": "aperto",
    "in arrivo": "aperto",
    "prossima apertura": "aperto",
    "sempre attivo": "aperto",
    "sportello": "aperto",
    "chiuso": "chiuso",
    "chiusa": "chiuso",
    "terminato": "chiuso",
}

STATI_NOTI = ["in apertura", "prossima apertura", "in arrivo", "sempre attivo",
              "in corso", "aperto", "aperta", "chiuso", "chiusa", "terminato", "sportello"]


def _card_container(anchor):
    """Risale di qualche livello per raggiungere il contenitore della card."""
    node = anchor
    for _ in range(4):
        if node.parent is not None:
            node = node.parent
    return node


def _estrai_stato(testo_card: str) -> tuple[str, str | None]:
    low = testo_card.lower()
    for etichetta in STATI_NOTI:
        if etichetta in low:
            return STATO_MAP.get(etichetta, "sconosciuto"), etichetta
    return "sconosciuto", None


def scrape() -> list[dict]:
    resp = safe_get(CATALOGO_URL)
    soup = BeautifulSoup(resp.text, "html.parser")

    # Raggruppa gli anchor per slug e scegli come titolo il testo più lungo
    # (scarta i link "Leggi tutto su ...").
    per_slug: dict[str, dict] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?")[0].rstrip("/")
        if not SLUG_RE.match(href):
            continue
        testo = a.get_text(" ", strip=True)
        if not testo or testo.lower().startswith("leggi tutto"):
            # tieni comunque traccia dello slug anche se qui manca il titolo
            per_slug.setdefault(href, {"titolo": "", "anchor": a})
            continue
        cur = per_slug.get(href)
        if cur is None or len(testo) > len(cur.get("titolo", "")):
            per_slug[href] = {"titolo": testo, "anchor": a}

    risultati = []
    for href, info in per_slug.items():
        titolo = info["titolo"] or href.split("/")[-1].replace("-", " ").title()
        card = _card_container(info["anchor"])
        testo_card = card.get_text(" ", strip=True) if card else ""
        stato, etichetta = _estrai_stato(testo_card)

        link = BASE + href
        risultati.append({
            "titolo": titolo,
            "ente": "Invitalia",
            "fonte": "Invitalia",
            "programma": None,
            "tipo_agevolazione": None,
            "settore": None,
            "beneficiari": "Imprese",
            "importo": None,
            "data_apertura": None,
            "data_scadenza": None,
            "scadenza_raw": etichetta,
            "link": link,
            "stato": stato,
            "note": (f"Stato dichiarato: {etichetta}. " if etichetta else "")
                    + "Verifica termini e scadenze sulla scheda Invitalia.",
        })

    if not risultati:
        raise RuntimeError(
            "Nessun incentivo estratto dal catalogo Invitalia. Verifica "
            f"{CATALOGO_URL} e il pattern dei link (/incentivi-e-strumenti/...)."
        )
    return risultati
