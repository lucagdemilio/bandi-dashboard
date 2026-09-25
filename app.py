import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from database import (init_db, get_all_bandi, get_last_log,
                      get_clienti, clienti_disponibili)
from scrapers import esegui_tutti, FONTI
from scrapers.utils import ateco_status, parse_ateco_codes
import ui

st.set_page_config(page_title="Studio Lombardo-Culotta · Bandi", layout="wide",
                   page_icon="📋", initial_sidebar_state="collapsed")
init_db()
ui.inject_css(st)

# Auto-refresh della vista ogni 5 minuti: ricarica i dati più recenti dal
# database senza intervento manuale (NON riesegue lo scraping, solo la lettura).
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=5 * 60 * 1000, key="auto_refresh_5min")
except Exception:
    pass

SETTORI_MACRO = [
    "Agricoltura, silvicoltura e pesca", "Agroalimentare", "Alberghiero", "Altri servizi",
    "Artigianato", "Autoveicoli e altri mezzi di trasporto", "Chimica e Farmaceutica",
    "Commercio", "Cultura", "Edilizia", "Elettronica", "Fornitura Energia, Acqua e gestione Rifiuti",
    "ICT", "Meccanica", "Metallurgia", "Mobili, Legno e Carta", "Moda e Tessile",
    "Ristorazione", "Salute", "Servizi di trasporto", "Turismo",
]

FONTI_TERRITORIALI = ["Regionale Sicilia", "IRFIS"]


def clienti_db_path():
    """Percorso a un DB clienti leggibile:
    - in locale usa data/clienti.db se presente;
    - altrimenti decifra data/clienti.db.enc con la chiave CLIENTI_KEY dai Secrets.
    Ritorna None se non disponibile."""
    plain = Path("data/clienti.db")
    if plain.exists():
        return plain
    enc = Path("data/clienti.db.enc")
    if not enc.exists():
        return None
    try:
        key = st.secrets["CLIENTI_KEY"]
    except Exception:
        return None
    if not key:
        return None
    try:
        from cryptography.fernet import Fernet
        dec = Path(tempfile.gettempdir()) / "slc_clienti_dec.db"
        if (not dec.exists()) or dec.stat().st_mtime < enc.stat().st_mtime:
            dec.write_bytes(Fernet(key.encode()).decrypt(enc.read_bytes()))
        return dec
    except Exception:
        return None


def aggiorna_dati():
    with st.spinner("Aggiornamento bandi in corso… può richiedere 30-60 secondi"):
        riepilogo = esegui_tutti()
    ok = sum(1 for e in riepilogo.values() if e["ok"])
    ko = [f"{f}: {e['errore'][:80]}" for f, e in riepilogo.items() if not e["ok"]]
    st.session_state["_upd_msg"] = (ok, ko)


# --- Pull-to-refresh (swipe-down): il gesto imposta ?do_refresh=1 e ricarica ---
if st.query_params.get("do_refresh") == "1":
    st.query_params.clear()
    aggiorna_dati()
    st.rerun()

bandi = get_all_bandi()
ultimo = max((b["data_scraping"] for b in bandi), default="")[:16].replace("T", " ") if bandi else "—"

# ======================= HEADER con pulsante refresh =======================
h1, h2 = st.columns([5, 1], vertical_alignment="center")
with h1:
    st.markdown(ui.brand_title(), unsafe_allow_html=True)
with h2:
    if st.button("Aggiorna", icon=":material/refresh:", type="primary", use_container_width=True,
                 help="Riesegue lo scraping di tutte le fonti."):
        aggiorna_dati()
        st.rerun()
    st.markdown(f'<div class="upd-note">Agg.: {ultimo}</div>', unsafe_allow_html=True)
st.markdown(ui.obs_line(), unsafe_allow_html=True)
st.markdown(ui.head_divider(), unsafe_allow_html=True)

if "_upd_msg" in st.session_state:
    ok, ko = st.session_state.pop("_upd_msg")
    if not ko:
        st.success(f"Aggiornamento completato: {ok} fonti aggiornate.")
    else:
        st.warning("Aggiornamento con avvisi: " + " · ".join(ko))


def pull_to_refresh_component():
    """Gestisce lo swipe-down (pull-to-refresh) sui dispositivi touch."""
    components.html("""
<script>
(function(){
  const doc = window.parent.document;
  if (doc.__ptrInstalled) return;
  doc.__ptrInstalled = true;
  const TH = 85;
  let startY = 0, pulling = false, dist = 0;
  const ind = doc.createElement('div');
  ind.style.cssText = 'position:fixed;top:0;left:50%;transform:translateX(-50%) translateY(-100%);'
    + 'z-index:999999;background:#14385f;color:#fff;padding:7px 16px;border-radius:0 0 12px 12px;'
    + 'font:600 12px -apple-system,sans-serif;transition:transform .12s;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,.2)';
  ind.textContent = '↓ Trascina per aggiornare';
  doc.body.appendChild(ind);
  function scroller(){ return doc.querySelector('[data-testid="stMain"]') || doc.scrollingElement || doc.documentElement; }
  doc.addEventListener('touchstart', e => {
    if (scroller().scrollTop <= 2) { startY = e.touches[0].clientY; pulling = true; dist = 0; }
  }, {passive:true});
  doc.addEventListener('touchmove', e => {
    if (!pulling) return;
    dist = e.touches[0].clientY - startY;
    if (dist > 0) {
      const y = Math.max(Math.min(dist, TH + 30) - 100, -100);
      ind.style.transform = 'translateX(-50%) translateY(' + y + '%)';
      ind.textContent = dist > TH ? '↑ Rilascia per aggiornare' : '↓ Trascina per aggiornare';
    }
  }, {passive:true});
  doc.addEventListener('touchend', () => {
    if (pulling && dist > TH) {
      ind.textContent = '⏳ Aggiornamento…';
      ind.style.transform = 'translateX(-50%) translateY(0)';
      const u = new URL(window.parent.location.href);
      u.searchParams.set('do_refresh', '1');
      window.parent.location.href = u.toString();
    } else {
      ind.style.transform = 'translateX(-50%) translateY(-100%)';
    }
    pulling = false;
  }, {passive:true});
})();
</script>
""", height=0)


pull_to_refresh_component()

if not bandi:
    st.info("Il database è vuoto. Premi **Aggiorna** in alto a destra per recuperare i bandi.")
    st.stop()

df = pd.DataFrame(bandi)
df["data_scadenza_dt"] = pd.to_datetime(df["data_scadenza"], errors="coerce")
oggi = pd.Timestamp(datetime.now().date())
df["giorni_scadenza"] = (df["data_scadenza_dt"] - oggi).dt.days
df.loc[df["giorni_scadenza"] < 0, "giorni_scadenza"] = pd.NA


# ======================= Componenti condivisi =======================
@st.dialog("Dettaglio bando", width="large")
def _dettaglio(row, aq=None):
    st.markdown(ui.detail_html(row, aq), unsafe_allow_html=True)
    link = row.get("link")
    if link and str(link).startswith("http"):
        st.link_button("Apri la scheda ufficiale", link, icon=":material/open_in_new:",
                       type="primary", use_container_width=True)


def render_cards(rows_df, aq, ns):
    """Rende una lista di bandi come griglia a 2 colonne di card cliccabili.
    ns = namespace per rendere univoche le key dei pulsanti."""
    grid = st.columns(2)
    for i, (_, row) in enumerate(rows_df.iterrows()):
        with grid[i % 2]:
            with st.container(border=True):
                st.markdown(ui.card_body_html(row, aq), unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Dettagli", key=f"det_{ns}_{row['id']}", icon=":material/read_more:",
                                 use_container_width=True):
                        _dettaglio(row, aq)
                with b2:
                    link = row.get("link")
                    if link and str(link).startswith("http"):
                        st.link_button("Apri", link, icon=":material/open_in_new:",
                                       type="primary", use_container_width=True)
                    else:
                        st.button("Link n/d", key=f"nd_{ns}_{row['id']}", disabled=True, use_container_width=True)


@st.cache_data(show_spinner=False)
def compat_index(distinct_ateco: tuple, ateco_items: tuple):
    """Distingue i bandi SPECIFICI per un ATECO dai bandi 'tutti i settori'.
    Ritorna (match_map, tutti_ids):
      - match_map[ateco] = id-bando che citano specificamente quel codice
      - tutti_ids = id-bando aperti a tutti i settori (validi per ogni azienda)
    ateco_items = tuple di (id_bando, codici_ateco)."""
    tutti_ids = [bid for (bid, cod) in ateco_items
                 if "tutti i settori" in str(cod).lower() or "tutti i codici" in str(cod).lower()]
    match_map = {}
    for a in distinct_ateco:
        match_map[a] = [bid for (bid, cod) in ateco_items if ateco_status(cod, [a]) == "match"]
    return match_map, tutti_ids


tab_bandi, tab_clienti = st.tabs(["Bandi", "Portafoglio clienti"])

# ============================================================================
# ============================ SCHEDA: BANDI =================================
# ============================================================================
with tab_bandi:
    def _reset_filtri():
        for k in ["f_kw", "f_fonte", "f_benef", "f_stato", "f_settore",
                  "f_ateco", "f_ateco_comp", "f_imprese", "f_scad", "f_ordina"]:
            st.session_state.pop(k, None)

    with st.expander("Filtri e ricerca", expanded=False, icon=":material/filter_alt:"):
        keyword = st.text_input("Ricerca libera", key="f_kw",
                                placeholder="Cerca per titolo, ente o settore…")

        st.markdown(ui.section("Fonte e destinatari"), unsafe_allow_html=True)
        a1, a2, a3 = st.columns(3)
        with a1:
            fonte_filtro = st.multiselect("Fonte", sorted(df["fonte"].dropna().unique()), key="f_fonte")
        with a2:
            benef_opzioni = sorted(df["beneficiari"].dropna().unique()) if "beneficiari" in df.columns else []
            benef_filtro = st.multiselect("Beneficiari", benef_opzioni, key="f_benef")
        with a3:
            stato_filtro = st.multiselect("Stato", sorted(df["stato"].dropna().unique()), key="f_stato")

        st.markdown(ui.section("Settore di attività"), unsafe_allow_html=True)
        b1, b2 = st.columns([3, 2])
        with b1:
            settore_filtro = st.multiselect("Macro-settore", SETTORI_MACRO, key="f_settore")
        with b2:
            ateco_input = st.text_input("Codice ATECO azienda", key="f_ateco", placeholder="es. 62.01, 56.10")
        solo_ateco_comp = st.checkbox("Mostra solo bandi con settore ATECO compatibile", key="f_ateco_comp",
                                      help="Nasconde i bandi privi di classificazione ATECO (UE/regionali).")

        st.markdown(ui.section("Opzioni e ordinamento"), unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            solo_imprese = st.checkbox("Solo pertinenti a imprese", value=True, key="f_imprese",
                                       help="Esclude i bandi UE di pura ricerca accademica.")
            solo_scad_futura = st.checkbox("Solo con scadenza futura", key="f_scad")
        with c2:
            ordina_per = st.selectbox("Ordina per",
                                      ["Scadenza (più imminente)", "Scadenza (più lontana)", "Titolo (A-Z)"],
                                      key="f_ordina")
        _sp, c_reset = st.columns([4, 1])
        with c_reset:
            st.button("Reimposta", icon=":material/restart_alt:", on_click=_reset_filtri,
                      type="secondary", use_container_width=True)

    ateco_query = parse_ateco_codes(ateco_input) if ateco_input else []

    _chips = []
    if fonte_filtro:
        _chips.append(("Fonte:", ", ".join(fonte_filtro)))
    if benef_filtro:
        _chips.append(("Beneficiari:", ", ".join(benef_filtro)))
    if stato_filtro:
        _chips.append(("Stato:", ", ".join(stato_filtro)))
    if settore_filtro:
        _chips.append(("Settore:", ", ".join(settore_filtro)))
    if ateco_query:
        _chips.append(("ATECO:", ", ".join(ateco_query)))
    if keyword:
        _chips.append(("Ricerca:", keyword))
    if solo_scad_futura:
        _chips.append(("", "Solo scadenza futura"))
    if solo_ateco_comp:
        _chips.append(("", "Solo ATECO compatibile"))
    if not solo_imprese:
        _chips.append(("", "Incluse ricerca/università", "warn"))
    if _chips:
        st.markdown(ui.chips_html(_chips), unsafe_allow_html=True)

    d = df.copy()
    if fonte_filtro:
        d = d[d["fonte"].isin(fonte_filtro)]
    if benef_filtro:
        d = d[d["beneficiari"].isin(benef_filtro)]
    if stato_filtro:
        d = d[d["stato"].isin(stato_filtro)]
    if solo_imprese and "beneficiari" in d.columns:
        d = d[d["beneficiari"] != "Ricerca/Università"]
    if settore_filtro:
        patt = "|".join(pd.Series(settore_filtro).str.lower().tolist())
        d = d[d["settore"].fillna("").str.lower().str.contains(patt, regex=True)]
    if keyword:
        kw = keyword.lower()
        d = d[
            d["titolo"].str.lower().str.contains(kw, na=False)
            | d["ente"].str.lower().str.contains(kw, na=False)
            | d["settore"].str.lower().str.contains(kw, na=False)
        ]
    if solo_scad_futura:
        d = d[d["data_scadenza_dt"] >= oggi]
    if ateco_query:
        stati = d["codici_ateco"].apply(lambda c: ateco_status(c, ateco_query))
        d = d[stati.isin(["match", "tutti"])] if solo_ateco_comp else d[stati != "no"]

    if ordina_per == "Scadenza (più imminente)":
        d = d.sort_values("giorni_scadenza", na_position="last")
    elif ordina_per == "Scadenza (più lontana)":
        d = d.sort_values("giorni_scadenza", ascending=False, na_position="last")
    else:
        d = d.sort_values("titolo")

    aperti = int((d["stato"] == "aperto").sum())
    in_scad_30 = int(((d["data_scadenza_dt"] >= oggi) & (d["data_scadenza_dt"] <= oggi + timedelta(days=30))).sum())

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(ui.kpi_card("Bandi (filtro attivo)", len(d), f"su {len(df)} totali"), unsafe_allow_html=True)
    k2.markdown(ui.kpi_card("Aperti", aperti, "scadenza futura / a sportello"), unsafe_allow_html=True)
    k3.markdown(ui.kpi_card("In scadenza", in_scad_30, "entro 30 giorni", variant="warn"), unsafe_allow_html=True)
    k4.markdown(ui.kpi_card("Ultimo aggiornamento", ultimo[:10], "dati locali"), unsafe_allow_html=True)
    st.write("")

    tot = len(d)
    r1, r2, r3 = st.columns([3, 1, 1])
    with r1:
        et = f"#### {tot} bandi trovati"
        if ateco_query:
            et += f"  ·  ATECO {', '.join(ateco_query)}"
        st.markdown(et)
    with r2:
        per_pagina = st.selectbox("Per pagina", [12, 20, 30, 50], index=1, label_visibility="collapsed")
    with r3:
        n_pagine = max(1, (tot + per_pagina - 1) // per_pagina)
        pagina = st.selectbox("Pagina", options=list(range(1, n_pagine + 1)),
                              format_func=lambda p: f"Pagina {p}/{n_pagine}", label_visibility="collapsed")

    if tot == 0:
        st.warning("Nessun bando corrisponde ai filtri selezionati. Prova ad allentare i criteri.")
    else:
        start = (pagina - 1) * per_pagina
        render_cards(d.iloc[start:start + per_pagina], ateco_query, "b")

    st.divider()
    colonne_csv = ["titolo", "fonte", "beneficiari", "ente", "programma", "tipo_agevolazione",
                   "settore", "codici_ateco", "importo", "data_scadenza", "giorni_scadenza", "stato", "link"]
    colonne_csv = [c for c in colonne_csv if c in d.columns]
    e1, e2, e3 = st.columns([1, 1, 2])
    with e1:
        st.download_button("Esporta CSV", d[colonne_csv].to_csv(index=False).encode("utf-8"),
                           "bandi_export.csv", "text/csv", icon=":material/download:", use_container_width=True)
    with e2:
        mostra_tabella = st.toggle("Vista tabella")
    with e3:
        with st.expander("Log aggiornamenti", icon=":material/history:"):
            for l in get_last_log()[:8]:
                icona = "✅" if l["esito"] == "ok" else "❌"
                st.caption(f"{icona} {l['timestamp'][:16].replace('T', ' ')} · {l['fonte']} ({l['n_record']})")

    if mostra_tabella:
        st.dataframe(
            d[colonne_csv], use_container_width=True, hide_index=True,
            column_config={
                "link": st.column_config.LinkColumn("Link", display_text="Apri ↗"),
                "giorni_scadenza": st.column_config.NumberColumn("Giorni", format="%d gg"),
                "data_scadenza": "Scadenza", "codici_ateco": "Codici ATECO",
            },
        )

# ============================================================================
# ====================== SCHEDA: PORTAFOGLIO CLIENTI =========================
# ============================================================================
with tab_clienti:
    _cli_path = clienti_db_path()
    if _cli_path is None:
        st.info(
            "Anagrafica clienti non disponibile. In locale: esegui "
            "`venv/bin/python importa_clienti.py`. Online: verifica che la chiave "
            "**CLIENTI_KEY** sia impostata nei Secrets dell'app."
        )
    else:
        clienti = get_clienti(_cli_path)
        cdf = pd.DataFrame(clienti)

        # Bandi aperti e indice di compatibilità ATECO
        aperti_df = df[df["stato"] == "aperto"].copy()
        con_ateco = aperti_df[aperti_df["codici_ateco"].notna()
                              & (aperti_df["codici_ateco"].astype(str).str.strip() != "")]
        ateco_items = tuple((r["id"], r["codici_ateco"]) for _, r in con_ateco.iterrows())
        distinct_ateco = tuple(sorted(cdf["ateco"].dropna().unique()))
        match_map, tutti_ids = compat_index(distinct_ateco, ateco_items)
        tutti_ids = set(tutti_ids)

        territ_ids = set(aperti_df.loc[aperti_df["fonte"].isin(FONTI_TERRITORIALI), "id"])

        cdf["n_settore"] = cdf["ateco"].map(lambda a: len(match_map.get(a, [])))

        # KPI
        n_coperti = int((cdf["n_settore"] > 0).sum())
        k1, k2, k3, k4 = st.columns(4)
        k1.markdown(ui.kpi_card("Clienti in portafoglio", f"{len(cdf):,}".replace(",", "."),
                                "anagrafica caricata"), unsafe_allow_html=True)
        k2.markdown(ui.kpi_card("Con bandi di settore", f"{n_coperti:,}".replace(",", "."),
                                "≥1 bando specifico ATECO"), unsafe_allow_html=True)
        k3.markdown(ui.kpi_card("Bandi a tutti i settori", len(tutti_ids), "aperti a ogni impresa"),
                    unsafe_allow_html=True)
        k4.markdown(ui.kpi_card("Bandi territoriali", len(territ_ids), "Sicilia / IRFIS aperti",
                                variant="warn"), unsafe_allow_html=True)
        st.write("")

        # Filtri clienti
        fc1, fc2 = st.columns([1, 2])
        with fc1:
            prov = st.multiselect("Provincia", sorted(cdf["provincia"].dropna().unique()), key="cl_prov")
        with fc2:
            cq = st.text_input("Cerca cliente", key="cl_q",
                               placeholder="Ragione sociale, P.IVA o codice ATECO…")

        view = cdf.copy()
        if prov:
            view = view[view["provincia"].isin(prov)]
        if cq:
            ql = cq.lower()
            view = view[
                view["ragione_sociale"].str.lower().str.contains(ql, na=False)
                | view["piva"].astype(str).str.contains(cq, na=False)
                | view["ateco_fmt"].astype(str).str.contains(cq, na=False)
            ]
        view = view.sort_values("n_settore", ascending=False).reset_index(drop=True)

        st.markdown(f"#### {len(view):,} clienti".replace(",", "."))
        show = view[["ragione_sociale", "provincia", "ateco_fmt", "piva", "n_settore"]]
        event = st.dataframe(
            show, hide_index=True, use_container_width=True, height=340,
            on_select="rerun", selection_mode="single-row",
            column_config={
                "ragione_sociale": "Ragione sociale",
                "provincia": "Provincia",
                "ateco_fmt": "ATECO",
                "piva": "P.IVA",
                "n_settore": st.column_config.NumberColumn("Bandi di settore", format="%d"),
            },
        )

        sel = event.selection.rows if event and event.selection else []
        if not sel:
            st.caption("Seleziona un cliente dalla tabella per vedere i bandi compatibili.")
        else:
            cliente = view.iloc[sel[0]]
            a = cliente["ateco"]
            match_ids = set(match_map.get(a, []))
            solo_tutti_ids = tutti_ids - match_ids
            territ_solo_ids = territ_ids - match_ids - tutti_ids

            def _subset(ids):
                sub = aperti_df[aperti_df["id"].isin(ids)].copy()
                return sub.sort_values("giorni_scadenza", na_position="last")

            bandi_match = _subset(match_ids)
            bandi_tutti = _subset(solo_tutti_ids)
            bandi_territ = _subset(territ_solo_ids)

            st.divider()
            st.markdown(f"### {cliente['ragione_sociale']}")
            st.caption(f"ATECO {cliente['ateco_fmt']} · {cliente['provincia']} · "
                       f"P.IVA {cliente['piva']}")

            st.markdown(ui.section(f"Specifici per il settore (ATECO {cliente['ateco_fmt']}) — "
                                   f"{len(bandi_match)} bandi"), unsafe_allow_html=True)
            if len(bandi_match):
                render_cards(bandi_match, [a], f"cm{sel[0]}")
            else:
                st.caption("Nessun bando aperto cita specificamente questo codice ATECO.")

            st.markdown(ui.section(f"Aperti a tutti i settori — {len(bandi_tutti)} bandi"),
                        unsafe_allow_html=True)
            if len(bandi_tutti):
                render_cards(bandi_tutti, [a], f"cu{sel[0]}")
            else:
                st.caption("Nessun bando 'a tutti i settori' aperto al momento.")

            st.markdown(ui.section(f"Territoriali Sicilia / IRFIS — {len(bandi_territ)} bandi"),
                        unsafe_allow_html=True)
            if len(bandi_territ):
                render_cards(bandi_territ, [a], f"ct{sel[0]}")
            else:
                st.caption("Nessun bando territoriale aperto al momento.")
