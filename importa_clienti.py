#!/usr/bin/env python3
"""
Importa l'anagrafica clienti/prospect da un file Excel in un database SQLite
separato (data/clienti.db), ripulendo i dati:
  - Partita IVA -> stringa a 11 cifre (ripristina gli zeri iniziali persi da Excel)
  - Codice ATECO 2007 -> stringa a 6 cifre + versione formattata "DD.DD.DD"

Uso:
    venv/bin/python importa_clienti.py ["Lista codici ateco e p.iva.xlsx"]

I dati clienti sono SENSIBILI: clienti.db è in .gitignore e non va su repo pubblici.
"""
from __future__ import annotations
import sys
import sqlite3
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent
CLIENTI_DB = PROJECT_DIR / "data" / "clienti.db"
DEFAULT_XLSX = PROJECT_DIR / "Lista codici ateco e p.iva.xlsx"

SCHEMA = """
CREATE TABLE IF NOT EXISTS clienti (
    piva TEXT PRIMARY KEY,
    ragione_sociale TEXT,
    provincia TEXT,
    ateco TEXT,            -- 6 cifre normalizzate (es. 412000)
    ateco_fmt TEXT,        -- formattato per la vista (es. 41.20.00)
    ricavi REAL,
    dipendenti INTEGER,
    chiusura_bilancio TEXT
);
CREATE INDEX IF NOT EXISTS idx_cli_ateco ON clienti(ateco);
CREATE INDEX IF NOT EXISTS idx_cli_prov ON clienti(provincia);
"""


def pad_piva(v) -> str | None:
    if pd.isna(v):
        return None
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = "".join(ch for ch in s if ch.isdigit())
    if not s:
        return None
    return s.zfill(11)


def norm_ateco(v):
    if pd.isna(v):
        return None, None
    s = str(v).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = "".join(ch for ch in s if ch.isdigit())
    if not s:
        return None, None
    s = s.zfill(6)
    fmt = f"{s[0:2]}.{s[2:4]}.{s[4:6]}"
    return s, fmt


def to_int(v):
    try:
        if pd.isna(v):
            return None
        return int(float(v))
    except (ValueError, TypeError):
        return None


def to_float(v):
    try:
        if pd.isna(v):
            return None
        return float(v)
    except (ValueError, TypeError):
        return None


def carica(xlsx_path: Path) -> list[dict]:
    df = pd.read_excel(xlsx_path)
    df.columns = ["idx", "ragione_sociale", "provincia", "chiusura_bilancio",
                  "ricavi", "dipendenti", "ateco", "piva"]
    records = []
    for _, r in df.iterrows():
        piva = pad_piva(r["piva"])
        if not piva:
            continue
        ateco, ateco_fmt = norm_ateco(r["ateco"])
        chius = r["chiusura_bilancio"]
        chius = str(chius)[:10] if not pd.isna(chius) else None
        records.append({
            "piva": piva,
            "ragione_sociale": str(r["ragione_sociale"]).strip() if not pd.isna(r["ragione_sociale"]) else None,
            "provincia": str(r["provincia"]).strip() if not pd.isna(r["provincia"]) else None,
            "ateco": ateco,
            "ateco_fmt": ateco_fmt,
            "ricavi": to_float(r["ricavi"]),
            "dipendenti": to_int(r["dipendenti"]),
            "chiusura_bilancio": chius,
        })
    return records


def salva(records: list[dict]):
    CLIENTI_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CLIENTI_DB)
    conn.executescript(SCHEMA)
    conn.execute("DELETE FROM clienti")  # ricarica pulita
    conn.executemany(
        """INSERT OR REPLACE INTO clienti
           (piva, ragione_sociale, provincia, ateco, ateco_fmt, ricavi, dipendenti, chiusura_bilancio)
           VALUES (:piva, :ragione_sociale, :provincia, :ateco, :ateco_fmt, :ricavi, :dipendenti, :chiusura_bilancio)""",
        records,
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM clienti").fetchone()[0]
    conn.close()
    return n


def main():
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    if not xlsx.exists():
        print(f"File non trovato: {xlsx}")
        return 1
    records = carica(xlsx)
    n = salva(records)
    print(f"Importati {n} clienti (da {len(records)} righe valide) in {CLIENTI_DB}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
