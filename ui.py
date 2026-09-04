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

/* Dimensione base del font leggermente più grande (tutto scala in rem) */
html { font-size: 17px; }

/* Larghezza contenuto e spaziatura generale */
.block-container { padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1280px; }

/* Pulsante "Reimposta" compatto e omogeneo agli altri controlli */
[data-testid="stExpander"] .stButton > button {
   padding: .3rem .7rem !important; font-size: .82rem !important; font-weight: 600 !important;
   border-radius: 8px !important; }

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

/* --- Redesign tendina filtri --- */
/* Intestazione dell'expander: barra pulita con accento navy */
[data-testid="stExpander"] { border:1px solid var(--line) !important; border-radius:12px !important;
   box-shadow:0 1px 2px rgba(16,42,67,.04); overflow:hidden; }
[data-testid="stExpander"] summary, [data-testid="stExpander"] details > summary {
   font-weight:650 !important; color:var(--nav) !important; background:#f7f9fc; padding:.55rem .9rem !important; }
[data-testid="stExpander"] summary:hover { background:#eef3f9; }
[data-testid="stExpander"] [data-testid="stExpanderDetails"] { padding:.4rem .3rem .2rem; }

/* Micro-intestazioni di sezione dentro i filtri */
.filter-sec { font-size:.68rem; font-weight:800; letter-spacing:.1em; text-transform:uppercase;
   color:var(--nav2); margin:.55rem 0 .35rem; padding-bottom:.28rem; border-bottom:1px solid var(--line);
   display:flex; align-items:center; gap:.4rem; }

/* Restyle dei campi (select/multiselect/input) coerente col tema */
[data-testid="stExpander"] [data-baseweb="select"] > div,
[data-testid="stExpander"] [data-baseweb="input"] > div,
[data-testid="stExpander"] input[type="text"] {
   border-radius:9px !important; border-color:#d5deea !important; }
[data-testid="stExpander"] [data-baseweb="select"] > div:focus-within,
[data-testid="stExpander"] [data-baseweb="input"] > div:focus-within {
   border-color:var(--nav2) !important; box-shadow:0 0 0 2px rgba(29,92,143,.15) !important; }
/* Tag selezionati nei multiselect in tinta navy */
[data-testid="stExpander"] [data-baseweb="tag"] { background:var(--nav) !important; border-radius:7px !important; }

/* Chip riassuntivi dei filtri attivi (sotto la tendina) */
.chips { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; margin:.5rem 0 .2rem; }
.chips .lbl { font-size:.72rem; font-weight:700; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }
.chip { display:inline-flex; align-items:center; gap:.35rem; background:#eaf1f9; color:var(--nav);
   font-size:.76rem; font-weight:600; padding:.2rem .6rem; border-radius:999px; border:1px solid #d5e2f0; }
.chip b { font-weight:700; }
.chip.warn { background:#fdeee3; color:var(--warn); border-color:#f6d6bf; }

/* KPI cards */
.kpi { background: var(--surface); border:1px solid var(--line); border-radius:12px;
       padding: .9rem 1.1rem; box-shadow: 0 1px 2px rgba(16,42,67,.04); height:100%; }
.kpi .k-label { color: var(--muted); font-size:.75rem; text-transform:uppercase; letter-spacing:.04em; font-weight:600; }
.kpi .k-value { color: var(--nav); font-size:1.9rem; font-weight:700; line-height:1.1; margin-top:.2rem; }
.kpi .k-sub { color: var(--muted); font-size:.72rem; margin-top:.15rem; }
.kpi.accent { border-left:4px solid var(--nav2); }
.kpi.warn   { border-left:4px solid var(--warn); }

/* Card bando: il BOX è il container Streamlit (border=True); .bando è il contenuto */
[data-testid="stVerticalBlockBorderWrapper"] { border:1px solid var(--line) !important;
   border-radius:12px !important; box-shadow:0 1px 2px rgba(16,42,67,.04);
   transition: box-shadow .15s ease, border-color .15s ease; }
[data-testid="stVerticalBlockBorderWrapper"]:hover { box-shadow:0 6px 18px rgba(16,42,67,.09); border-color:#cfd8e3; }
.bando .top { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.5rem; }
.bando .title { font-size:1.02rem; font-weight:650; color:var(--ink); margin:.1rem 0 .45rem; line-height:1.35;
   display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.bando .meta { display:flex; flex-wrap:wrap; gap:.3rem 1rem; color:var(--muted); font-size:.82rem; margin-bottom:.5rem; }
.bando .meta b { color:#3d4753; font-weight:600; }
.bando .scadline { border-top:1px solid var(--line); padding-top:.5rem; margin-top:.2rem; }

/* Pulsanti dentro le card, compatti e coerenti */
[data-testid="stVerticalBlockBorderWrapper"] .stButton > button,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stLinkButton"] > a {
   font-size:.8rem !important; font-weight:600 !important; padding:.28rem .6rem !important;
   border-radius:8px !important; min-height:0 !important; }

/* Finestra dettaglio (modale) */
.detail .top { display:flex; align-items:center; gap:.5rem; flex-wrap:wrap; margin-bottom:.7rem; }
.detail h3 { color:var(--nav); font-size:1.15rem; font-weight:700; margin:.1rem 0 .8rem; line-height:1.3; }
.detail .drow { display:grid; grid-template-columns:160px 1fr; gap:.2rem 1rem; padding:.45rem 0;
   border-bottom:1px solid var(--line); font-size:.9rem; }
.detail .drow .dl { color:var(--muted); font-weight:700; text-transform:uppercase; font-size:.68rem;
   letter-spacing:.05em; padding-top:.15rem; }
.detail .drow .dv { color:var(--ink); }
.detail .note { margin-top:.8rem; background:#f4f6f9; border-radius:9px; padding:.6rem .8rem;
   font-size:.85rem; color:#3d4753; }

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


def _badges(row, ateco_query=None) -> str:
    fonte = row.get("fonte") or ""
    stato = row.get("stato") or "sconosciuto"
    giorni = row.get("giorni_scadenza")
    benef = row.get("beneficiari")
    ben_badge = f'<span class="badge ben">{html.escape(str(benef))}</span>' if benef and str(benef) not in ("None", "nan") else ""
    at_badge = ateco_badge(ateco_status(row.get("codici_ateco"), ateco_query)) if ateco_query else ""
    return f'{source_badge(fonte)} {stato_badge(stato, giorni)} {ben_badge} {at_badge}'


def card_body_html(row, ateco_query=None) -> str:
    """Contenuto della card (senza pulsanti: quelli sono widget Streamlit)."""
    titolo = html.escape(str(row.get("titolo") or "Senza titolo"))
    giorni = row.get("giorni_scadenza")
    scadenza = row.get("data_scadenza")

    meta_parts = [
        _kv("Ente", row.get("ente")),
        _kv("Programma", row.get("programma")),
        _kv("Tipo", row.get("tipo_agevolazione")),
        _kv("Settore", row.get("settore")),
    ]
    meta = "".join(p for p in meta_parts if p)

    return f"""
<div class="bando">
  <div class="top">{_badges(row, ateco_query)}</div>
  <div class="title">{titolo}</div>
  <div class="meta">{meta}</div>
  <div class="scadline">{_scad_html(scadenza, giorni)}</div>
</div>
"""


def detail_html(row, ateco_query=None) -> str:
    """Riepilogo completo di un bando, mostrato nella finestra modale."""
    titolo = html.escape(str(row.get("titolo") or "Senza titolo"))
    giorni = row.get("giorni_scadenza")
    scad = row.get("data_scadenza")
    scad_txt = "—"
    if scad:
        scad_txt = html.escape(str(scad))
        if pd.notna(giorni) and giorni is not None:
            scad_txt += f" ({int(giorni)} giorni)"
    elif str(row.get("scadenza_raw") or "") not in ("", "None", "nan"):
        scad_txt = html.escape(str(row.get("scadenza_raw"))) + " (da verificare)"
    else:
        scad_txt = "Non indicata / a sportello"

    campi = [
        ("Fonte", row.get("fonte")),
        ("Ente / concedente", row.get("ente")),
        ("Programma", row.get("programma")),
        ("Tipo agevolazione", row.get("tipo_agevolazione")),
        ("Beneficiari", row.get("beneficiari")),
        ("Settore", row.get("settore")),
        ("Codici ATECO", row.get("codici_ateco")),
        ("Importo / dotazione", row.get("importo")),
        ("Apertura", row.get("data_apertura")),
        ("Scadenza", scad_txt),
        ("Stato", row.get("stato")),
    ]
    righe = ""
    for label, value in campi:
        if value is None or str(value).strip() in ("", "None", "nan"):
            continue
        righe += f'<div class="drow"><div class="dl">{html.escape(label)}</div>' \
                 f'<div class="dv">{html.escape(str(value))}</div></div>'

    note = row.get("note")
    note_html = ""
    if note and str(note).strip() not in ("", "None", "nan"):
        note_html = f'<div class="note">{html.escape(str(note))}</div>'

    return f"""
<div class="detail">
  <div class="top">{_badges(row, ateco_query)}</div>
  <h3>{titolo}</h3>
  {righe}
  {note_html}
</div>
"""


def kpi_card(label: str, value, sub: str = "", variant: str = "accent") -> str:
    sub_html = f'<div class="k-sub">{html.escape(sub)}</div>' if sub else ""
    return f'<div class="kpi {variant}"><div class="k-label">{html.escape(label)}</div>' \
           f'<div class="k-value">{html.escape(str(value))}</div>{sub_html}</div>'


def section(label: str) -> str:
    """Micro-intestazione di sezione dentro la tendina filtri."""
    return f'<div class="filter-sec">{html.escape(label)}</div>'


def chips_html(items: list) -> str:
    """Chip riassuntivi dei filtri attivi. items = lista di (etichetta, valore, cls)."""
    if not items:
        return ""
    parts = []
    for it in items:
        label, value, cls = (list(it) + [""])[:3]
        parts.append(f'<span class="chip {cls}"><b>{html.escape(str(label))}</b> '
                     f'{html.escape(str(value))}</span>')
    return '<div class="chips"><span class="lbl">Filtri attivi</span>' + "".join(parts) + "</div>"
