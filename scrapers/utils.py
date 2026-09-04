from __future__ import annotations
"""
Utility condivise dagli scraper: sessione HTTP, parsing date italiane/ISO,
pulizia testo e calcolo dello stato del bando.
"""
import re
import requests
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
}

# Sessione riusata da tutti gli scraper (connessioni keep-alive + header comuni)
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

MESI_IT = {
    "gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
    "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
}


def safe_get(url, **kwargs):
    kwargs.setdefault("timeout", 30)
    resp = SESSION.get(url, **kwargs)
    resp.raise_for_status()
    return resp


def safe_post(url, **kwargs):
    kwargs.setdefault("timeout", 30)
    resp = SESSION.post(url, **kwargs)
    resp.raise_for_status()
    return resp


def parse_data_ita(text) -> str | None:
    """Estrae una data ISO (YYYY-MM-DD) da un testo italiano/ISO libero."""
    if not text:
        return None
    text = str(text).strip()

    # ISO con eventuale orario: 2027-04-06 oppure 2027-04-06T00:00:00.000+0000
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", text)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date().isoformat()
        except ValueError:
            pass

    # dd/mm/yyyy o dd-mm-yyyy
    m = re.search(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", text)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d).date().isoformat()
        except ValueError:
            pass

    # "12 marzo 2026"
    m = re.search(r"(\d{1,2})\s+([a-zA-Zàèìòù]+)\s+(\d{4})", text.lower())
    if m:
        giorno, mese_str, anno = int(m.group(1)), m.group(2), int(m.group(3))
        mese = MESI_IT.get(mese_str)
        if mese:
            try:
                return datetime(anno, mese, giorno).date().isoformat()
            except ValueError:
                pass

    return None


def stato_da_scadenza(data_iso) -> str:
    """'aperto' se la scadenza è futura, 'chiuso' se passata, altrimenti 'sconosciuto'."""
    if not data_iso:
        return "sconosciuto"
    try:
        d = datetime.fromisoformat(str(data_iso)).date()
    except ValueError:
        return "sconosciuto"
    return "aperto" if d >= datetime.now().date() else "chiuso"


def clean_html(text) -> str | None:
    """Rimuove i tag HTML da un testo e normalizza gli spazi."""
    if not text:
        return None
    txt = re.sub(r"<[^>]+>", " ", str(text))
    txt = re.sub(r"&nbsp;", " ", txt)
    txt = re.sub(r"\s+", " ", txt).strip()
    return txt or None


def first(value, default=None):
    """Restituisce il primo elemento se è una lista, altrimenti il valore stesso."""
    if isinstance(value, list):
        return value[0] if value else default
    return value if value not in (None, "") else default


# --------------------------- Matching ATECO ---------------------------
def _norm_ateco(code) -> str:
    """Normalizza un codice ATECO alle sole cifre (es. '62.01.00' -> '620100')."""
    return re.sub(r"\D", "", str(code or ""))


# Forma valida di un codice ATECO: 2 cifre (divisione) + eventuali gruppi ".dd".
# Esclude etichette e anni come "ATECO" o "2025" presenti nelle stringhe grezze.
_ATECO_TOKEN = re.compile(r"^\d{2}(?:\.\d{1,2}){0,3}$")


def parse_ateco_codes(testo) -> list[str]:
    """Estrae i soli codici ATECO validi da una stringa
    ('ATECO 2025: 90.00; 90.01' -> ['90.00', '90.01'])."""
    if not testo:
        return []
    out = []
    for c in re.split(r"[;,/|\s]+", str(testo)):
        c = c.strip().rstrip(".:")
        if _ATECO_TOKEN.match(c):
            out.append(c)
    return out


def ateco_status(codici_bando, query_codes) -> str:
    """Confronta i codici ATECO del bando con quelli dell'azienda.
    Ritorna: 'tutti' (bando aperto a tutti i settori), 'match' (compatibile),
    'no' (non compatibile), 'n/d' (bando senza dati ATECO)."""
    if not codici_bando:
        return "n/d"
    low = str(codici_bando).lower()
    if "tutti i settori" in low or "tutti i codici" in low:
        return "tutti"
    bando = [_norm_ateco(c) for c in parse_ateco_codes(codici_bando)]
    bando = [c for c in bando if len(c) >= 2]
    query = [_norm_ateco(c) for c in query_codes]
    query = [c for c in query if len(c) >= 2]
    for a in query:
        for b in bando:
            if a.startswith(b) or b.startswith(a):
                return "match"
    return "no"
