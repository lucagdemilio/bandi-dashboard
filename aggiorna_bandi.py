#!/usr/bin/env python3
"""
Aggiornamento NON interattivo dei bandi, pensato per uno scheduler
(launchd su macOS, cron su Linux, Task Scheduler su Windows).

Esegue tutti gli scraper, salva su SQLite e scrive un log leggibile in
data/refresh.log. Può essere lanciato anche a mano:

    venv/bin/python aggiorna_bandi.py
"""
import sys
from pathlib import Path
from datetime import datetime

# Assicura che la cartella del progetto sia importabile anche se lo scheduler
# lo lancia da un'altra working directory.
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from database import init_db          # noqa: E402
from scrapers import esegui_tutti     # noqa: E402

LOG_PATH = PROJECT_DIR / "data" / "refresh.log"


def main() -> int:
    init_db()
    inizio = datetime.now()
    esito = esegui_tutti()

    righe = [f"[{inizio.isoformat(timespec='seconds')}] Aggiornamento bandi"]
    totale = 0
    errori = 0
    for fonte, e in esito.items():
        if e["ok"]:
            totale += e["n"]
            righe.append(f"  ✓ {fonte}: {e['n']} bandi")
        else:
            errori += 1
            righe.append(f"  ✗ {fonte}: ERRORE — {str(e['errore'])[:150]}")
    durata = (datetime.now() - inizio).total_seconds()
    righe.append(f"  → totale {totale} record, {errori} fonti in errore, {durata:.1f}s")
    testo = "\n".join(righe) + "\n"

    print(testo, end="")
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(testo)
    except Exception as exc:  # il log su file non deve far fallire l'update
        print(f"(impossibile scrivere {LOG_PATH}: {exc})")

    return 1 if errori else 0


if __name__ == "__main__":
    raise SystemExit(main())
