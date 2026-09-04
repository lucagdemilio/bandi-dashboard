from __future__ import annotations
"""
Scraper per il catalogo incentivi di incentivi.gov.it (MIMIT).

Il portale espone il proprio indice di ricerca (Apache Solr) tramite lo stesso
endpoint usato dai pulsanti "Scarica JSON / CSV" della sezione Open Data
(licenza IODL 2.0). È la fonte italiana più ricca e stabile: un'unica GET
restituisce tutti gli incentivi con campi già strutturati, comprese le
agevolazioni regionali (campo Regioni).

Endpoint (host www obbligatorio per via del certificato SNI):
  https://www.incentivi.gov.it/solr/coredrupal/select
"""
from .utils import safe_get, parse_data_ita, stato_da_scadenza, first

SOLR_URL = "https://www.incentivi.gov.it/solr/coredrupal/select"

# Alias leggibile -> campo Solr interno. Ricavato dalla richiesta reale del
# pulsante "Scarica JSON" della pagina Open Data.
FIELD_MAP = {
    "ID_Incentivo": "zs_nid",
    "Titolo": "zs_title",
    "Obiettivo": "zm_field_scopes_value",
    "Data_apertura": "zs_field_open_date",
    "Data_chiusura": "zs_field_close_date",
    "Note_apertura_chiusura": "zs_field_close_date_descriptor",
    "Tipologia_Soggetto": "zm_field_subject_type_value",
    "Forma_agevolazione": "zm_field_support_form_value",
    "Settore_Attivita": "zm_field_activity_sector_value",
    "Codici_ATECO": "zs_field_ateco",
    "Regioni": "zm_field_regions_value",
    "Soggetto_Concedente": "zs_field_subject_grant",
    "Stanziamento": "zs_field_budget_allocation",
    "Link_istituzionale": "zs_field_link",
    "Data_ultimo_aggiornamento": "ds_last_update",
}

# Il catalogo incentivi.gov.it aggrega misure nazionali E regionali di TUTTE
# le regioni. Per una dashboard focalizzata su UE/Italia/Sicilia teniamo solo:
#   - incentivi nazionali (coprono ~tutte le regioni, soglia REGIONI_NAZIONALE)
#   - incentivi che includono la Sicilia
# Gli incentivi mono/pluri-regionali di sole ALTRE regioni vengono scartati.
REGIONI_NAZIONALE = 15  # n. regioni oltre il quale l'incentivo è di fatto nazionale


def _fl_param() -> str:
    return ",".join(f"{alias}:{campo}" for alias, campo in FIELD_MAP.items())


def _regioni_list(rec: dict) -> list:
    reg = rec.get("Regioni")
    if isinstance(reg, list):
        return [str(x) for x in reg]
    return [str(reg)] if reg else []


def _classifica(rec: dict):
    """Ritorna (rilevante: bool, fonte: str, regioni_str: str)."""
    regioni = _regioni_list(rec)
    regioni_str = ", ".join(regioni)
    n = len(regioni)
    has_sicilia = any("sicil" in r.lower() for r in regioni)

    if n == 0 or n >= REGIONI_NAZIONALE:
        return True, "Nazionale", regioni_str
    if has_sicilia:
        return True, "Regionale Sicilia", regioni_str
    return False, "Nazionale (altra regione)", regioni_str


def _normalizza(rec: dict) -> dict:
    _, fonte, regioni_str = _classifica(rec)
    scadenza_iso = parse_data_ita(rec.get("Data_chiusura"))
    apertura_iso = parse_data_ita(rec.get("Data_apertura"))

    stanziamento = first(rec.get("Stanziamento"))
    importo = f"€ {stanziamento}" if stanziamento else None

    nid = first(rec.get("ID_Incentivo"))
    link = first(rec.get("Link_istituzionale"))
    if not link and nid:
        link = f"https://www.incentivi.gov.it/it/node/{nid}"

    return {
        "titolo": str(first(rec.get("Titolo")) or "Titolo non disponibile"),
        "ente": first(rec.get("Soggetto_Concedente")),
        "fonte": fonte,
        "programma": first(rec.get("Obiettivo")),
        "tipo_agevolazione": ", ".join(rec["Forma_agevolazione"]) if isinstance(rec.get("Forma_agevolazione"), list) else first(rec.get("Forma_agevolazione")),
        "settore": ", ".join(rec["Settore_Attivita"]) if isinstance(rec.get("Settore_Attivita"), list) else first(rec.get("Settore_Attivita")),
        "codici_ateco": first(rec.get("Codici_ATECO")),
        "beneficiari": ", ".join(rec["Tipologia_Soggetto"]) if isinstance(rec.get("Tipologia_Soggetto"), list) else first(rec.get("Tipologia_Soggetto")),
        "importo": importo,
        "data_apertura": apertura_iso,
        "data_scadenza": scadenza_iso,
        "scadenza_raw": str(first(rec.get("Data_chiusura"))) if rec.get("Data_chiusura") else None,
        "link": link,
        "stato": stato_da_scadenza(scadenza_iso),
        "note": (f"Regioni: {regioni_str}" if regioni_str else "Incentivo nazionale"),
    }


def scrape(solo_aperti: bool = True, solo_rilevanti: bool = True, righe: int = 8000) -> list[dict]:
    """Scarica il catalogo incentivi.gov.it.
    - solo_rilevanti: tiene solo incentivi nazionali o che includono la Sicilia
      (scarta le misure di sole altre regioni).
    - solo_aperti: tiene i bandi con scadenza futura o senza scadenza (a sportello)."""
    params = {
        "q.op": "OR",
        "wt": "json",
        "rows": righe,
        "fl": _fl_param(),
        "q": "index_id:incentivi",
    }
    resp = safe_get(SOLR_URL, params=params)
    docs = resp.json().get("response", {}).get("docs", [])
    if not docs:
        raise RuntimeError(
            "L'endpoint Solr di incentivi.gov.it non ha restituito documenti. "
            "Verifica l'URL o i nomi dei campi (fl) nella pagina Open Data."
        )

    record = []
    for d in docs:
        rilevante, _, _ = _classifica(d)
        if solo_rilevanti and not rilevante:
            continue
        record.append(_normalizza(d))

    if solo_aperti:
        record = [r for r in record if r["stato"] in ("aperto", "sconosciuto")]
    return record
