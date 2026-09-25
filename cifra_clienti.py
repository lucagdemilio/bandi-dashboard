#!/usr/bin/env python3
"""
Cifra data/clienti.db in data/clienti.db.enc (Fernet / AES-128).

- Il file cifrato (.enc) può stare anche in un repo pubblico: è illeggibile
  senza la chiave.
- La chiave viene salvata in .streamlit/secrets.toml (in .gitignore) e va
  incollata anche nei Secrets dell'app su Streamlit Cloud.

Uso:
    venv/bin/python cifra_clienti.py
"""
from __future__ import annotations
from pathlib import Path
import re
from cryptography.fernet import Fernet

PROJECT = Path(__file__).resolve().parent
PLAIN = PROJECT / "data" / "clienti.db"
ENC = PROJECT / "data" / "clienti.db.enc"
SECRETS = PROJECT / ".streamlit" / "secrets.toml"


def leggi_chiave_esistente() -> str | None:
    if SECRETS.exists():
        m = re.search(r'CLIENTI_KEY\s*=\s*"([^"]+)"', SECRETS.read_text(encoding="utf-8"))
        if m:
            return m.group(1)
    return None


def salva_chiave(key: str):
    SECRETS.parent.mkdir(parents=True, exist_ok=True)
    testo = SECRETS.read_text(encoding="utf-8") if SECRETS.exists() else ""
    if "CLIENTI_KEY" in testo:
        testo = re.sub(r'CLIENTI_KEY\s*=\s*"[^"]*"', f'CLIENTI_KEY = "{key}"', testo)
    else:
        testo = (testo.rstrip() + "\n" if testo.strip() else "") + f'CLIENTI_KEY = "{key}"\n'
    SECRETS.write_text(testo, encoding="utf-8")


def main() -> int:
    if not PLAIN.exists():
        print(f"Manca {PLAIN}. Esegui prima importa_clienti.py")
        return 1
    key = leggi_chiave_esistente() or Fernet.generate_key().decode()
    salva_chiave(key)
    token = Fernet(key.encode()).encrypt(PLAIN.read_bytes())
    ENC.write_bytes(token)
    print(f"Cifrato: {ENC}  ({ENC.stat().st_size} byte)")
    print(f"Chiave salvata in {SECRETS}")
    print("\n--- CHIAVE (da incollare nei Secrets di Streamlit Cloud) ---")
    print(f'CLIENTI_KEY = "{key}"')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
