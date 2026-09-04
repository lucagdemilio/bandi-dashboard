"""
Layer di accesso al database SQLite per i bandi di finanza agevolata.
"""
import sqlite3
import hashlib
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).parent / "data" / "bandi.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS bandi (
    id TEXT PRIMARY KEY,           -- hash univoco (fonte+titolo+link)
    titolo TEXT NOT NULL,
    ente TEXT,                     -- soggetto concedente / programma
    fonte TEXT NOT NULL,           -- 'UE' | 'Nazionale' | 'Regionale Sicilia'
    programma TEXT,                -- es. Horizon Europe, PR FESR Sicilia, PNRR...
    tipo_agevolazione TEXT,        -- fondo perduto, credito d'imposta, finanziamento...
    settore TEXT,
    codici_ateco TEXT,             -- codici ATECO ammessi (o "Tutti i settori")
    beneficiari TEXT,               -- a chi è rivolto (PMI, enti, ricercatori...)
    importo TEXT,
    data_apertura TEXT,
    data_scadenza TEXT,            -- formato ISO YYYY-MM-DD quando possibile
    scadenza_raw TEXT,             -- testo originale, se non parsabile
    link TEXT,
    stato TEXT,                    -- 'aperto' | 'chiuso' | 'sconosciuto'
    data_scraping TEXT NOT NULL,   -- quando è stato raccolto/aggiornato
    note TEXT
);
CREATE INDEX IF NOT EXISTS idx_fonte ON bandi(fonte);
CREATE INDEX IF NOT EXISTS idx_scadenza ON bandi(data_scadenza);
CREATE INDEX IF NOT EXISTS idx_stato ON bandi(stato);

CREATE TABLE IF NOT EXISTS log_scraping (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fonte TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    esito TEXT NOT NULL,           -- 'ok' | 'errore'
    n_record INTEGER DEFAULT 0,
    dettaglio TEXT
);
"""


def make_id(fonte: str, titolo: str, link: str = "") -> str:
    raw = f"{fonte}|{titolo.strip().lower()}|{(link or '').strip().lower()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migrazione leggera per DB creati prima dell'aggiunta di codici_ateco.
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(bandi)").fetchall()}
        if "codici_ateco" not in cols:
            conn.execute("ALTER TABLE bandi ADD COLUMN codici_ateco TEXT")


def upsert_bandi(records: list[dict]):
    """Inserisce o aggiorna una lista di bandi (dict con le chiavi dello schema)."""
    if not records:
        return 0
    now = datetime.now().isoformat(timespec="seconds")
    with get_conn() as conn:
        for r in records:
            bid = make_id(r.get("fonte", ""), r.get("titolo", ""), r.get("link", ""))
            conn.execute(
                """
                INSERT INTO bandi (id, titolo, ente, fonte, programma, tipo_agevolazione,
                    settore, codici_ateco, beneficiari, importo, data_apertura, data_scadenza,
                    scadenza_raw, link, stato, data_scraping, note)
                VALUES (:id, :titolo, :ente, :fonte, :programma, :tipo_agevolazione,
                    :settore, :codici_ateco, :beneficiari, :importo, :data_apertura, :data_scadenza,
                    :scadenza_raw, :link, :stato, :data_scraping, :note)
                ON CONFLICT(id) DO UPDATE SET
                    titolo=excluded.titolo, ente=excluded.ente, programma=excluded.programma,
                    tipo_agevolazione=excluded.tipo_agevolazione, settore=excluded.settore,
                    codici_ateco=excluded.codici_ateco,
                    beneficiari=excluded.beneficiari, importo=excluded.importo,
                    data_apertura=excluded.data_apertura, data_scadenza=excluded.data_scadenza,
                    scadenza_raw=excluded.scadenza_raw, link=excluded.link,
                    stato=excluded.stato, data_scraping=excluded.data_scraping,
                    note=excluded.note
                """,
                {
                    "id": bid,
                    "titolo": r.get("titolo", "")[:500],
                    "ente": r.get("ente"),
                    "fonte": r.get("fonte"),
                    "programma": r.get("programma"),
                    "tipo_agevolazione": r.get("tipo_agevolazione"),
                    "settore": r.get("settore"),
                    "codici_ateco": r.get("codici_ateco"),
                    "beneficiari": r.get("beneficiari"),
                    "importo": r.get("importo"),
                    "data_apertura": r.get("data_apertura"),
                    "data_scadenza": r.get("data_scadenza"),
                    "scadenza_raw": r.get("scadenza_raw"),
                    "link": r.get("link"),
                    "stato": r.get("stato", "sconosciuto"),
                    "data_scraping": now,
                    "note": r.get("note"),
                },
            )
    return len(records)


def log_run(fonte: str, esito: str, n_record: int = 0, dettaglio: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO log_scraping (fonte, timestamp, esito, n_record, dettaglio) VALUES (?,?,?,?,?)",
            (fonte, datetime.now().isoformat(timespec="seconds"), esito, n_record, dettaglio[:2000]),
        )


def get_all_bandi():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM bandi ORDER BY data_scadenza IS NULL, data_scadenza ASC").fetchall()
        return [dict(r) for r in rows]


def get_last_log():
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM log_scraping ORDER BY id DESC LIMIT 20"
        ).fetchall()
        return [dict(r) for r in rows]
