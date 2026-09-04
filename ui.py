"""
Livello di presentazione della dashboard: tema CSS e componenti (card, badge).
Stile: professionale/istituzionale sobrio (blu navy + grigi).
"""
from __future__ import annotations
import html
import pandas as pd
from scrapers.utils import ateco_status

# Colore identificativo per fonte (toni sobri e distinguibili).
SOURCE_STYLES = {
    "UE": ("#1a4d8f", "UE"),
    "Nazionale": ("#2f6b4f", "Nazionale"),
    "Nazionale (regionalizzato)": ("#2f6b4f", "Nazionale"),
    "Regionale Sicilia": ("#a4562a", "Regione Sicilia"),
    "Invitalia": ("#276b6b", "Invitalia"),
    "IRFIS": ("#574b8c", "IRFIS"),
}
DEFAULT_SOURCE = ("#5b6572", "Altro")

CSS = """
<style>
:root {
  --nav:#14385f; --nav2:#1d5c8f; --ink:#1f2933; --muted:#66727f;
  --line:#e3e8ef; --surface:#ffffff; --bg:#f4f6f9;
  --ok:#2f855a; --warn:#c05621; --off:#8a94a1;
  --sans: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
          "Helvetica Neue", "Inter", "Segoe UI", Roboto, sans-serif;
  --emoji: "Apple Color Emoji", "Segoe UI Emoji", "Noto Color Emoji";
}
/* Font di sistema Apple (San Francisco) su tutta l'app, con emoji stile Apple.
   NB: si evita di toccare bare span/div per non rompere il font delle icone Material. */
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"],
.stMarkdown, .stMarkdown p, .stMarkdown span, .stMarkdown div, .stMarkdown li,
h1, h2, h3, h4, h5, h6, .stButton > button, .stTextInput input, .stSelectbox,
.stMultiSelect, .stCheckbox, .stExpander summary, input, textarea, select, button {
  font-family: var(--sans), var(--emoji) !important;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
/* Ripristina il font delle icone Material di Streamlit (freccette, ecc.) */
[data-testid="stIconMaterial"], .material-icons, [class*="material-symbols"] {
  font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
}

/* Nasconde la chrome di Streamlit (barra in alto a destra, menu, sidebar, footer) */
header[data-testid="stHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"],
#MainMenu, [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"],
[data-testid="collapsedControl"], footer { display: none !important; }

/* Collassa (senza nascondere: il JS deve girare) il contenitore dell'iframe
   del componente pull-to-refresh, così non lascia spazi vuoti. */
[data-testid="stIFrame"] { height: 0 !important; }
div[data-testid="stElementContainer"]:has([data-testid="stIFrame"]) {
  height: 0 !important; min-height: 0 !important; margin: 0 !important; overflow: hidden; }

/* Larghezza contenuto e spaziatura generale */
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1280px; }

/* Griglia card a 2 colonne (riempie lo spazio; 1 colonna su schermi stretti) */
.cards-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: .85rem; }
.cards-grid .bando { margin-bottom: 0; }
@media (max-width: 900px) { .cards-grid { grid-template-columns: 1fr; } }

/* Header dashboard + branding */
.dash-header { border-bottom: 2px solid var(--nav); padding-bottom: .7rem; margin-bottom: 1rem; }
.dash-header h1 { font-size: 1.55rem; font-weight: 700; color: var(--nav); margin: .55rem 0 0; letter-spacing:-.01em; }
.dash-header p { color: var(--muted); margin:.2rem 0 0; font-size:.85rem; }
.upd-note { color: var(--muted); font-size:.74rem; margin:.15rem 0 0; }
.brand { display:flex; align-items:center; gap:.85rem; }
.brand .mono { width:58px; height:58px; border-radius:14px; background:var(--nav); color:#fff;
   display:flex; align-items:center; justify-content:center; font-weight:800; font-size:1.15rem; letter-spacing:.03em;
   box-shadow:0 3px 10px rgba(20,56,95,.28); flex:0 0 auto; }
.brand .name { line-height:1.2; }
.brand .name .firm { font-weight:700; color:var(--nav); font-size:1.7rem; letter-spacing:-.015em; }
.brand .name .role { color:var(--muted); font-size:.82rem; font-weight:600; margin-top:.28rem;
   text-transform:uppercase; letter-spacing:.11em; }

/* Riga descrittiva (eyebrow) sotto l'header */
.obs-line { color:var(--muted); font-size:.82rem; margin:.1rem 0 0; }
.obs-line b { color:var(--nav); font-weight:650; }

/* Pannello filtri in pagina */
.filter-title { font-weight:700; color:var(--nav); font-size:.9rem; margin:.1rem 0 .1rem; display:flex; align-items:center; gap:.4rem; }

/* KPI cards */
.kpi { background: var(--surface); border:1px solid var(--line); border-radius:12px;
       padding: .9rem 1.1rem; box-shadow: 0 1px 2px rgba(16,42,67,.04); height:100%; }
.kpi .k-label { color: var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; font-weight:600; }
.kpi .k-value { color: var(--nav); font-size:1.9rem; font-weight:700; line-height:1.1; margin-top:.2rem; }
.kpi .k-sub { color: var(--muted); font-size:.72rem; margin-top:.15rem; }
.kpi.accent { border-left:4px solid var(--nav2); }
.kpi.warn   { border-left:4px solid var(--warn); }

/* Card bando */
.bando { background: var(--surface); border:1px solid var(--line); border-radius:12px;
         padding: 1rem 1.15rem; margin-bottom:.8rem; box-shadow:0 1px 2px rgba(16,42,67,.04);
         transition: box-shadow .15s ease, border-color .15s ease; }
.bando:hover { box-shadow:0 6px 18px rgba(16,42,67,.09); border-color:#cfd8e3; }
.bando .top { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.5rem; }
.bando .title { font-size:1.02rem; font-weight:650; color:var(--ink); margin:.1rem 0 .45rem; line-height:1.35; }
.bando .meta { display:flex; flex-wrap:wrap; gap:.35rem 1.1rem; color:var(--muted); font-size:.82rem; margin-bottom:.55rem; }
.bando .meta b { color:#3d4753; font-weight:600; }
.bando .foot { display:flex; align-items:center; justify-content:space-between; gap:1rem;
               border-top:1px solid var(--line); padding-top:.55rem; margin-top:.2rem; }
.bando .apri { display:inline-flex; align-items:center; gap:.4rem; background:var(--nav); color:#fff !important;
               text-decoration:none; font-size:.82rem; font-weight:600; padding:.34rem .8rem; border-radius:7px; white-space:nowrap; }
.bando .apri:hover { background:var(--nav2); }
.bando .apri::after { content:''; width:13px; height:13px; flex:0 0 auto;
   background:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23ffffff' stroke-width='2.4' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M14 4h6v6'/%3E%3Cpath d='M20 4 10 14'/%3E%3Cpath d='M19 13v6a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V6a1 1 0 0 1 1-1h6'/%3E%3C/svg%3E") no-repeat center / contain; }
.bando .noapri { color:var(--off); font-size:.8rem; font-style:italic; }

/* Badge */
.badge { display:inline-flex; align-items:center; gap:.3rem; font-size:.71rem; font-weight:700;
         padding:.16rem .5rem; border-radius:999px; letter-spacing:.02em; white-space:nowrap; }
.badge.src { color:#fff; }
.badge.st-aperto { background:#e6f4ec; color:var(--ok); }
.badge.st-scad   { background:#fdece1; color:var(--warn); }
.badge.st-chiuso { background:#eef1f4; color:var(--off); }
.badge.ben { background:#eef2f8; color:#3a527a; }
.badge.ateco-ok { background:#e6f4ec; color:var(--ok); }
.badge.ateco-all { background:#e8f0fb; color:#1a4d8f; }

.scad-info { font-size:.82rem; color:var(--muted); }
.scad-info .gg { font-weight:700; color:var(--warn); }
.scad-info .gg.calm { color:var(--ok); }

/* Sidebar */
section[data-testid="stSidebar"] { background:#fbfcfe; border-right:1px solid var(--line); }
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 { color:var(--nav); }
.side-title { font-weight:700; color:var(--nav); font-size:.95rem; margin:.2rem 0 .4rem; }

/* Metric nativi (log ecc.) più discreti */
hr { margin: 1rem 0; }
</style>
"""


def inject_css(st):
    st.markdown(CSS, unsafe_allow_html=True)


def brand_title() -> str:
    """Blocco brand: monogramma + nome studio (grande) + sottotitolo."""
    return """
<div class="brand">
  <div class="mono">SLC</div>
  <div class="name">
    <div class="firm">Studio Lombardo - Culotta</div>
    <div class="role">Consulenza legale e finanziaria</div>
  </div>
</div>
"""


def obs_line() -> str:
    """Riga descrittiva della dashboard (fonti aggregate)."""
    return ('<div class="obs-line"><b>Osservatorio Bandi</b> · Unione Europea · '
            'Nazionale (incentivi.gov.it) · Invitalia · Regione Siciliana · IRFIS-FinSicilia</div>')


def head_divider() -> str:
    return '<hr style="border:none;border-top:2px solid #14385f;margin:.6rem 0 1rem;">'


def ateco_badge(status: str) -> str:
    if status == "match":
        return '<span class="badge ateco-ok">✓ ATECO compatibile</span>'
    if status == "tutti":
        return '<span class="badge ateco-all">Tutti i settori</span>'
    return ""


def source_badge(fonte: str) -> str:
    color, label = SOURCE_STYLES.get(fonte, DEFAULT_SOURCE)
    return f'<span class="badge src" style="background:{color}">{html.escape(label)}</span>'


def stato_badge(stato: str, giorni) -> str:
    urgente = pd.notna(giorni) and giorni is not None and giorni <= 14 and giorni >= 0
    if stato == "aperto" and urgente:
        return '<span class="badge st-scad">In scadenza</span>'
    if stato == "aperto":
        return '<span class="badge st-aperto">Aperto</span>'
    if stato == "chiuso":
        return '<span class="badge st-chiuso">Chiuso</span>'
    return '<span class="badge st-chiuso">Da verificare</span>'


def _scad_html(scadenza, giorni) -> str:
    if scadenza and pd.notna(giorni) and giorni is not None:
        g = int(giorni)
        cls = "gg" if g <= 30 else "gg calm"
        return f'<span class="scad-info">Scade il <b>{html.escape(str(scadenza))}</b> · <span class="{cls}">{g} gg</span></span>'
    if scadenza:
        return f'<span class="scad-info">Scadenza: <b>{html.escape(str(scadenza))}</b></span>'
    return '<span class="scad-info">Scadenza non indicata / a sportello</span>'


def _kv(label: str, value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)) or str(value).strip() in ("", "None", "nan"):
        return ""
    return f'<span><b>{label}:</b> {html.escape(str(value))}</span>'


def card_html(row, ateco_query=None) -> str:
    titolo = html.escape(str(row.get("titolo") or "Senza titolo"))
    fonte = row.get("fonte") or ""
    stato = row.get("stato") or "sconosciuto"
    giorni = row.get("giorni_scadenza")
    scadenza = row.get("data_scadenza")

    benef = row.get("beneficiari")
    ben_badge = f'<span class="badge ben">{html.escape(str(benef))}</span>' if benef and str(benef) not in ("None", "nan") else ""

    at_badge = ""
    if ateco_query:
        at_badge = ateco_badge(ateco_status(row.get("codici_ateco"), ateco_query))

    meta_parts = [
        _kv("Ente", row.get("ente")),
        _kv("Programma", row.get("programma")),
        _kv("Tipo", row.get("tipo_agevolazione")),
        _kv("Settore", row.get("settore")),
        _kv("Importo", row.get("importo")),
    ]
    meta = "".join(p for p in meta_parts if p)

    link = row.get("link")
    if link and str(link).startswith("http"):
        apri = f'<a class="apri" href="{html.escape(str(link))}" target="_blank" rel="noopener">Apri scheda</a>'
    else:
        apri = '<span class="noapri">Link non disponibile</span>'

    return f"""
<div class="bando">
  <div class="top">{source_badge(fonte)} {stato_badge(stato, giorni)} {ben_badge} {at_badge}</div>
  <div class="title">{titolo}</div>
  <div class="meta">{meta}</div>
  <div class="foot">{_scad_html(scadenza, giorni)} {apri}</div>
</div>
"""


def kpi_card(label: str, value, sub: str = "", variant: str = "accent") -> str:
    sub_html = f'<div class="k-sub">{html.escape(sub)}</div>' if sub else ""
    return f'<div class="kpi {variant}"><div class="k-label">{html.escape(label)}</div>' \
           f'<div class="k-value">{html.escape(str(value))}</div>{sub_html}</div>'
