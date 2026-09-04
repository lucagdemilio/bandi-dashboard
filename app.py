import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta

from database import init_db, get_all_bandi, get_last_log
from scrapers import esegui_tutti, FONTI
from scrapers.utils import ateco_status, parse_ateco_codes
import ui

st.set_page_config(page_title="Studio Lombardo-Culotta · Bandi", layout="wide",
                   page_icon="📋", initial_sidebar_state="collapsed")
init_db()
ui.inject_css(st)

SETTORI_MACRO = [
    "Agricoltura, silvicoltura e pesca", "Agroalimentare", "Alberghiero", "Altri servizi",
    "Artigianato", "Autoveicoli e altri mezzi di trasporto", "Chimica e Farmaceutica",
    "Commercio", "Cultura", "Edilizia", "Elettronica", "Fornitura Energia, Acqua e gestione Rifiuti",
    "ICT", "Meccanica", "Metallurgia", "Mobili, Legno e Carta", "Moda e Tessile",
    "Ristorazione", "Salute", "Servizi di trasporto", "Turismo",
]


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

# ======================= FILTRI (menù a tendina) =======================
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
    # Pulsante "Reimposta" allineato al margine destro della tendina
    _sp, c_reset = st.columns([4, 1])
    with c_reset:
        st.button("Reimposta", icon=":material/restart_alt:", on_click=_reset_filtri,
                  type="secondary", use_container_width=True)

ateco_query = parse_ateco_codes(ateco_input) if ateco_input else []

# Chip riassuntivi dei filtri attivi (sotto la tendina)
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

# ======================= APPLICA FILTRI =======================
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

# ======================= KPI =======================
aperti = int((d["stato"] == "aperto").sum())
in_scad_30 = int(((d["data_scadenza_dt"] >= oggi) & (d["data_scadenza_dt"] <= oggi + timedelta(days=30))).sum())

k1, k2, k3, k4 = st.columns(4)
k1.markdown(ui.kpi_card("Bandi (filtro attivo)", len(d), f"su {len(df)} totali"), unsafe_allow_html=True)
k2.markdown(ui.kpi_card("Aperti", aperti, "scadenza futura / a sportello"), unsafe_allow_html=True)
k3.markdown(ui.kpi_card("In scadenza", in_scad_30, "entro 30 giorni", variant="warn"), unsafe_allow_html=True)
k4.markdown(ui.kpi_card("Ultimo aggiornamento", ultimo[:10], "dati locali"), unsafe_allow_html=True)
st.write("")

# ======================= RISULTATI: header + paginazione =======================
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

@st.dialog("Dettaglio bando", width="large")
def _dettaglio(row):
    st.markdown(ui.detail_html(row, ateco_query), unsafe_allow_html=True)
    link = row.get("link")
    if link and str(link).startswith("http"):
        st.link_button("Apri la scheda ufficiale", link, icon=":material/open_in_new:",
                       type="primary", use_container_width=True)


if tot == 0:
    st.warning("Nessun bando corrisponde ai filtri selezionati. Prova ad allentare i criteri.")
else:
    start = (pagina - 1) * per_pagina
    fetta = d.iloc[start:start + per_pagina]
    grid = st.columns(2)
    for i, (_, row) in enumerate(fetta.iterrows()):
        with grid[i % 2]:
            with st.container(border=True):
                st.markdown(ui.card_body_html(row, ateco_query), unsafe_allow_html=True)
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("Dettagli", key=f"det_{row['id']}", icon=":material/read_more:",
                                 use_container_width=True):
                        _dettaglio(row)
                with b2:
                    link = row.get("link")
                    if link and str(link).startswith("http"):
                        st.link_button("Apri", link, icon=":material/open_in_new:",
                                       type="primary", use_container_width=True)
                    else:
                        st.button("Link n/d", key=f"nd_{row['id']}", disabled=True, use_container_width=True)

# ======================= EXPORT + TABELLA + LOG =======================
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
