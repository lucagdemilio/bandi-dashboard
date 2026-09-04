from __future__ import annotations
from . import (
    eu_scraper,
    nazionale_scraper,
    sicilia_scraper,
    invitalia_scraper,
    irfis_scraper,
)
from database import upsert_bandi, log_run

# Ordine = ordine di visualizzazione nella sidebar.
FONTI = {
    "UE": eu_scraper,
    "Nazionale": nazionale_scraper,
    "Invitalia": invitalia_scraper,
    "Regione Sicilia": sicilia_scraper,
    "IRFIS": irfis_scraper,
}


def esegui_uno(nome: str) -> dict:
    """Esegue un singolo scraper e salva i risultati. Ritorna l'esito."""
    modulo = FONTI[nome]
    try:
        records = modulo.scrape()
        n = upsert_bandi(records)
        log_run(nome, "ok", n)
        return {"ok": True, "n": n, "errore": None}
    except Exception as e:
        log_run(nome, "errore", 0, str(e))
        return {"ok": False, "n": 0, "errore": str(e)}


def esegui_tutti(fonti_selezionate=None) -> dict:
    """Esegue gli scraper richiesti (default: tutti) e salva i risultati su DB.
    Ritorna un riepilogo {fonte: {"ok": bool, "n": int, "errore": str|None}}."""
    fonti_selezionate = fonti_selezionate or list(FONTI.keys())
    return {nome: esegui_uno(nome) for nome in fonti_selezionate}
