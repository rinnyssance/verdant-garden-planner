"""Verdant visual system: palette, CSS, inline icons, botanical illustrations and HTML components.

Everything here is presentation only. Components render real garden data passed
in by the screens; nothing here invents values.
"""

from __future__ import annotations

import html

FOREST = "#244C3A"
SAGE = "#A8B99D"
IVORY = "#F8F5EC"
TERRACOTTA = "#C77452"
INK = "#27372E"
GOLD = "#C9A464"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap');
:root {
  --forest:#244C3A; --forest-2:#2F5E48; --sage:#A8B99D; --sage-soft:#E6ECDF; --ivory:#F8F5EC;
  --paper:#FFFDF7; --terracotta:#C77452; --terracotta-soft:#F6E2D8; --ink:#27372E; --muted:#5E6B62;
  --gold:#C9A464; --gold-soft:#F4EAD3; --line:rgba(36,76,58,.12);
  --shadow:0 1px 2px rgba(39,55,46,.05), 0 8px 24px rgba(39,55,46,.07);
  --radius:18px;
}
/* Typography: never touch spans globally, Streamlit's icon font lives there. */
html, body, .stApp, p, label, input, textarea, li, td, th, button p { font-family:'Inter', system-ui, sans-serif; }
h1, h2, h3, h4, .vd-serif { font-family:'Fraunces', Georgia, serif !important; color:var(--forest); letter-spacing:-.015em; }
.stApp { background: radial-gradient(1200px 500px at 85% -10%, #EEF2E6 0%, rgba(238,242,230,0) 60%), var(--ivory); color:var(--ink); }
header[data-testid="stHeader"] { background:transparent; }
[data-testid="stDecoration"] { display:none; }
.block-container { padding-top:2.2rem; padding-bottom:4rem; max-width:1180px; }
hr { border-color:var(--line); }

/* ---- Sidebar ---------------------------------------------------------- */
[data-testid="stSidebar"] { background:linear-gradient(180deg, #23493A 0%, #1E3F32 100%); }
[data-testid="stSidebar"] * { color:#EEF1E8; }
[data-testid="stSidebar"] .vd-brand-name { font-family:'Fraunces', Georgia, serif; font-size:1.65rem; font-weight:600; color:#FBF8EF; line-height:1; }
[data-testid="stSidebar"] .vd-brand-tag { font-size:.78rem; color:#C9D4C1; margin-top:.35rem; }
[data-testid="stSidebar"] .vd-side-label { font-size:.7rem; letter-spacing:.12em; text-transform:uppercase; color:#AFC0A6; margin:1.2rem 0 .35rem; }
[data-testid="stSidebar"] [data-baseweb="select"] > div { background:rgba(255,255,255,.08); border-color:rgba(255,255,255,.18); border-radius:12px; }
[data-testid="stSidebar"] [data-baseweb="select"] svg { fill:#EEF1E8; }
[data-testid="stSidebar"] [role="radiogroup"] { gap:.15rem; width:100%; }
[data-testid="stSidebar"] [role="radiogroup"] label { width:100%; padding:.55rem .75rem; border-radius:12px; margin:0; transition:background .15s; }
[data-testid="stSidebar"] [role="radiogroup"] label > div:first-child { display:none; }
[data-testid="stSidebar"] [role="radiogroup"] label:hover { background:rgba(255,255,255,.07); }
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked),
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] { background:rgba(248,245,236,.14); box-shadow:inset 3px 0 0 var(--gold); }
/* Newer Streamlit (react-aria): hide the radio circle, keep the accessible input. */
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) { display:none; }
[data-testid="stSidebar"] [data-testid="stRadioOption"] { cursor:pointer; }
[data-testid="stSidebar"] [data-testid="stRadioOption"]:has(input:focus-visible) { outline:2px solid var(--gold); outline-offset:1px; }
[data-testid="stSidebar"] .react-aria-ComboBox [role="group"] { background:rgba(255,255,255,.10) !important; border:1px solid rgba(255,255,255,.24) !important; border-radius:12px; }
[data-testid="stSidebar"] .react-aria-ComboBox input { color:#FBF8EF !important; -webkit-text-fill-color:#FBF8EF; font-weight:500; }
[data-testid="stSidebar"] [role="radiogroup"] label p { font-size:.95rem; font-weight:500; }
[data-testid="stSidebar"] [role="radiogroup"] label:focus-within { outline:2px solid var(--gold); outline-offset:1px; }
[data-testid="stSidebar"] .vd-side-foot { font-size:.75rem; color:#AFC0A6; line-height:1.45; margin-top:1.5rem; }

/* ---- Mobile context bar (sidebar collapses into a menu on phones) ------ */
.vd-mobilebar { display:none; }
@media (max-width: 768px) {
  .vd-mobilebar { display:flex; align-items:center; gap:.5rem; background:var(--paper); border:1px solid var(--line);
                  border-radius:999px; padding:.4rem .8rem; font-size:.85rem; color:var(--muted); margin-bottom:1rem; box-shadow:var(--shadow); }
  .vd-mobilebar b { color:var(--forest); }
  .block-container { padding-left:1rem; padding-right:1rem; padding-top:3.2rem; }
}

/* ---- Page header ------------------------------------------------------ */
.vd-eyebrow { font-size:.75rem; letter-spacing:.14em; text-transform:uppercase; color:var(--terracotta); font-weight:600; }
.vd-h1 { font-family:'Fraunces', Georgia, serif; font-size:2.6rem; line-height:1.08; color:var(--forest); margin:.3rem 0 .45rem; font-weight:500; }
.vd-lede { color:var(--muted); font-size:1.02rem; max-width:52rem; }
.vd-h2 { font-family:'Fraunces', Georgia, serif; font-size:1.45rem; color:var(--forest); margin:1.6rem 0 .2rem; font-weight:500; display:flex; align-items:center; gap:.5rem; }
.vd-sub { color:var(--muted); font-size:.88rem; margin-bottom:.8rem; }
@media (max-width: 640px) { .vd-h1 { font-size:2rem; } }

/* ---- Cards ------------------------------------------------------------ */
[class*="st-key-vc-"] { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius);
                         box-shadow:var(--shadow); padding:1.05rem 1.15rem 1.1rem; }
.vd-card { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:1rem 1.15rem; }
.vd-grid { display:grid; gap:1rem; grid-template-columns:repeat(auto-fill, minmax(240px, 1fr)); }
.vd-metrics { display:grid; gap:1rem; grid-template-columns:repeat(4, minmax(0, 1fr)); margin:1.2rem 0 .4rem; }
@media (max-width: 1100px) { .vd-metrics { grid-template-columns:repeat(2, minmax(0, 1fr)); } }
@media (max-width: 480px) {
  .vd-metrics { gap:.6rem; }
  .vd-metric { padding:.75rem .8rem; gap:.55rem; }
  .vd-metric .vd-ico { width:32px; height:32px; border-radius:10px; }
  .vd-metric .vd-num { font-size:1.55rem; }
  .vd-metric .vd-lbl { font-size:.76rem; }
}
.vd-metric { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:1rem 1.1rem; display:flex; gap:.85rem; align-items:flex-start; }
.vd-metric .vd-ico { flex:none; width:42px; height:42px; border-radius:12px; display:grid; place-items:center; background:var(--sage-soft); color:var(--forest); }
.vd-metric.warm .vd-ico { background:var(--terracotta-soft); color:#9A4F31; }
.vd-metric.gold .vd-ico { background:var(--gold-soft); color:#7A5C1E; }
.vd-metric .vd-num { font-family:'Fraunces', Georgia, serif; font-size:2rem; line-height:1; color:var(--ink); }
.vd-metric .vd-lbl { font-size:.82rem; color:var(--muted); margin-top:.25rem; }
.vd-metric .vd-note { font-size:.75rem; color:var(--terracotta); margin-top:.2rem; }
.vd-ico svg, .vd-inline svg { display:block; }
.vd-inline { display:inline-flex; vertical-align:-3px; margin-right:.3rem; }

/* ---- Chips, badges, progress -------------------------------------------- */
.vd-chip { display:inline-flex; align-items:center; gap:.3rem; padding:.18rem .6rem; border-radius:999px; font-size:.76rem; font-weight:500;
           background:var(--sage-soft); color:var(--forest); border:1px solid rgba(36,76,58,.08); margin:.1rem .25rem .1rem 0; white-space:nowrap; }
.vd-chip.warm { background:var(--terracotta-soft); color:#8E4A2E; }
.vd-chip.gold { background:var(--gold-soft); color:#6E531B; }
.vd-chip.ink { background:#E9ECE8; color:var(--ink); }
.vd-chip.out { background:transparent; border-color:var(--line); color:var(--muted); }
.vd-sev-action { background:#F3D9CC; color:#8A3F22; }
.vd-sev-watch { background:var(--gold-soft); color:#6E531B; }
.vd-sev-info { background:var(--sage-soft); color:var(--forest); }
.vd-stages { display:flex; gap:3px; margin:.55rem 0 .25rem; }
.vd-stages i { flex:1; height:6px; border-radius:3px; background:#E3E7DD; }
.vd-stages i.on { background:linear-gradient(90deg, var(--sage), var(--forest)); }
.vd-stagecap { font-size:.74rem; color:var(--muted); }

/* ---- Plant / seed / space cards ---------------------------------------- */
.vd-art { border-radius:14px; overflow:hidden; aspect-ratio: 16 / 9; background:#EEF1E6; margin-bottom:.75rem; }
.vd-art svg { width:100%; height:100%; display:block; }
.vd-title { font-family:'Fraunces', Georgia, serif; font-size:1.2rem; color:var(--ink); line-height:1.2; }
.vd-cultivar { font-family:'Fraunces', Georgia, serif; font-style:italic; color:var(--muted); font-size:.95rem; }
.vd-meta { font-size:.82rem; color:var(--muted); margin-top:.35rem; line-height:1.5; }
.vd-kv { display:grid; grid-template-columns:auto 1fr; gap:.25rem .8rem; font-size:.84rem; margin-top:.6rem; }
.vd-kv dt { color:var(--muted); } .vd-kv dd { margin:0; color:var(--ink); }
.vd-indicators { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.6rem; }
[class*="st-key-vc-"] img { border-radius:14px; }

/* ---- Timeline ---------------------------------------------------------- */
.vd-timeline { display:flex; gap:0; margin:.7rem 0 .2rem; }
.vd-timeline .step { flex:1; position:relative; padding-top:16px; font-size:.74rem; color:var(--muted); }
.vd-timeline .step::before { content:""; position:absolute; top:5px; left:0; right:0; height:2px; background:#E1E6DA; }
.vd-timeline .step::after { content:""; position:absolute; top:0; left:0; width:12px; height:12px; border-radius:50%; background:#fff; border:2px solid #CBD5C3; }
.vd-timeline .step.done::before { background:var(--sage); }
.vd-timeline .step.done::after { background:var(--forest); border-color:var(--forest); }
.vd-timeline .step b { display:block; color:var(--ink); font-weight:600; font-size:.78rem; }

/* ---- Weather ----------------------------------------------------------- */
.vd-weather { display:grid; grid-auto-flow:column; grid-auto-columns:minmax(112px, 1fr); gap:.7rem; overflow-x:auto; padding-bottom:.3rem; }
.vd-day { background:var(--paper); border:1px solid var(--line); border-radius:16px; padding:.85rem .7rem; text-align:center; box-shadow:var(--shadow); }
.vd-day.today { background:linear-gradient(160deg, #2C5A45, var(--forest)); border-color:transparent; }
.vd-day.today * { color:#F8F5EC !important; }
.vd-day .d { font-size:.78rem; font-weight:600; color:var(--muted); text-transform:uppercase; letter-spacing:.06em; }
.vd-day .ic { display:grid; place-items:center; margin:.45rem 0; color:var(--forest); }
.vd-day .hi { font-family:'Fraunces', Georgia, serif; font-size:1.35rem; color:var(--ink); }
.vd-day .lo { font-size:.85rem; color:var(--muted); }
.vd-day .rn { font-size:.74rem; color:#3D6D8A; margin-top:.25rem; }
.vd-day .fr { font-size:.68rem; font-weight:600; color:#8A3F22; background:#F3D9CC; border-radius:999px; padding:.05rem .45rem; display:inline-block; margin-top:.3rem; }
.vd-day.today .fr { background:rgba(255,255,255,.18); }

/* ---- Lists, tables, journal -------------------------------------------- */
.vd-list { list-style:none; padding:0; margin:0; }
.vd-list li { display:flex; gap:.75rem; align-items:center; padding:.6rem 0; border-bottom:1px solid var(--line); font-size:.9rem; }
.vd-list li:last-child { border-bottom:none; }
.vd-when { flex:none; width:4.2rem; text-align:center; background:var(--sage-soft); color:var(--forest); border-radius:10px; padding:.25rem 0; font-size:.72rem; font-weight:600; line-height:1.2; }
.vd-when b { display:block; font-family:'Fraunces', Georgia, serif; font-size:1.05rem; }
.vd-table { width:100%; border-collapse:separate; border-spacing:0; font-size:.86rem; background:var(--paper); border:1px solid var(--line); border-radius:14px; overflow:hidden; }
.vd-table th { text-align:left; font-weight:600; font-size:.72rem; letter-spacing:.08em; text-transform:uppercase; color:var(--muted); background:#F2F0E6; padding:.55rem .75rem; }
.vd-table td { padding:.55rem .75rem; border-top:1px solid var(--line); color:var(--ink); vertical-align:top; }
.vd-entry { display:grid; grid-template-columns:5.2rem 1fr; gap:1.1rem; }
.vd-date { text-align:center; border-right:1px dashed rgba(36,76,58,.25); padding-right:1rem; }
.vd-date .dd { font-family:'Fraunces', Georgia, serif; font-size:2.2rem; color:var(--forest); line-height:1; }
.vd-date .mm { font-size:.72rem; letter-spacing:.12em; text-transform:uppercase; color:var(--terracotta); font-weight:600; }
.vd-date .tt { font-size:.72rem; color:var(--muted); margin-top:.2rem; }
.vd-note-text { font-family:'Fraunces', Georgia, serif; font-size:1.02rem; color:var(--ink); line-height:1.55; }
.vd-week { display:grid; grid-template-columns:repeat(7, minmax(0, 1fr)); gap:.4rem; margin:.4rem 0 1rem; }
.vd-week .wd { background:var(--paper); border:1px solid var(--line); border-radius:12px; padding:.45rem .2rem; text-align:center; font-size:.72rem; color:var(--muted); }
.vd-week .wd b { display:block; font-family:'Fraunces', Georgia, serif; font-size:1.15rem; color:var(--ink); }
.vd-week .wd.sel { background:var(--forest); border-color:var(--forest); }
.vd-week .wd.sel, .vd-week .wd.sel b { color:#F8F5EC; }
.vd-week .dot { display:inline-block; min-width:1.2rem; border-radius:999px; background:var(--terracotta-soft); color:#8E4A2E; font-weight:600; margin-top:.15rem; }
.vd-week .wd.sel .dot { background:rgba(255,255,255,.2); color:#fff; }

/* ---- Empty states ------------------------------------------------------ */
.vd-empty { display:flex; gap:1rem; align-items:center; background:repeating-linear-gradient(135deg, #FBF9F2, #FBF9F2 12px, #F7F4EA 12px, #F7F4EA 24px);
            border:1px dashed rgba(36,76,58,.25); border-radius:var(--radius); padding:1.1rem 1.2rem; color:var(--muted); }
.vd-empty .vd-ico { flex:none; width:46px; height:46px; border-radius:50%; display:grid; place-items:center; background:var(--sage-soft); color:var(--forest); }
.vd-empty b { color:var(--ink); font-family:'Fraunces', Georgia, serif; font-weight:500; font-size:1.05rem; display:block; }

/* ---- Streamlit widgets -------------------------------------------------- */
div.stButton > button, div.stFormSubmitButton > button { border-radius:999px; border:1px solid rgba(36,76,58,.25); background:var(--paper); color:var(--forest); font-weight:500; padding:.35rem 1rem; }
div.stButton > button:hover, div.stFormSubmitButton > button:hover { border-color:var(--forest); color:var(--forest); background:#F3F5EE; }
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] { background:var(--forest); border-color:var(--forest); color:#FBF8EF; }
div.stButton > button[kind="primary"]:hover, div.stFormSubmitButton > button[kind="primary"]:hover { background:var(--forest-2); color:#fff; }
div.stButton > button:focus-visible, div.stFormSubmitButton > button:focus-visible { outline:3px solid var(--gold); outline-offset:2px; }
[data-testid="stExpander"] details { background:var(--paper); border:1px solid var(--line); border-radius:14px; }
[data-testid="stForm"] { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); }
[data-baseweb="input"] > div, [data-baseweb="select"] > div, [data-baseweb="textarea"] { border-radius:10px; }
[data-testid="stAlert"] { border-radius:14px; }
[data-testid="stMetric"] { background:var(--paper); border:1px solid var(--line); border-radius:var(--radius); padding:.8rem 1rem; box-shadow:var(--shadow); }
</style>
"""

# ---------------------------------------------------------------------------
# Icons: small stroke icons (24x24) used inside HTML. Decorative: aria-hidden.
# ---------------------------------------------------------------------------
_PATHS = {
    "leaf": '<path d="M5 19c0-8 6-14 15-14 0 9-6 15-14 15"/><path d="M5 19 14 10"/>',
    "sprout": '<path d="M12 21v-9"/><path d="M12 12C12 8 9 6 5 6c0 4 3 6 7 6z"/><path d="M12 11c0-3 2.5-5 6-5 0 3.5-2.5 5-6 5z"/>',
    "seed": '<rect x="5" y="3" width="14" height="18" rx="2"/><path d="M9 7h6"/><path d="M12 18v-4"/><path d="M12 14c-2.2 0-3.3-1.2-3.3-3.2 2.2 0 3.3 1.2 3.3 3.2z"/>',
    "task": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "calendar": '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M3 10h18M8 3v4M16 3v4"/>',
    "spark": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
    "sun": '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    "cloud": '<path d="M7 18h10a4 4 0 0 0 .6-7.96A6 6 0 0 0 6.2 9.3 4.4 4.4 0 0 0 7 18z"/>',
    "rain": '<path d="M7 14h10a4 4 0 0 0 .6-7.96A6 6 0 0 0 6.2 5.3 4.4 4.4 0 0 0 7 14z"/><path d="M8 17l-1 3M12 17l-1 3M16 17l-1 3"/>',
    "partly": '<circle cx="8" cy="8" r="3"/><path d="M8 2v1.5M2 8h1.5M3.8 3.8l1 1M12.2 3.8l-1 1"/><path d="M9 20h8a3.5 3.5 0 0 0 .5-6.96A5 5 0 0 0 8.2 12.4 3.8 3.8 0 0 0 9 20z"/>',
    "thermo": '<path d="M14 14.8V5a2 2 0 0 0-4 0v9.8a4 4 0 1 0 4 0z"/><path d="M12 9v7"/>',
    "drop": '<path d="M12 3s6 6.4 6 11a6 6 0 0 1-12 0c0-4.6 6-11 6-11z"/>',
    "home": '<path d="M3 11.5 12 4l9 7.5"/><path d="M5.5 10v10h13V10"/><path d="M10 20v-5h4v5"/>',
    "bed": '<path d="M3 13h18v6H3z"/><path d="M7 13V9.5M12 13V7.5M17 13V9.5"/><path d="M12 7.5c-1.8 0-2.7-1-2.7-2.7 1.8 0 2.7 1 2.7 2.7zM12 7.5c1.8 0 2.7-1 2.7-2.7-1.8 0-2.7 1-2.7 2.7z"/>',
    "pot": '<path d="M5 11h14"/><path d="M6.5 11 8 20h8l1.5-9"/><path d="M12 11V6"/><path d="M12 7c-2.2 0-3.4-1.2-3.4-3.4C10.8 3.6 12 4.8 12 7zM12 8c2.2 0 3.4-1.2 3.4-3.4C13.2 4.6 12 5.8 12 8z"/>',
    "tray": '<path d="M3 15h18l-1.5 4h-15z"/><path d="M7 15v-3M10 15v-4M14 15v-4M17 15v-3"/>',
    "lamp": '<path d="M4 4h16"/><path d="M7 4 5 9h14l-2-5"/><path d="M8 12l-1 3M12 12v3.5M16 12l1 3"/>',
    "cover": '<path d="M3 12a9 9 0 0 1 18 0z"/><path d="M12 12v6a2 2 0 0 0 4 0"/>',
    "greenhouse": '<path d="M3 20v-9l9-7 9 7v9z"/><path d="M12 4v16M3 13.5h18"/>',
    "alert": '<path d="M12 4 2.5 20h19z"/><path d="M12 10v4.5M12 17.2v.1"/>',
    "book": '<path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v15H6.5A2.5 2.5 0 0 0 4 20.5z"/><path d="M4 20.5A2.5 2.5 0 0 0 6.5 23H20v-5"/>',
    "wind": '<path d="M3 8h10a3 3 0 1 0-3-3"/><path d="M3 12h15a3 3 0 1 1-3 3"/><path d="M3 16h7"/>',
    "ruler": '<path d="M4 17 17 4l3 3L7 20z"/><path d="m8 13 1.5 1.5M11 10l1.5 1.5M14 7l1.5 1.5"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="m8.5 12 2.5 2.5 4.5-5"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
}


def icon(name: str, size: int = 20, stroke: float = 1.7) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_PATHS.get(name, _PATHS["leaf"])}</svg>')


SETTING_ICON = {"indoor": "home", "outdoor": "bed", "greenhouse": "greenhouse", "covered": "cover"}
SETTING_LABEL = {"indoor": "Indoor", "outdoor": "Outdoor", "greenhouse": "Greenhouse", "covered": "Covered"}
METHOD_ICON = {"bed": "bed", "raised_bed": "bed", "container": "pot", "tray": "tray", "other": "leaf"}


def esc(value) -> str:
    return html.escape(str(value))


# ---------------------------------------------------------------------------
# Botanical illustrations: generic line art per category with crop accents.
# They are clearly illustrations, not photos of the user's plants.
# ---------------------------------------------------------------------------
_ACCENT = {"tomato": "#C8553D", "pepper": "#D9822B", "watermelon": "#3F7A4F", "basil": "#4E8B57",
           "carrot": "#D9822B", "beet": "#8E2D4A", "kale": "#3F6B4E", "spinach": "#3F7A4F",
           "lavender": "#8A79B8", "chamomile": "#E8C547", "wildflower_mix": "#C77452", "bean": "#7A6A4F",
           "pea": "#6E9E5A", "cucumber": "#4E8B57", "summer_squash": "#D8B13A", "onion": "#9DB07F",
           "cauliflower": "#E9E2CC", "rosemary": "#5B7F6A", "sage": "#8FA58E", "parsley": "#4E8B57",
           "microgreens": "#7DAA5C"}

_BG = ('<defs><linearGradient id="g{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#F3F1E6"/>'
       '<stop offset="1" stop-color="#E2E9DA"/></linearGradient></defs>'
       '<rect width="320" height="180" fill="url(#g{uid})"/>'
       '<circle cx="262" cy="34" r="58" fill="#FFFFFF" opacity=".35"/>'
       '<path d="M0 150 C 80 132, 160 160, 320 142 L320 180 L0 180 Z" fill="#D5DFCB" opacity=".7"/>')

_STEM = "#2F5E48"


def _leaf(x, y, angle, scale=1.0, fill="#7FA36E"):
    return (f'<g transform="translate({x} {y}) rotate({angle}) scale({scale})">'
            f'<path d="M0 0 C 10 -14, 32 -14, 42 0 C 32 14, 10 14, 0 0 Z" fill="{fill}" opacity=".92"/>'
            f'<path d="M2 0 H 38" stroke="{_STEM}" stroke-width="1" opacity=".5"/></g>')


def _art_vegetable(accent):
    return (f'<path d="M160 150 C 160 120, 158 95, 160 62" stroke="{_STEM}" stroke-width="3" fill="none"/>'
            + _leaf(160, 118, -150, 1.1) + _leaf(160, 104, -30, 1.15) + _leaf(160, 86, -140, .9) + _leaf(160, 76, -40, .85)
            + f'<circle cx="188" cy="128" r="17" fill="{accent}"/><circle cx="182" cy="122" r="5" fill="#fff" opacity=".35"/>'
            f'<circle cx="136" cy="134" r="12" fill="{accent}" opacity=".85"/>'
            f'<path d="M186 111 l3 -6 l3 6" stroke="{_STEM}" stroke-width="2" fill="none"/>')


def _art_herb(accent):
    leaves = "".join(_leaf(160, y, a, s, accent) for y, a, s in
                     ((128, -160, .9), (128, -20, .9), (108, -150, .8), (108, -30, .8), (90, -140, .7), (90, -40, .7), (74, -120, .55), (74, -60, .55)))
    return f'<path d="M160 152 V 62" stroke="{_STEM}" stroke-width="3"/>' + leaves


def _art_flower(accent):
    petals = "".join(f'<ellipse cx="160" cy="62" rx="9" ry="22" transform="rotate({a} 160 84)" fill="#FFFDF7" stroke="#E4DCC6"/>'
                     for a in range(0, 360, 36))
    return (f'<path d="M160 152 C 156 130, 164 110, 160 84" stroke="{_STEM}" stroke-width="3" fill="none"/>'
            + _leaf(158, 128, -160, .9) + _leaf(161, 116, -25, .8) + petals
            + f'<circle cx="160" cy="84" r="11" fill="{accent}"/>')


def _art_microgreen(accent):
    sprouts = "".join(
        f'<path d="M{x} 132 C {x} 118, {x + 2} 110, {x} 100" stroke="{_STEM}" stroke-width="2" fill="none"/>'
        f'<ellipse cx="{x - 6}" cy="99" rx="7" ry="4" fill="{accent}" transform="rotate(-20 {x - 6} 99)"/>'
        f'<ellipse cx="{x + 6}" cy="98" rx="7" ry="4" fill="{accent}" transform="rotate(20 {x + 6} 98)"/>'
        for x in range(104, 228, 18))
    return sprouts + '<rect x="88" y="130" width="144" height="18" rx="4" fill="#B98C66"/><rect x="88" y="130" width="144" height="5" fill="#A47753"/>'


def _art_seedling(accent):
    return (f'<path d="M160 150 V 100" stroke="{_STEM}" stroke-width="3"/>'
            + _leaf(160, 100, -150, 1.1, accent) + _leaf(160, 100, -30, 1.1, accent)
            + '<ellipse cx="160" cy="152" rx="40" ry="6" fill="#B98C66" opacity=".55"/>')


_ART = {"vegetable": _art_vegetable, "fruit": _art_vegetable, "herb": _art_herb, "flower": _art_flower,
        "microgreen": _art_microgreen}


_LEAFY = {"kale", "spinach", "onion", "cauliflower", "carrot", "beet", "pea", "bean"}


def _art_leafy(accent):
    leaves = "".join(_leaf(160, 146, a, s, accent) for a, s in ((-160, 1.0), (-135, 1.25), (-105, 1.35), (-75, 1.35), (-45, 1.25), (-20, 1.0)))
    return leaves + '<ellipse cx="160" cy="150" rx="46" ry="6" fill="#B98C66" opacity=".5"/>'


def illustration(category: str | None, crop_key: str | None = None, uid: str = "a", label: str = "") -> str:
    accent = _ACCENT.get(crop_key or "", TERRACOTTA if category in ("vegetable", "fruit") else "#7FA36E")
    if crop_key in _LEAFY:
        body = _art_leafy(accent if crop_key not in ("cauliflower", "carrot", "beet") else "#5E8C5A")
    else:
        body = _ART.get(category or "", _art_seedling)(accent)
    title = f"<title>Illustration: {esc(label)}</title>" if label else ""
    return (f'<div class="vd-art"><svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" role="img">'
            f'{title}{_BG.format(uid=esc(uid))}{body}</svg></div>')


def space_illustration(space, uid: str) -> str:
    """Scene for a growing space, chosen from its recorded setting, method and light."""
    sky = {"indoor": "#EDE6D6", "greenhouse": "#E3ECE0", "covered": "#EAE6DA", "outdoor": "#E6EEDF"}[space.setting]
    parts = [f'<rect width="320" height="180" fill="{sky}"/>']
    if space.setting == "outdoor":
        parts.append('<circle cx="262" cy="40" r="20" fill="#F2D27A" opacity=".85"/>')
    if space.setting == "greenhouse":
        parts.append('<path d="M60 150 V 80 L160 30 L260 80 V150" fill="#FFFFFF" opacity=".5" stroke="#9DB59A" stroke-width="2"/>'
                     '<path d="M160 30 V150 M60 110 H260" stroke="#9DB59A" stroke-width="2"/>')
    if space.setting == "covered":
        parts.append('<path d="M40 52 H280 L260 36 H60 Z" fill="#C77452" opacity=".75"/><path d="M60 52 V150 M260 52 V150" stroke="#8E6A4E" stroke-width="4"/>')
    if space.uses_grow_light:
        parts.append('<rect x="90" y="40" width="140" height="8" rx="4" fill="#3B4A42"/>'
                     '<path d="M100 48 L80 120 H240 L220 48 Z" fill="#F7E7A6" opacity=".45"/>')
    if space.growing_method in ("bed", "raised_bed"):
        parts.append('<rect x="60" y="122" width="200" height="30" rx="4" fill="#8E6A4E"/><rect x="60" y="118" width="200" height="8" rx="3" fill="#6B4F3A"/>')
        parts += [f'<path d="M{x} 120 V 102" stroke="{_STEM}" stroke-width="2.5"/>' + _leaf(x, 104, -150, .45) + _leaf(x, 104, -30, .45) for x in (90, 130, 170, 210, 240)]
    elif space.growing_method == "container":
        parts += [f'<path d="M{x - 22} 118 h44 l-6 34 h-32 z" fill="#C77452"/><path d="M{x} 118 V 92" stroke="{_STEM}" stroke-width="2.5"/>'
                  + _leaf(x, 98, -150, .6) + _leaf(x, 98, -30, .6) for x in (110, 210)]
    elif space.growing_method == "tray":
        parts.append('<rect x="70" y="128" width="180" height="16" rx="3" fill="#B98C66"/>')
        parts += [f'<path d="M{x} 128 V 114" stroke="{_STEM}" stroke-width="2"/><ellipse cx="{x - 5}" cy="113" rx="6" ry="3" fill="#7DAA5C"/><ellipse cx="{x + 5}" cy="112" rx="6" ry="3" fill="#7DAA5C"/>' for x in range(84, 244, 16)]
    else:
        parts.append(f'<path d="M160 150 V 100" stroke="{_STEM}" stroke-width="3"/>' + _leaf(160, 104, -150, .9) + _leaf(160, 104, -30, .9))
    parts.append('<rect y="150" width="320" height="30" fill="#D5DFCB" opacity=".8"/>')
    return (f'<div class="vd-art"><svg viewBox="0 0 320 180" preserveAspectRatio="xMidYMid slice" role="img">'
            f'<title>Illustration of {esc(space.name)}</title>{"".join(parts)}</svg></div>')


# ---------------------------------------------------------------------------
# HTML components
# ---------------------------------------------------------------------------
def page_header(eyebrow: str, title: str, lede: str = "") -> str:
    return (f'<div class="vd-eyebrow">{esc(eyebrow)}</div><div class="vd-h1">{esc(title)}</div>'
            + (f'<div class="vd-lede">{esc(lede)}</div>' if lede else ""))


def section(title: str, icon_name: str | None = None, sub: str = "") -> str:
    ico = f'<span class="vd-inline" style="color:var(--terracotta)">{icon(icon_name, 22)}</span>' if icon_name else ""
    return f'<div class="vd-h2">{ico}{esc(title)}</div>' + (f'<div class="vd-sub">{esc(sub)}</div>' if sub else "")


def metric(value, label: str, icon_name: str, note: str = "", tone: str = "") -> str:
    note_html = f'<div class="vd-note">{esc(note)}</div>' if note else ""
    return (f'<div class="vd-metric {tone}"><div class="vd-ico">{icon(icon_name, 22)}</div>'
            f'<div><div class="vd-num">{esc(value)}</div><div class="vd-lbl">{esc(label)}</div>{note_html}</div></div>')


def chip(text: str, tone: str = "", icon_name: str | None = None) -> str:
    ico = icon(icon_name, 14, 2) if icon_name else ""
    return f'<span class="vd-chip {tone}">{ico}{esc(text)}</span>'


def empty_state(title: str, body: str, icon_name: str = "sprout") -> str:
    return (f'<div class="vd-empty"><div class="vd-ico">{icon(icon_name, 24)}</div>'
            f'<div><b>{esc(title)}</b>{esc(body)}</div></div>')


def stage_bar(stage: str, stages: tuple) -> str:
    index = stages.index(stage)
    bars = "".join(f'<i class="{"on" if i <= index else ""}"></i>' for i in range(1, len(stages)))
    return f'<div class="vd-stages" aria-hidden="true">{bars}</div>'


def table(rows: list[dict]) -> str:
    if not rows:
        return ""
    head = "".join(f"<th>{esc(k)}</th>" for k in rows[0])
    body = "".join("<tr>" + "".join(f"<td>{esc(v)}</td>" for v in row.values()) + "</tr>" for row in rows)
    return f'<table class="vd-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def weather_icon(snap) -> tuple[str, str]:
    """Pick an icon from the provider's own numbers (rain chance, rain amount, sunshine hours)."""
    rain = (snap.precipitation_probability or 0) >= 50 or (snap.precipitation_amount or 0) >= 0.1
    if rain:
        return "rain", "Rain likely"
    if snap.sunshine_duration is None:
        return "thermo", "Temperature"
    if snap.sunshine_duration >= 7:
        return "sun", "Mostly sunny"
    if snap.sunshine_duration >= 3:
        return "partly", "Some sun"
    return "cloud", "Mostly cloudy"


def weather_strip(snapshots, today, frost_watch_f: float) -> str:
    cards = []
    for s in snapshots:
        name, words = weather_icon(s)
        low_f = None if s.min_temperature is None else (s.min_temperature if s.units == "imperial" else s.min_temperature * 9 / 5 + 32)
        frost = '<div class="fr">Near frost</div>' if low_f is not None and low_f <= frost_watch_f else ""
        hi = "—" if s.temperature is None else f"{s.temperature:.0f}°"
        lo = "—" if s.min_temperature is None else f"{s.min_temperature:.0f}°"
        rain = "" if s.precipitation_probability is None else f'<div class="rn">{s.precipitation_probability:.0f}% rain</div>'
        label = "Today" if s.forecast_for == today else f"{s.forecast_for:%a}"
        cards.append(f'<div class="vd-day{" today" if s.forecast_for == today else ""}" title="{esc(words)}">'
                     f'<div class="d">{label}</div><div class="ic">{icon(name, 30, 1.5)}</div>'
                     f'<div class="hi">{hi}</div><div class="lo">low {lo}</div>{rain}{frost}</div>')
    return f'<div class="vd-weather" role="list">{"".join(cards)}</div>'


def logo(size: int = 34) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 40 40" aria-hidden="true">'
            '<circle cx="20" cy="20" r="19" fill="#F8F5EC" opacity=".12"/>'
            '<path d="M20 31V17" stroke="#F8F5EC" stroke-width="2" stroke-linecap="round"/>'
            '<path d="M20 19c0-5-3.5-8-9-8 0 5.5 3.5 8 9 8z" fill="#A8B99D"/>'
            '<path d="M20 17c0-4.5 3-7.5 8.5-7.5 0 5-3 7.5-8.5 7.5z" fill="#C9A464"/></svg>')
