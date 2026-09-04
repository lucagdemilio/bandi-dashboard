from __future__ import annotations
"""
Scraper per il portale EU Funding & Tenders (SEDIA).

Usa l'endpoint di ricerca pubblico che alimenta il portale ufficiale.
Dettaglio tecnico importante (scoperto ispezionando le chiamate reali del
portale): i campi `query` e `languages` devono essere inviati come PARTI
multipart di tipo `application/json` (dei "blob"), NON come semplici campi
di testo — altrimenti il gateway risponde 500. I parametri di paginazione
(`pageSize`, `pageNumber`) vanno invece nella query string dell'URL.

Se un giorno l'endpoint cambia, la risposta grezza dell'ultima pagina viene
salvata in data/_debug_eu_raw.json per aiutare la ricalibrazione.
"""
import json
from datetime import datetime
from pathlib import Path
from .utils import safe_post, parse_data_ita, stato_da_scadenza, clean_html, first

SEARCH_URL = "https://api.tech.ec.europa.eu/search-api/prod/rest/search"
API_KEY = "SEDIA"
RAW_DEBUG_PATH = Path(__file__).parent.parent / "data" / "_debug_eu_raw.json"

# type: "1" = grants / calls for proposals (i bandi veri e propri per beneficiari).
# status: 31094501 = Forthcoming (in arrivo), 31094502 = Open (aperto).
TYPES = ["1"]
STATUSES = ["31094501", "31094502"]

# Mappatura prefisso identifier -> nome leggibile del programma.
PROGRAMMI = {
    "HORIZON": "Horizon Europe",
    "ERASMUS": "Erasmus+",
    "LIFE": "Programma LIFE",
    "CEF": "Connecting Europe Facility",
    "DIGITAL": "Digital Europe",
    "CREA": "Creative Europe",
    "SMP": "Single Market Programme",
    "COSME": "COSME",
    "EU4H": "EU4Health",
    "CERV": "Citizens, Equality, Rights and Values",
    "JUST": "Justice Programme",
    "AMIF": "Asylum, Migration and Integration Fund",
    "ISF": "Internal Security Fund",
    "BMVI": "Border Management and Visa Instrument",
    "EMFAF": "European Maritime, Fisheries and Aquaculture Fund",
    "EDF": "European Defence Fund",
    "IMCAP": "Common Agricultural Policy",
    "RFCS": "Research Fund for Coal and Steel",
    "PERF": "Single Market / Performance",
    "NDICI": "Global Europe (NDICI)",
    "I3": "Interregional Innovation Investments (I3)",
}


def _programma_da_identifier(identifier: str | None) -> str | None:
    if not identifier:
        return None
    prefix = identifier.split("-")[0].upper()
    return PROGRAMMI.get(prefix, prefix.title() if prefix else None)


# --- Classificazione per beneficiari (per una dashboard focalizzata imprese) ---
import re as _re

# Strumenti puramente accademici / individuali: NON rivolti alle imprese.
_RICERCA_RE = _re.compile(
    r"MSCA|ERC\b|Doctoral|Postdoc|Fellowship|COFUND|Prize|Citizen|Training Network",
    _re.IGNORECASE,
)
# Programmi con prefisso identifier tipicamente rivolti a imprese/mercato.
_PROG_IMPRESE = {"DIGITAL", "LIFE", "EDF", "CEF", "I3", "SMP", "COSME",
                 "INNOVFUND", "EIE", "EIC", "CREA"}


def classifica_beneficiari(md: dict) -> str:
    """Ritorna una delle etichette: 'Imprese/PMI', 'Imprese in consorzio R&I',
    'Ricerca/Università'. Serve a filtrare i bandi realmente utili alle imprese."""
    toa = md.get("typesOfAction")
    toa = " ".join(toa) if isinstance(toa, list) else str(toa or "")
    identifier = str(first(md.get("identifier")) or "")
    prefix = identifier.split("-")[0].upper()
    up = identifier.upper()

    if _RICERCA_RE.search(toa) or _RICERCA_RE.search(identifier):
        return "Ricerca/Università"
    # Innovation Actions (ma NON "Research and Innovation Actions") = vicino al mercato.
    is_ia = bool(_re.search(r"Innovation Action", toa, _re.IGNORECASE)) and not \
        _re.search(r"Research and Innovation", toa, _re.IGNORECASE)
    if is_ia or "EIC" in up or "EIE" in up or prefix in _PROG_IMPRESE:
        return "Imprese/PMI"
    return "Imprese in consorzio R&I"


def _build_files(page_size: int):
    query = {
        "bool": {
            "must": [
                {"terms": {"type": TYPES}},
                {"terms": {"status": STATUSES}},
            ]
        }
    }
    # Le parti DEVONO avere content-type application/json (blob), da qui la tupla a 3.
    return {
        "query": ("blob", json.dumps(query), "application/json"),
        "languages": ("blob", json.dumps(["it", "en"]), "application/json"),
    }


def _scegli_scadenza(deadline_val):
    """I bandi possono avere più cut-off (lista di date). Sceglie la prossima
    scadenza futura; se sono tutte passate, l'ultima. Ritorna (iso, raw)."""
    if not deadline_val:
        return None, None
    valori = deadline_val if isinstance(deadline_val, list) else [deadline_val]
    date_iso = sorted({parse_data_ita(v) for v in valori if parse_data_ita(v)})
    if not date_iso:
        return None, str(first(valori))
    oggi = datetime.now().date().isoformat()
    future = [d for d in date_iso if d >= oggi]
    scelta = future[0] if future else date_iso[-1]
    return scelta, scelta


def _normalizza(item: dict) -> dict:
    md = item.get("metadata", {}) or {}

    titolo = clean_html(first(md.get("title"))) or "Titolo non disponibile"
    identifier = first(md.get("identifier")) or item.get("reference")
    scadenza_iso, scadenza_raw = _scegli_scadenza(md.get("deadlineDate"))
    apertura_iso = parse_data_ita(first(md.get("startDate")))
    status_code = first(md.get("status"))

    link = item.get("url")
    if not link and identifier:
        link = ("https://ec.europa.eu/info/funding-tenders/opportunities/portal/"
                f"screen/opportunities/topic-details/{identifier}")

    # Scarichiamo solo bandi Forthcoming/Open: per definizione sono "aperti".
    stato = "aperto" if status_code in STATUSES else stato_da_scadenza(scadenza_iso)

    return {
        "titolo": titolo,
        "ente": "Commissione Europea",
        "fonte": "UE",
        "programma": _programma_da_identifier(identifier),
        "tipo_agevolazione": clean_html(first(md.get("typesOfAction"))) or "Grant UE",
        "settore": clean_html(first(md.get("callTitle"))),
        "beneficiari": classifica_beneficiari(md),
        "importo": None,  # budgetOverview è un JSON non strutturato: meglio non mostrarlo
        "data_apertura": apertura_iso,
        "data_scadenza": scadenza_iso,
        "scadenza_raw": str(scadenza_raw) if scadenza_raw else None,
        "link": link,
        "stato": stato,
        "note": f"Identificativo bando: {identifier}" if identifier else None,
    }


def scrape(max_pages: int = 6, page_size: int = 100) -> list[dict]:
    """Scarica i bandi UE aperti/in arrivo. Solleva eccezione se l'API non risponde."""
    risultati = []
    data = None
    for page in range(1, max_pages + 1):
        url = f"{SEARCH_URL}?apiKey={API_KEY}&text=***&pageSize={page_size}&pageNumber={page}"
        resp = safe_post(url, files=_build_files(page_size))
        data = resp.json()

        items = data.get("results") or []
        if not items:
            break
        for item in items:
            risultati.append(_normalizza(item))

        total = data.get("totalResults", 0)
        if page * page_size >= total:
            break

    # Salva l'ultima risposta grezza per eventuale debug/ricalibrazione.
    try:
        RAW_DEBUG_PATH.parent.mkdir(parents=True, exist_ok=True)
        RAW_DEBUG_PATH.write_text(json.dumps(data, indent=2)[:300000], encoding="utf-8")
    except Exception:
        pass

    if not risultati:
        raise RuntimeError(
            "L'API SEDIA non ha restituito bandi. Verifica la struttura della "
            "richiesta (query/languages come blob application/json) o eventuali "
            "modifiche all'endpoint di ricerca del portale F&T."
        )
    return risultati
