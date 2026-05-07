import streamlit as st
import base64, csv, io, json, html, os, re
from pathlib import Path
from graph import app as pipeline_app
from demo_output import DEMO_INVOKE_RESULT
from apt import get_apt_techniques, get_group_info
from agents.llm import has_live_llm_config, live_health
from topology import generate_attack_paths, generate_topology, score_path_detection
from export import generate_pdf

PIPELINE_VERSION = "aegisops-ui-v2"
ASSETS_DIR = Path(__file__).parent / "assets"

TECHNIQUE_CATALOG = [
    ("T1059.001", "PowerShell"),
    ("T1566.001", "Spearphishing Attachment"),
    ("T1078",     "Valid Accounts"),
    ("T1003",     "OS Credential Dumping"),
    ("T1055",     "Process Injection"),
    ("T1110",     "Brute Force"),
    ("T1486",     "Data Encrypted for Impact"),
    ("T1218",     "System Binary Proxy Execution"),
    ("T1027",     "Obfuscated Files or Information"),
    ("T1136",     "Create Account"),
]

st.set_page_config(
    page_title="AegisOps AI",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg:       #020617;
  --bg-card:  #0E1223;
  --bg-input: #0F172A;
  --bg-muted: #1A1E2F;
  --border:   #1E293B;
  --border-hi:#334155;
  --fg:       #F8FAFC;
  --fg-muted: #94A3B8;
  --fg-dim:   #64748B;
  --red:      #EF4444;
  --blue:     #3B82F6;
  --green:    #22C55E;
  --amber:    #F59E0B;
  --purple:   #8B5CF6;
}

.stApp { background: var(--bg) !important; font-family: 'Inter', sans-serif !important; }
#MainMenu, footer, header { visibility: hidden !important; }
.stDeployButton { display: none !important; }
* { box-sizing: border-box; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border-hi); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--fg-dim); }

[data-testid="stSidebar"] {
  background: #060C18 !important;
  border-right: 1px solid #334155 !important;
}
[data-testid="stSidebar"] > div:first-child { padding: 18px 14px !important; }
[data-testid="stSidebar"] p { color: var(--fg-muted) !important; font-size: 13px !important; margin: 0 !important; }

[data-testid="stRadio"] > label { display: none !important; }
[data-testid="stRadio"] > div { flex-direction: column !important; gap: 3px !important; }
[data-testid="stRadio"] > div > label {
  background: transparent !important;
  border: 1px solid transparent !important;
  border-radius: 6px !important;
  padding: 9px 10px 9px 10px !important;
  cursor: pointer !important;
  color: var(--fg-muted) !important;
  font-size: 13px !important;
  font-weight: 500 !important;
}
[data-testid="stRadio"] > div > label:hover {
  background: var(--bg-input) !important;
  border-color: var(--border-hi) !important;
  color: var(--fg) !important;
}
[data-testid="stRadio"] > div > label[aria-checked="true"],
[data-testid="stRadio"] > div > label:has(input:checked) {
  background: rgba(139,92,246,0.12) !important;
  border-color: rgba(139,92,246,0.4) !important;
  color: #C4B5FD !important;
}

.stTextInput > div > div > input {
  background: var(--bg-input) !important;
  border: 1px solid var(--border-hi) !important;
  border-radius: 6px !important;
  color: var(--fg) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px !important;
  padding: 9px 12px !important;
}
.stTextInput > div > div > input:focus {
  border-color: var(--purple) !important;
  box-shadow: 0 0 0 2px rgba(139,92,246,0.2) !important;
  outline: none !important;
}
.stTextInput > div > div > input::placeholder { color: var(--fg-dim) !important; }
.stTextInput > label {
  color: var(--fg-dim) !important;
  font-size: 9px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
}

.stSelectbox > label {
  color: var(--fg-dim) !important;
  font-size: 9px !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.1em !important;
}
[data-baseweb="select"] > div {
  background: var(--bg-input) !important;
  border: 1px solid var(--border-hi) !important;
  border-radius: 6px !important;
  color: var(--fg) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 13px !important;
}

.stButton > button {
  background: linear-gradient(135deg, #7C3AED 0%, #4F46E5 100%) !important;
  border: 1px solid rgba(139,92,246,0.5) !important;
  border-radius: 6px !important;
  color: #fff !important;
  font-family: 'Inter', sans-serif !important;
  font-weight: 700 !important;
  font-size: 11px !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  padding: 10px 22px !important;
  box-shadow: 0 4px 14px rgba(139,92,246,0.3) !important;
  transition: all 0.2s ease !important;
}
.stButton > button:hover {
  background: linear-gradient(135deg, #8B5CF6 0%, #6366F1 100%) !important;
  box-shadow: 0 4px 18px rgba(139,92,246,0.45) !important;
  transform: translateY(-1px) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

.stDownloadButton > button {
  background: transparent !important;
  border: 1px solid var(--border-hi) !important;
  color: var(--fg-muted) !important;
  font-size: 11px !important;
  font-family: 'Inter', sans-serif !important;
  border-radius: 6px !important;
  padding: 8px 18px !important;
  text-transform: uppercase !important;
  letter-spacing: 0.07em !important;
  font-weight: 600 !important;
}
.stDownloadButton > button:hover {
  border-color: var(--green) !important;
  color: var(--green) !important;
  background: rgba(34,197,94,0.08) !important;
}

.stToggle label { color: var(--fg-muted) !important; font-size: 11px !important; font-family: 'Inter', sans-serif !important; }
.stProgress > div > div > div > div {
  background: linear-gradient(90deg, var(--purple), var(--blue)) !important;
}
.stProgress > div > div > div { background: var(--bg-input) !important; }

[data-testid="stExpander"] {
  border: 1px solid var(--border-hi) !important;
  border-radius: 6px !important;
  background: var(--bg-card) !important;
  margin-bottom: 6px !important;
}
[data-testid="stExpander"] summary {
  background: var(--bg-card) !important;
  color: var(--fg-muted) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 12px !important;
  padding: 10px 14px !important;
}
[data-testid="stExpander"] > div:last-child {
  background: var(--bg-card) !important;
  border-top: 1px solid var(--border) !important;
  padding: 14px !important;
}

[data-testid="stCode"] { background: #000810 !important; border: 1px solid var(--border-hi) !important; border-radius: 6px !important; }
pre code { font-family: 'JetBrains Mono', monospace !important; font-size: 11px !important; }

.stMarkdown p { color: var(--fg-muted) !important; font-size: 13px !important; line-height: 1.7 !important; }
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 { color: var(--fg) !important; }
.stMarkdown strong { color: var(--fg) !important; }
.stMarkdown code {
  background: var(--bg-muted) !important; color: #C4B5FD !important;
  font-family: 'JetBrains Mono', monospace !important; border-radius: 3px;
  padding: 2px 6px; font-size: 12px;
}
.stMarkdown ul, .stMarkdown ol { color: var(--fg-muted) !important; }
.stMarkdown li { font-size: 13px !important; line-height: 1.7 !important; }

hr { border-color: var(--border-hi) !important; margin: 16px 0 !important; }
.block-container { padding-top: 1.5rem !important; max-width: 98% !important; }

@keyframes blink-dot { 0%,100%{opacity:1} 50%{opacity:0.25} }
</style>""", unsafe_allow_html=True)


# ── HTML helpers ───────────────────────────────────────────────────────────────

def _badge(tid: str, name: str = "") -> str:
    label = tid + (f"&nbsp;·&nbsp;{name[:24]}{'…' if len(name)>24 else ''}" if name else "")
    return (
        f'<span style="display:inline-block;background:rgba(139,92,246,.12);'
        f'border:1px solid rgba(139,92,246,.35);color:#C4B5FD;font-family:JetBrains Mono,monospace;'
        f'font-size:11px;font-weight:600;padding:3px 10px;border-radius:4px;letter-spacing:.04em;'
        f'white-space:nowrap">{label}</span>'
    )


def _metric_row(metrics: list) -> str:
    cards = ""
    for val, label, color in metrics:
        cards += (
            f'<div style="flex:1;background:#0E1223;border:1px solid #334155;'
            f'border-radius:8px;padding:12px 14px;text-align:center">'
            f'<div style="font-family:JetBrains Mono,monospace;font-size:22px;font-weight:700;'
            f'color:{color};line-height:1">{val}</div>'
            f'<div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
            f'color:#475569;margin-top:4px">{label}</div></div>'
        )
    return f'<div style="display:flex;gap:10px;margin-bottom:14px;flex-wrap:wrap">{cards}</div>'


def _pdf_download_link(label: str, pdf_bytes: bytes, file_name: str) -> str:
    payload = base64.b64encode(pdf_bytes).decode("ascii")
    safe_label = html.escape(label)
    return (
        f'<a href="data:application/pdf;base64,{payload}" download="{html.escape(file_name, quote=True)}" '
        'style="display:inline-flex;align-items:center;justify-content:center;'
        'background:transparent;border:1px solid #334155;color:#94A3B8;'
        'font-size:11px;font-family:Inter,sans-serif;border-radius:6px;'
        'padding:9px 18px;text-transform:uppercase;letter-spacing:.07em;'
        'font-weight:600;text-decoration:none;cursor:pointer">'
        f'{safe_label}</a>'
    )


def _section_header(title: str, eyebrow: str, accent: str = "#8B5CF6") -> str:
    return (
        '<div style="display:flex;align-items:flex-end;justify-content:space-between;'
        'gap:12px;margin:20px 0 12px;flex-wrap:wrap">'
        '<div>'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
        f'color:{accent};font-family:Inter,sans-serif;margin-bottom:4px">{eyebrow}</div>'
        f'<div style="font-family:Inter,sans-serif;font-size:16px;font-weight:700;'
        f'color:#F8FAFC;letter-spacing:-.01em">{title}</div>'
        '</div></div>'
    )


def _artifact_card(title: str, subtitle: str, accent: str, body: str = "") -> str:
    return (
        f'<div style="background:#0E1223;border:1px solid #334155;border-top:2px solid {accent};'
        'border-radius:8px;padding:14px;margin-bottom:12px">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'color:{accent};font-family:Inter,sans-serif;margin-bottom:5px">{title}</div>'
        f'<p style="font-size:11px;color:#94A3B8;line-height:1.55;margin:0 0 10px;'
        f'font-family:Inter,sans-serif">{subtitle}</p>'
        f'{body}</div>'
    )


def _pill_list(items: list, accent: str, empty_label: str = "—") -> str:
    if not items:
        return f'<span style="color:#64748B;font-size:12px">{empty_label}</span>'
    return "".join(
        f'<span style="display:inline-block;background:rgba(245,158,11,.08);border:1px solid {accent};'
        f'color:#FCD34D;font-family:JetBrains Mono,monospace;font-size:10px;padding:3px 7px;'
        f'border-radius:3px;margin:2px 3px 2px 0">{html.escape(str(item))}</span>'
        for item in items[:8]
    )


def _extract_fenced(text: str, lang: str) -> str:
    m = re.search(rf"```{lang}\s*(.*?)\s*```", text or "", re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_red_json(red: str) -> dict:
    payload = _extract_fenced(red, "json")
    try:
        return json.loads(payload) if payload else {}
    except json.JSONDecodeError:
        return {}


def _extract_section(text: str, heading: str) -> str:
    m = re.search(rf"##\s+{re.escape(heading)}\s*(.*?)(?=\n##\s+|\Z)", text or "", re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""


def _extract_bullets(text: str, limit: int = 5) -> list:
    bullets = []
    for line in text.splitlines():
        cleaned = re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", line).strip()
        if cleaned and cleaned != line.strip():
            bullets.append(cleaned)
    return bullets[:limit]


def _sigma_title(yaml_text: str) -> str:
    m = re.search(r"^title:\s*(.+)$", yaml_text or "", re.MULTILINE)
    return m.group(1).strip() if m else "Sigma-style detection"


def _short_model(model: str) -> str:
    return model.rsplit("/", 1)[-1] if model else "unknown"


def _load_asset_json(name: str) -> dict:
    p = ASSETS_DIR / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


# ── ROCm / AMD provenance panel ────────────────────────────────────────────────

def _rocm_panel_html(demo_mode: bool, health: dict) -> str:
    benchmark = _load_asset_json("rocm_benchmark.json")
    smi = _load_asset_json("rocm_smi.json")
    smi_ok = bool(smi) and "note" not in smi
    bench_p50 = benchmark.get("latency_ms_p50") or benchmark.get("p50_ms")
    bench_p95 = benchmark.get("latency_ms_p95") or benchmark.get("p95_ms")
    bench_tps = benchmark.get("tokens_per_second") or benchmark.get("tps")

    meta_items = []
    if not demo_mode and health.get("reachable"):
        meta_items.append(f'<span style="color:#475569">/v1/models latency:</span> {health.get("latency_ms")} ms')
    meta_items.append('<span style="color:#475569">runtime:</span> vLLM · ROCm container · MI300X')
    if smi_ok:
        meta_items.append('<span style="color:#475569">rocm-smi.json</span> <span style="color:#86EFAC">captured</span>')
    if benchmark:
        meta_items.append('<span style="color:#475569">rocm_benchmark.json</span>')
    meta_html = "".join(
        f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#94A3B8">{m}</span>'
        for m in meta_items
    )
    meta_row = f'<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:6px">{meta_html}</div>' if meta_items else ""

    bench_row = ""
    if any(v is not None for v in (bench_p50, bench_p95, bench_tps)):
        parts = []
        if bench_p50 is not None: parts.append(f'<span style="color:#475569">p50:</span> {bench_p50} ms')
        if bench_p95 is not None: parts.append(f'<span style="color:#475569">p95:</span> {bench_p95} ms')
        if bench_tps is not None: parts.append(f'<span style="color:#475569">throughput:</span> {bench_tps} tok/s')
        bench_row = (
            '<div style="display:flex;gap:14px;flex-wrap:wrap;margin-top:6px">'
            + "".join(f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#94A3B8">{p}</span>' for p in parts)
            + "</div>"
        )

    if demo_mode:
        accent, accent_bg, accent_bd = "#F59E0B", "rgba(245,158,11,.06)", "rgba(245,158,11,.25)"
        dot_color, pill_label = "#F59E0B", "DEMO"
        title = "DEMO MODE · AMD MI300X provenance preserved"
        body = (
            '<p style="font-size:11px;color:#FCD34D;margin:0 0 4px;line-height:1.5;font-family:Inter,sans-serif">'
            'Public Space runs precomputed artifacts for reliable judging. Bundled evidence below is captured from AMD Developer Cloud MI300X.'
            '</p>'
        )
    elif health.get("reachable"):
        accent, accent_bg, accent_bd = "#22C55E", "rgba(34,197,94,.06)", "rgba(34,197,94,.25)"
        dot_color, pill_label = "#22C55E", "LIVE"
        model = _short_model(str(health.get("model") or os.getenv("MODEL_NAME") or ""))
        title = f"LIVE · vLLM on ROCm · MI300X · {html.escape(model)}"
        body = (
            '<p style="font-size:11px;color:#86EFAC;margin:0 0 4px;line-height:1.5;font-family:Inter,sans-serif">'
            'Health probe confirmed the OpenAI-compatible vLLM endpoint is reachable. Each agent in the pipeline executes against this AMD MI300X / ROCm endpoint.'
            '</p>'
        )
    else:
        accent, accent_bg, accent_bd = "#EF4444", "rgba(239,68,68,.06)", "rgba(239,68,68,.25)"
        dot_color, pill_label = "#EF4444", "OFFLINE"
        err = html.escape(str(health.get("error") or "unreachable"))
        title = "LIVE ENDPOINT NOT REACHABLE"
        body = (
            f'<p style="font-size:11px;color:#FCA5A5;margin:0 0 4px;line-height:1.5;font-family:Inter,sans-serif">'
            f'Configured vLLM endpoint did not respond ({err}). Toggle Demo Mode or run ./start_vllm.sh.</p>'
        )

    return (
        f'<div style="background:{accent_bg};border:1px solid {accent_bd};'
        f'border-left:3px solid {accent};border-radius:8px;padding:12px 16px;margin-bottom:14px">'
        '<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:6px">'
        '<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:{dot_color};box-shadow:0 0 6px {dot_color}"></span>'
        f'<span style="font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:{accent};font-family:Inter,sans-serif">{title}</span>'
        '</div>'
        f'<span style="background:{accent};color:#0B1220;font-family:JetBrains Mono,monospace;font-size:9px;font-weight:700;padding:2px 8px;border-radius:4px">{pill_label}</span>'
        '</div>'
        f'{body}{meta_row}{bench_row}'
        '</div>'
    )


def _status_bar_html(demo_mode: bool, mode: str) -> str:
    if demo_mode:
        live_span = '<span style="color:#F59E0B;font-size:11px;font-family:JetBrains Mono,monospace">● DEMO MODE</span>'
    else:
        live_span = (
            '<span style="display:inline-flex;align-items:center;gap:5px;color:#22C55E;'
            'font-size:11px;font-family:JetBrains Mono,monospace">'
            '<span style="width:6px;height:6px;border-radius:50%;background:#22C55E;'
            'animation:blink-dot 2s infinite;display:inline-block"></span>'
            'LIVE ENDPOINT — AMD/ROCm READY</span>'
        )
    sep = '<span style="color:#1E293B;font-size:14px">|</span>'
    return (
        '<div style="display:flex;align-items:center;gap:14px;padding:8px 14px;'
        'background:#0E1223;border:1px solid #1E293B;border-radius:6px;margin-bottom:14px;flex-wrap:wrap">'
        f'{live_span}{sep}'
        '<span style="font-size:11px;font-family:JetBrains Mono,monospace;color:#475569">MITRE ATT&amp;CK v14</span>'
        f'{sep}'
        '<span style="font-size:11px;font-family:JetBrains Mono,monospace;color:#475569">Threat · Detection · Response · Validation</span>'
        f'{sep}'
        f'<span style="font-size:11px;font-family:JetBrains Mono,monospace;color:#475569">MODE: {html.escape(mode.upper())}</span>'
        '</div>'
    )


def _page_header_html(mode: str, demo_mode: bool = False) -> str:
    cfg = {
        "Single Technique": (
            "TECHNIQUE ANALYSIS", "#8B5CF6", "139,92,246",
            "Advanced known ATT&CK simulation that turns attacker behavior into realtime detections"
        ),
        "APT Group": (
            "THREAT ACTOR SIM", "#F59E0B", "245,158,11",
            "Defensive simulation across techniques attributed to a threat actor"
        ),
        "Kill Chain": (
            "KILL CHAIN SIM", "#22C55E", "34,197,94",
            "Stage-by-stage defensive analysis for expected attacker behavior"
        ),
        "Topology Lab": (
            "TOPOLOGY LAB", "#06B6D4", "6,182,212",
            "Sandbox lateral-movement simulation with realtime detection response"
        ),
    }
    badge, color, rgb, subtitle = cfg.get(mode, ("", "#8B5CF6", "139,92,246", ""))
    if demo_mode and mode == "Single Technique":
        color, rgb = "#F59E0B", "245,158,11"
    return (
        '<div style="margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #1E293B">'
        '<div style="display:flex;align-items:flex-end;justify-content:space-between;flex-wrap:wrap;gap:12px">'
        '<div>'
        '<h1 style="font-family:Inter,sans-serif;font-size:22px;font-weight:800;color:#F8FAFC;'
        'margin:0 0 4px;letter-spacing:-.02em">AegisOps AI</h1>'
        f'<p style="font-size:12px;color:#64748B;margin:0;font-family:Inter,sans-serif">{subtitle}</p>'
        '</div>'
        f'<div style="display:inline-flex;align-items:center;gap:6px;background:rgba({rgb},.1);'
        f'border:1px solid rgba({rgb},.3);border-radius:20px;padding:5px 12px;'
        f'font-size:10px;font-weight:700;color:{color};text-transform:uppercase;letter-spacing:.1em;font-family:Inter,sans-serif">'
        f'<span style="width:5px;height:5px;border-radius:50%;background:{color};box-shadow:0 0 6px {color};'
        f'animation:blink-dot 2s infinite;display:inline-block"></span>{badge}</div>'
        '</div></div>'
    )


# ── Pipeline metrics panel ─────────────────────────────────────────────────────

def _agent_card_html(m: dict) -> str:
    LABELS = {
        "red_agent":      ("Red / Threat",     "#EF4444"),
        "blue_agent":     ("Detection",         "#3B82F6"),
        "response_agent": ("Response",          "#22C55E"),
        "verifier_agent": ("Validation",        "#8B5CF6"),
    }
    label, color = LABELS.get(m.get("agent", ""), (m.get("agent", "agent"), "#8B5CF6"))
    return (
        f'<div style="flex:1;min-width:150px;background:#0E1223;border:1px solid #334155;'
        f'border-top:2px solid {color};border-radius:6px;padding:9px 11px">'
        f'<div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        f'color:{color};font-family:Inter,sans-serif;margin-bottom:5px">{label}</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:14px;font-weight:700;color:#F8FAFC">'
        f'{m.get("latency_ms", 0)} ms</div>'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#64748B;margin-top:3px">'
        f'in {m.get("prompt_tokens", 0)} · out {m.get("completion_tokens", 0)}</div>'
        '</div>'
    )


def _pipeline_metrics_html(metrics: dict, demo_mode: bool = False) -> str:
    if not metrics:
        return ""
    agents = metrics.get("agents") or []
    if not agents:
        return ""
    cards = "".join(_agent_card_html(m) for m in agents)
    total_latency = metrics.get("total_latency_ms", 0)
    total_tokens = metrics.get("total_tokens", 0)
    model = _short_model(str(metrics.get("model") or ""))
    head_color = "#F59E0B" if demo_mode else "#8B5CF6"
    head_label = "BUNDLED EVIDENCE · CAPTURED FROM AMD MI300X" if demo_mode else "AMD MI300X · vLLM · ROCm — per-agent inference metrics"
    summary = (
        '<div style="display:flex;gap:14px;flex-wrap:wrap;font-family:JetBrains Mono,monospace;'
        'font-size:10px;color:#94A3B8;margin-bottom:10px">'
        f'<span><span style="color:#475569">total latency:</span> {total_latency} ms</span>'
        f'<span><span style="color:#475569">total tokens:</span> {total_tokens}</span>'
        f'<span><span style="color:#475569">model:</span> {html.escape(model)}</span>'
        '<span><span style="color:#475569">runtime:</span> <span style="color:#86EFAC">vLLM · ROCm · MI300X</span></span>'
        '</div>'
    )
    return (
        f'<div style="background:#0B1220;border:1px solid #1E293B;border-radius:8px;padding:12px 14px;margin-bottom:14px">'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'color:{head_color};font-family:Inter,sans-serif;margin-bottom:10px">{head_label}</div>'
        f'{summary}<div style="display:flex;gap:8px;flex-wrap:wrap">{cards}</div>'
        '</div>'
    )


# ── Agent output rendering ─────────────────────────────────────────────────────

def _panel_head(side: str, label: str, badge_tid: str = "", precomputed: bool = False) -> str:
    COLOR_MAP = {
        "red":    ("#EF4444", "239,68,68"),
        "blue":   ("#3B82F6", "59,130,246"),
        "green":  ("#22C55E", "34,197,94"),
        "purple": ("#8B5CF6", "139,92,246"),
        "amber":  ("#F59E0B", "245,158,11"),
    }
    color, rgb = COLOR_MAP.get(side, ("#8B5CF6", "139,92,246"))
    tag = "— PRECOMPUTED" if precomputed else ""
    badge = f"&nbsp;&nbsp;{_badge(badge_tid)}" if badge_tid else ""
    return (
        f'<div style="background:rgba({rgb},.06);border:1px solid rgba({rgb},.2);'
        f'border-top:2px solid {color};border-radius:8px 8px 0 0;padding:10px 14px;'
        'display:flex;align-items:center;justify-content:space-between">'
        f'<div style="display:flex;align-items:center;gap:8px">'
        f'<span style="width:7px;height:7px;border-radius:50%;background:{color};'
        f'box-shadow:0 0 6px {color};display:inline-block"></span>'
        f'<span style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
        f'color:{color};font-family:Inter,sans-serif">{html.escape(label)} {tag}</span></div>'
        f'{badge}</div>'
    )


def _verifier_html(verifier_output: str) -> str:
    try:
        m = re.search(r'```json\s*(.*?)\s*```', verifier_output, re.DOTALL)
        data = json.loads(m.group(1) if m else verifier_output)
        score = data.get("coverage_score", 0)
        verdict = data.get("verdict", "UNKNOWN")
        safety = data.get("safety_verdict", "PASS")
        covered = data.get("covered_observables", [])
        missing = data.get("missing_observables", [])
        suggestions = data.get("improvement_suggestions", [])

        v_color = "#22C55E" if verdict == "PASS" else "#EF4444"
        v_bg = f"rgba({'34,197,94' if verdict=='PASS' else '239,68,68'},.1)"
        v_bd = f"rgba({'34,197,94' if verdict=='PASS' else '239,68,68'},.3)"
        s_color = "#22C55E" if safety == "PASS" else "#EF4444"
        s_bg = f"rgba({'34,197,94' if safety=='PASS' else '239,68,68'},.1)"
        s_bd = f"rgba({'34,197,94' if safety=='PASS' else '239,68,68'},.3)"
        sc_color = "#22C55E" if score >= 80 else "#F59E0B" if score >= 60 else "#EF4444"

        cov_html = "".join(
            f'<span style="display:inline-block;background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);'
            f'color:#86EFAC;font-family:JetBrains Mono,monospace;font-size:11px;padding:2px 8px;'
            f'border-radius:4px;margin:2px">{o}</span>' for o in covered
        ) or '<span style="color:#475569;font-size:12px">None detected</span>'

        mis_html = "".join(
            f'<span style="display:inline-block;background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);'
            f'color:#FCA5A5;font-family:JetBrains Mono,monospace;font-size:11px;padding:2px 8px;'
            f'border-radius:4px;margin:2px">{o}</span>' for o in missing
        ) if missing else '<span style="color:#22C55E;font-size:12px">All observables covered ✓</span>'

        sug_html = "".join(
            f'<li style="color:#94A3B8;font-size:12px;margin-bottom:4px">{s}</li>'
            for s in suggestions
        )

        return (
            '<div style="background:#0E1223;border:1px solid #334155;border-top:2px solid #8B5CF6;'
            'border-radius:8px;padding:16px;margin-top:14px">'
            '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:14px;flex-wrap:wrap;gap:10px">'
            '<div style="display:flex;align-items:center;gap:8px">'
            '<span style="width:7px;height:7px;border-radius:50%;background:#8B5CF6;box-shadow:0 0 6px #8B5CF6;display:inline-block"></span>'
            '<span style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#8B5CF6;font-family:Inter,sans-serif">VALIDATOR AGENT — QUALITY CHECK</span>'
            '</div>'
            '<div style="display:flex;gap:8px;align-items:center">'
            f'<div style="background:{s_bg};border:1px solid {s_bd};border-radius:4px;padding:4px 10px;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:{s_color}">SCOPE {safety}</div>'
            f'<div style="background:{v_bg};border:1px solid {v_bd};border-radius:4px;padding:4px 10px;font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:{v_color}">{verdict}</div>'
            f'<div style="background:#0F172A;border:1px solid #334155;border-radius:4px;padding:4px 12px;font-family:JetBrains Mono,monospace;font-size:18px;font-weight:700;color:{sc_color}">{score}%</div>'
            '</div></div>'
            '<div style="display:grid;grid-template-columns:1fr 1fr;gap:14px">'
            '<div><div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin-bottom:8px;font-family:Inter,sans-serif">COVERED OBSERVABLES</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px">{cov_html}</div></div>'
            '<div><div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin-bottom:8px;font-family:Inter,sans-serif">MISSING OBSERVABLES</div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:4px">{mis_html}</div></div></div>'
            + (f'<div style="margin-top:12px"><div style="font-size:9px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#475569;margin-bottom:8px;font-family:Inter,sans-serif">IMPROVEMENT SUGGESTIONS</div><ul style="margin:0;padding-left:16px">{sug_html}</ul></div>' if sug_html else "")
            + '</div>'
        )
    except Exception:
        return (
            '<div style="background:#0E1223;border:1px solid #334155;border-top:2px solid #8B5CF6;'
            'border-radius:8px;padding:14px;margin-top:14px">'
            '<span style="font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#8B5CF6;font-family:Inter,sans-serif">VALIDATOR AGENT OUTPUT</span>'
            f'<pre style="color:#94A3B8;font-size:12px;margin-top:8px;white-space:pre-wrap">{html.escape(verifier_output or "")}</pre>'
            '</div>'
        )


def _render_operational_outputs(red: str, blue: str):
    red_json = _extract_red_json(red)
    observables = red_json.get("observables", [])
    sigma = _extract_fenced(blue, "yaml")
    response_items = _extract_bullets(_extract_section(blue, "Response Guidance") or _extract_section(blue, "Recommendations"), limit=5)
    realtime_items = _extract_bullets(_extract_section(blue, "Real-Time Detection Plan"), limit=6)

    col_obs, col_resp, col_rt = st.columns(3, gap="small")
    obs_pills = _pill_list(observables, "rgba(245,158,11,.35)", "No observables extracted")
    with col_obs:
        st.markdown(
            _artifact_card("OBSERVABLES", "Telemetry indicators for SIEM, EDR, and endpoint logs.", "#F59E0B", obs_pills),
            unsafe_allow_html=True,
        )
    with col_resp:
        body = "<ul style='margin:0;padding-left:14px;list-style:none'>" + "".join(
            f'<li style="font-size:11px;color:#CBD5E1;line-height:1.55;margin-bottom:4px;position:relative;padding-left:14px">'
            f'<span style="position:absolute;left:0;color:#22C55E;font-family:JetBrains Mono,monospace">→</span>'
            f'{html.escape(item)}</li>'
            for item in response_items
        ) + "</ul>" if response_items else '<span style="color:#64748B;font-size:12px">No response steps extracted</span>'
        st.markdown(
            _artifact_card("RESPONSE GUIDANCE", "Immediate analyst actions for triage, hardening, and escalation.", "#22C55E", body),
            unsafe_allow_html=True,
        )
    with col_rt:
        rt_body = "<ul style='margin:0;padding-left:14px;list-style:none'>" + "".join(
            f'<li style="font-size:11px;color:#CBD5E1;line-height:1.55;margin-bottom:4px;position:relative;padding-left:14px">'
            f'<span style="position:absolute;left:0;color:#22C55E;font-family:JetBrains Mono,monospace">→</span>'
            f'{html.escape(item)}</li>'
            for item in realtime_items
        ) + "</ul>" if realtime_items else '<span style="color:#64748B;font-size:12px">No realtime detection logic extracted</span>'
        st.markdown(
            _artifact_card("REAL-TIME DETECTION", "Streaming SIEM/EDR alert logic generated from simulated behavior.", "#8B5CF6", rt_body),
            unsafe_allow_html=True,
        )


def display_agent_panels(red: str, blue: str, verifier: str | None, tid: str, demo_mode: bool = False):
    col_red, col_blue = st.columns(2, gap="small")
    with col_red:
        st.markdown(_panel_head("red", "RED/THREAT AGENT — HIGH-FIDELITY SIM", tid, demo_mode), unsafe_allow_html=True)
        st.markdown('<div style="background:rgba(239,68,68,.03);border:1px solid rgba(239,68,68,.12);border-top:none;border-radius:0 0 8px 8px;padding:14px">', unsafe_allow_html=True)
        if "```json" in red:
            parts = red.split("```json")
            st.markdown(parts[0])
            st.code(parts[1].split("```")[0].strip(), language="json")
        else:
            st.markdown(red)
        st.markdown("</div>", unsafe_allow_html=True)

    with col_blue:
        st.markdown(_panel_head("blue", "DETECTION AGENT — DEFENSE", "", demo_mode), unsafe_allow_html=True)
        st.markdown('<div style="background:rgba(59,130,246,.03);border:1px solid rgba(59,130,246,.12);border-top:none;border-radius:0 0 8px 8px;padding:14px">', unsafe_allow_html=True)
        if "```yaml" in blue:
            parts = blue.split("```yaml")
            st.markdown(parts[0])
            st.code(parts[1].split("```")[0].strip(), language="yaml")
            if len(parts) > 2:
                st.markdown(parts[2])
        else:
            st.markdown(blue)
        st.markdown("</div>", unsafe_allow_html=True)

    if verifier:
        st.markdown(_verifier_html(verifier), unsafe_allow_html=True)


# ── APT Group HTML ─────────────────────────────────────────────────────────────

def _apt_actor_card(group: dict, count: int) -> str:
    name = group.get("name", "Unknown")
    aliases = ", ".join(group.get("aliases", [])[:5])
    raw_desc = group.get("description", "")
    desc = (raw_desc[:350] + "…") if len(raw_desc) > 350 else raw_desc
    return (
        '<div style="background:#0E1223;border:1px solid #334155;border-left:3px solid #F59E0B;'
        'border-radius:8px;padding:16px 20px;margin-bottom:14px">'
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px">'
        '<div>'
        '<div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#64748B;margin-bottom:5px;font-family:Inter,sans-serif">THREAT ACTOR</div>'
        f'<div style="font-size:18px;font-weight:700;color:#F8FAFC;letter-spacing:-.01em;font-family:Inter,sans-serif">{html.escape(name)}</div>'
        + (f'<div style="font-size:10px;color:#F59E0B;font-family:JetBrains Mono,monospace;margin-top:3px">aka {html.escape(aliases)}</div>' if aliases else "")
        + f'<p style="font-size:11px;color:#94A3B8;line-height:1.55;margin:8px 0 0;font-family:Inter,sans-serif">{html.escape(desc)}</p>'
        '</div>'
        '<div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);'
        'border-radius:6px;padding:8px 16px;text-align:center;flex-shrink:0">'
        f'<div style="font-family:JetBrains Mono,monospace;font-size:24px;font-weight:700;color:#F59E0B;line-height:1">{count}</div>'
        '<div style="font-size:8px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:#64748B;margin-top:3px;font-family:Inter,sans-serif">TECHNIQUES</div>'
        '</div></div></div>'
    )


def _trow_html(tid: str, name: str, status_text: str, badge: str, state: str) -> str:
    state_styles = {
        "done":   ("rgba(34,197,94,.1)", "rgba(34,197,94,.3)", "#86EFAC", "#22C55E"),
        "run":    ("rgba(139,92,246,.12)", "rgba(139,92,246,.35)", "#C4B5FD", "#8B5CF6"),
        "queued": ("#0F172A", "#334155", "#64748B", "#334155"),
    }
    bg, bd, badge_color, border_color = state_styles.get(state, state_styles["queued"])
    return (
        f'<div style="display:grid;grid-template-columns:auto 1fr auto auto;gap:14px;align-items:center;'
        f'background:#0E1223;border:1px solid #1E293B;border-left:2px solid {border_color};'
        f'border-radius:6px;padding:9px 14px;margin-bottom:6px">'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:11px;font-weight:700;color:#C4B5FD">{html.escape(tid)}</span>'
        f'<span style="font-size:11px;color:#F8FAFC;font-family:Inter,sans-serif">{html.escape(name)}</span>'
        f'<span style="font-family:JetBrains Mono,monospace;font-size:10px;color:#64748B">{html.escape(status_text)}</span>'
        f'<span style="background:{bg};border:1px solid {bd};color:{badge_color};'
        f'font-family:JetBrains Mono,monospace;font-size:9px;font-weight:700;'
        f'padding:3px 7px;border-radius:3px;letter-spacing:.06em">{html.escape(badge)}</span>'
        '</div>'
    )


# ── Kill Chain HTML ────────────────────────────────────────────────────────────

def _chain_flow_html(steps: list) -> str:
    nodes = ""
    for i, step in enumerate(steps):
        tid = step.get("technique_id", "")
        name = step.get("name", "")
        if i == 0:
            bg, bd, clr = "rgba(239,68,68,.12)", "rgba(239,68,68,.4)", "#FCA5A5"
        elif i == len(steps) - 1:
            bg, bd, clr = "rgba(34,197,94,.12)", "rgba(34,197,94,.4)", "#86EFAC"
        else:
            bg, bd, clr = "rgba(139,92,246,.12)", "rgba(139,92,246,.35)", "#C4B5FD"
        nodes += (
            f'<span style="display:inline-flex;align-items:center;gap:4px;background:{bg};'
            f'border:1px solid {bd};color:{clr};font-family:JetBrains Mono,monospace;'
            f'font-size:11px;font-weight:600;padding:5px 10px;border-radius:4px;white-space:nowrap" '
            f'title="{html.escape(name)}"><span style="opacity:.6;font-size:9px">#{i+1}</span>{html.escape(tid)}</span>'
        )
        if i < len(steps) - 1:
            nodes += '<span style="color:#475569;font-size:14px;margin:0 2px">→</span>'
    return (
        '<div style="background:#0F172A;border:1px solid #334155;border-radius:8px;'
        'padding:14px 16px;margin-bottom:14px">'
        '<div style="font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;'
        'color:#64748B;font-family:Inter,sans-serif;margin-bottom:10px">ATTACK CHAIN SEQUENCE</div>'
        f'<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px">{nodes}</div>'
        '</div>'
    )


# ── Topology Lab HTML ──────────────────────────────────────────────────────────

def _topology_html(topology: dict, path: dict) -> str:
    active = {node_id for hop in path["hops"] for node_id in (hop["from"], hop["to"])}
    node_map = {n["id"]: n for n in topology["nodes"]}

    zones_html = ""
    for zone in topology["zones"]:
        cards = ""
        for node in [n for n in topology["nodes"] if n["zone"] == zone]:
            is_active = node["id"] in active
            bdr = "#EF4444" if is_active else "#334155"
            bg = "rgba(239,68,68,.10)" if is_active else "#0F172A"
            clr = "#FCA5A5" if is_active else "#CBD5E1"
            cards += (
                f'<div style="background:{bg};border:1px solid {bdr};border-radius:6px;'
                'padding:8px 10px;margin-bottom:6px">'
                f'<div style="font-size:11px;font-weight:700;color:{clr};font-family:Inter,sans-serif;line-height:1.3">'
                f'{html.escape(node["label"])}</div>'
                f'<div style="font-size:9px;color:#64748B;font-family:JetBrains Mono,monospace;margin-top:3px">'
                f'{html.escape(node["ip"])}</div>'
                '</div>'
            )
        zones_html += (
            '<div style="min-width:140px;flex:1;background:#0E1223;border:1px solid #1E293B;border-radius:7px;padding:11px">'
            '<div style="font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;'
            f'color:#64748B;font-family:Inter,sans-serif;margin-bottom:8px">{html.escape(zone)}</div>'
            f'{cards}</div>'
        )

    hops_html = ""
    for i, hop in enumerate(path["hops"]):
        src = node_map.get(hop["from"], {}).get("label", hop["from"])
        dst = node_map.get(hop["to"], {}).get("label", hop["to"])
        hops_html += (
            f'<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(239,68,68,.10);'
            'border:1px solid rgba(239,68,68,.35);border-radius:4px;padding:4px 8px;'
            'font-family:JetBrains Mono,monospace;font-size:10px;color:#FCA5A5;white-space:nowrap">'
            f'#{i+1} {html.escape(src)} → {html.escape(dst)} · {html.escape(hop["technique_id"])}</span>'
        )
        if i < len(path["hops"]) - 1:
            hops_html += '<span style="color:#475569;margin:0 4px">→</span>'

    return (
        '<div style="background:#060C18;border:1px solid #334155;border-radius:10px;padding:16px;margin-bottom:14px">'
        '<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;margin-bottom:12px">'
        '<div>'
        '<div style="font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#8B5CF6;font-family:Inter,sans-serif">SANDBOX TOPOLOGY</div>'
        f'<div style="font-size:16px;font-weight:800;color:#F8FAFC;font-family:Inter,sans-serif;margin-top:3px">{html.escape(path["label"])}</div>'
        f'<p style="font-size:11px;color:#94A3B8;line-height:1.5;margin:5px 0 0;font-family:Inter,sans-serif;max-width:560px">{html.escape(path["summary"])}</p>'
        '</div>'
        '<div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);'
        'border-radius:5px;padding:5px 10px;color:#86EFAC;font-family:JetBrains Mono,monospace;font-size:10px">ZERO-DAY GENERATION: OUT OF SCOPE</div>'
        '</div>'
        f'<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:12px">{zones_html}</div>'
        '<div style="background:#0F172A;border:1px solid #1E293B;border-radius:6px;padding:10px 12px">'
        '<div style="font-size:9px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#64748B;font-family:Inter,sans-serif;margin-bottom:8px">ACTIVE LATERAL PATH</div>'
        f'<div style="display:flex;align-items:center;flex-wrap:wrap;gap:5px">{hops_html}</div>'
        '</div></div>'
    )


def _hop_card_html(hop: dict, index: int) -> str:
    telemetry = _pill_list(hop.get("telemetry", []), "rgba(59,130,246,.35)", "No telemetry")
    body = (
        f'<div style="background:#000810;border:1px solid #334155;border-radius:5px;padding:8px 10px;'
        f'font-family:JetBrains Mono,monospace;font-size:10px;color:#C4B5FD;margin-bottom:8px">'
        f'{html.escape(hop.get("command", ""))}</div>'
        f'<div style="font-size:10px;font-weight:700;letter-spacing:.10em;text-transform:uppercase;'
        f'color:#64748B;font-family:Inter,sans-serif;margin-bottom:6px">TELEMETRY</div>'
        f'<div style="margin-bottom:8px">{telemetry}</div>'
        f'<div style="font-size:12px;color:#93C5FD;line-height:1.55"><strong>Detection:</strong> {html.escape(hop.get("detection", ""))}</div>'
        f'<div style="font-size:12px;color:#86EFAC;line-height:1.55;margin-top:5px"><strong>Response:</strong> {html.escape(hop.get("response", ""))}</div>'
        f'<div style="font-size:11px;color:#F59E0B;font-family:JetBrains Mono,monospace;margin-top:6px">Realtime: {html.escape(hop.get("realtime_signal", ""))}</div>'
    )
    return _artifact_card(
        f"HOP {index} · {hop.get('technique_id','')} · {hop.get('technique_name','')}",
        f"{hop.get('from','')} → {hop.get('to','')} · reacts in ~{hop.get('reaction_seconds', 0)}s",
        "#EF4444",
        body,
    )


# ── Artifact exports ───────────────────────────────────────────────────────────

def _splunk_spl(red_output: str, tid: str) -> str:
    red_json = _extract_red_json(red_output)
    obs = [str(o) for o in red_json.get("observables", []) if o]
    net = [str(n) for n in red_json.get("network_indicators", []) if n]
    if not obs:
        return (
            f'index=windows (sourcetype="WinEventLog:Security" OR sourcetype="Sysmon")\n'
            f'  earliest=-24h\n| eval mitre_technique="{tid}"\n'
            f'| stats count by host, user, ParentImage, Image, CommandLine, mitre_technique\n| sort -count'
        )
    obs_clause = " OR ".join(f'"{o}"' for o in obs[:10])
    net_clause = " OR ".join(f'DestinationHostname="*{n}*"' for n in net[:5])
    net_line = f'\n  AND ({net_clause})' if net_clause else ''
    return (
        f'index=windows (sourcetype="WinEventLog:Security" OR sourcetype="Sysmon" OR sourcetype="WinEventLog:Microsoft-Windows-PowerShell/Operational")\n'
        f'  earliest=-24h\n  ({obs_clause}){net_line}\n'
        f'| eval mitre_technique="{tid}"\n'
        f'| eval suspicious_parent=if(match(ParentImage, "(?i)WINWORD\\\\.EXE|EXCEL\\\\.EXE|OUTLOOK\\\\.EXE"), 1, 0)\n'
        f'| stats count, values(CommandLine) as cmdlines, values(ParentImage) as parents\n'
        f'    by host, user, Image, mitre_technique, suspicious_parent\n'
        f'| where count > 0 | sort -suspicious_parent, -count'
    )


def _verifier_summary(verifier_output: str) -> dict:
    if not verifier_output:
        return {"verdict": "PENDING", "coverage_score": 0, "covered": [], "missing": []}
    try:
        m = re.search(r'```json\s*(.*?)\s*```', verifier_output, re.DOTALL)
        data = json.loads(m.group(1) if m else verifier_output)
        return {
            "verdict": data.get("verdict", "UNKNOWN"),
            "coverage_score": int(data.get("coverage_score", 0) or 0),
            "covered": [str(x) for x in data.get("covered_observables", []) or []],
            "missing": [str(x) for x in data.get("missing_observables", []) or []],
            "safety_verdict": data.get("safety_verdict", "PASS"),
        }
    except Exception:
        return {"verdict": "UNKNOWN", "coverage_score": 0, "covered": [], "missing": []}


def _vectr_csv(tid: str, red: str, blue: str, verifier: str | None) -> bytes:
    red_json = _extract_red_json(red)
    sigma = _extract_fenced(blue, "yaml")
    case_name = _sigma_title(sigma) or red_json.get("technique_name", "") or tid
    tactic = red_json.get("tactic", "")
    observables = [str(o) for o in red_json.get("observables", []) if o]
    summary = _verifier_summary(verifier or "")
    rows = [
        ["Campaign", "Test Case ID", "Test Case Name", "MITRE ATT&CK ID", "Tactic",
         "Description", "Detection Source", "Indicators", "Outcome", "Status", "Detection Coverage %", "Source"],
        ["AegisOps Readiness Drill", f"AGO-{tid}", case_name, tid, tactic,
         f"Authorized purple-team validation for ATT&CK {tid}. Generated by AegisOps AI multi-agent pipeline.",
         "Sigma + Splunk SPL + EDR telemetry", "; ".join(observables[:12]),
         summary["verdict"], "Closed" if summary["verdict"] == "PASS" else "Open",
         str(summary["coverage_score"]), "AegisOps AI · vLLM/ROCm · MI300X"],
    ]
    buf = io.StringIO()
    csv.writer(buf).writerows(rows)
    return buf.getvalue().encode("utf-8")


def _render_downloads(red: str, blue: str, verifier: str | None, tid: str):
    sigma_yaml = _extract_fenced(blue, "yaml")
    spl_query = _splunk_spl(red, tid)
    vectr_data = _vectr_csv(tid, red, blue, verifier)
    try:
        pdf_bytes = generate_pdf(tid, red, blue)
    except Exception:
        pdf_bytes = None

    st.markdown(_section_header("Detection Engineering Artifacts", "Drop into SIEM, EDR, or VECTR", "#3B82F6"), unsafe_allow_html=True)
    col_sigma, col_spl = st.columns(2, gap="small")
    with col_sigma:
        st.markdown("##### Sigma Rule")
        if sigma_yaml:
            st.code(sigma_yaml, language="yaml")
        else:
            st.caption("No Sigma YAML block extracted.")
        st.download_button("Download Sigma (.yml)", data=(sigma_yaml or "").encode(), file_name=f"aegisops_sigma_{tid}.yml", mime="application/x-yaml", use_container_width=True, disabled=not sigma_yaml)
    with col_spl:
        st.markdown("##### Splunk SPL")
        st.code(spl_query, language="text")
        st.download_button("Download Splunk SPL (.spl)", data=spl_query.encode(), file_name=f"aegisops_splunk_{tid}.spl", mime="text/plain", use_container_width=True)

    col_vectr, col_pdf = st.columns(2, gap="small")
    with col_vectr:
        st.download_button("Download VECTR-Style CSV", data=vectr_data, file_name=f"aegisops_vectr_{tid}.csv", mime="text/csv", use_container_width=True)
    with col_pdf:
        if pdf_bytes:
            st.markdown(_pdf_download_link("Download Full PDF Report", pdf_bytes, f"aegisops_report_{tid}.pdf"), unsafe_allow_html=True)


def _render_rocm_evidence():
    evidence = [
        ("rocm_smi.json",       "ROCm GPU snapshot (rocm-smi --json)"),
        ("vllm_info.txt",       "vLLM version + endpoint metadata"),
        ("rocm_benchmark.json", "Latency + throughput benchmark summary"),
    ]
    cols = st.columns(3, gap="small")
    for idx, (name, label) in enumerate(evidence):
        path = ASSETS_DIR / name
        with cols[idx]:
            if not path.exists():
                st.caption(f"{name} not present yet.")
                continue
            data = path.read_bytes()
            mime = "application/json" if name.endswith(".json") else "text/plain"
            st.download_button(f"Download {name}", data=data, file_name=name, mime=mime, use_container_width=True)
            with st.expander(label, expanded=False):
                if name.endswith(".json"):
                    try:
                        st.json(json.loads(data.decode()))
                    except Exception:
                        st.code(data.decode("utf-8", errors="replace"))
                else:
                    st.code(data.decode("utf-8", errors="replace"))


# ── Session state init ─────────────────────────────────────────────────────────
for _k, _v in [
    ("pipeline_version", PIPELINE_VERSION),
    ("red", None), ("blue", None), ("verifier", None), ("metrics", None),
    ("technique_id", "T1059.001"), ("context_note", ""),
    ("apt_mode", False), ("apt_group", {}), ("apt_results", []),
    ("chain_mode", False), ("chain_results", []),
]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

if st.session_state.pipeline_version != PIPELINE_VERSION:
    for _k in ["red", "blue", "verifier", "metrics", "apt_results", "chain_results", "apt_mode", "chain_mode"]:
        st.session_state[_k] = None if _k in ("red", "blue", "verifier", "metrics") else ([] if "results" in _k else False)
    st.session_state.pipeline_version = PIPELINE_VERSION
    st.rerun()


# ── Cached live health probe ───────────────────────────────────────────────────
@st.cache_data(ttl=20, show_spinner=False)
def _health() -> dict:
    return dict(live_health(timeout_s=3.0))


# ── Agent runner ───────────────────────────────────────────────────────────────
def run_agents(tid: str, demo: bool) -> tuple:
    result = DEMO_INVOKE_RESULT if demo else pipeline_app.invoke({"technique_id": tid})
    blue = result["blue_output"]
    resp = result.get("response_output")
    if resp and resp not in blue:
        blue = f"{blue}\n\n{resp}"
    return result["red_output"], blue, result.get("verifier_output"), result.get("metrics")


# ── Sidebar ────────────────────────────────────────────────────────────────────
live_llm_configured = has_live_llm_config()

with st.sidebar:
    # Brand header
    st.markdown(
        '<div style="display:flex;align-items:center;gap:10px;padding:6px 4px 14px;'
        'border-bottom:1px solid #1E293B;margin-bottom:16px">'
        '<div style="width:30px;height:30px;border-radius:8px;flex-shrink:0;'
        'background:linear-gradient(135deg,#7C3AED,#4F46E5);'
        'display:flex;align-items:center;justify-content:center;'
        'font-family:JetBrains Mono,monospace;font-weight:700;color:#fff;font-size:16px;'
        'box-shadow:0 4px 12px rgba(139,92,246,.4)">A</div>'
        '<div>'
        '<div style="font-weight:800;font-size:15px;letter-spacing:-.01em;color:#F8FAFC">AegisOps AI</div>'
        '<div style="font-family:JetBrains Mono,monospace;font-size:9px;color:#64748B;margin-top:1px">v1.0 · ROCm</div>'
        '</div></div>',
        unsafe_allow_html=True,
    )

    # Mode nav
    st.markdown(
        '<div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
        'color:#64748B;margin-bottom:6px;font-family:Inter,sans-serif">Mode</div>',
        unsafe_allow_html=True,
    )
    mode = st.radio(
        "Mode",
        ["Single Technique", "APT Group", "Kill Chain", "Topology Lab"],
        label_visibility="collapsed",
    )

    st.markdown('<div style="height:1px;background:#1E293B;margin:16px 0"></div>', unsafe_allow_html=True)

    # Settings
    st.markdown(
        '<div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
        'color:#64748B;margin-bottom:8px;font-family:Inter,sans-serif">Settings</div>',
        unsafe_allow_html=True,
    )
    demo_mode = st.toggle("Demo Mode", value=not live_llm_configured, help="Replay precomputed golden run. Disable to hit the live MI300X/vLLM endpoint.")
    verbose_output = st.toggle("Verbose Output", value=True, help="Show full agent markdown output below the summary panels.")

    if demo_mode:
        st.markdown(
            '<div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.25);'
            'border-radius:6px;padding:8px 10px;margin-top:8px">'
            '<p style="font-size:11px;color:#FCD34D;margin:0;line-height:1.5">'
            'Replaying AMD MI300X golden run. AMD provenance preserved.</p></div>',
            unsafe_allow_html=True,
        )
    elif not live_llm_configured:
        st.markdown(
            '<div style="background:rgba(239,68,68,.08);border:1px solid rgba(239,68,68,.25);'
            'border-radius:6px;padding:8px 10px;margin-top:8px">'
            '<p style="font-size:11px;color:#FCA5A5;margin:0;line-height:1.5">'
            'Live secrets not configured. Toggle Demo Mode or run ./start_vllm.sh.</p></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height:1px;background:#1E293B;margin:16px 0"></div>', unsafe_allow_html=True)

    # Endpoint info box
    st.markdown(
        '<div style="font-size:9px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
        'color:#64748B;margin-bottom:8px;font-family:Inter,sans-serif">Endpoint</div>',
        unsafe_allow_html=True,
    )
    health = {} if demo_mode else _health()
    if demo_mode:
        ep_runtime, ep_model, ep_latency_color, ep_latency = "vLLM · ROCm", "MI300X · Llama 3.3 70B", "#F59E0B", "DEMO"
    elif health.get("reachable"):
        ep_model_name = _short_model(str(health.get("model") or os.getenv("MODEL_NAME") or ""))
        ep_runtime, ep_model = "vLLM · ROCm", f"MI300X · {ep_model_name}"
        ep_latency_color, ep_latency = "#22C55E", f"● {health.get('latency_ms')} ms"
    else:
        ep_runtime, ep_model = "vLLM · ROCm", "MI300X · not reachable"
        ep_latency_color, ep_latency = "#EF4444", "● offline"

    st.markdown(
        '<div style="padding:8px 10px;background:#0F172A;border-radius:6px;border:1px solid #334155;'
        'font-family:JetBrains Mono,monospace;font-size:10px;line-height:1.6">'
        f'<div style="color:#86EFAC">{html.escape(ep_runtime)}</div>'
        f'<div style="color:#64748B">{html.escape(ep_model)}</div>'
        f'<div style="color:{ep_latency_color};margin-top:4px">{html.escape(ep_latency)}</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # Footer
    st.markdown(
        '<div style="margin-top:auto;padding-top:16px;border-top:1px solid #1E293B;margin-top:20px">'
        '<p style="font-family:JetBrains Mono,monospace;font-size:10px;color:#64748B;line-height:1.7;margin:0">'
        'MITRE ATT&amp;CK v14<br>4-agent pipeline</p>'
        '</div>',
        unsafe_allow_html=True,
    )


# ── Mode sync ──────────────────────────────────────────────────────────────────
if mode != "APT Group":
    st.session_state.apt_mode = False
if mode != "Kill Chain":
    st.session_state.chain_mode = False


# ══════════════════════════════════════════════════════════════════════════════
# MODE: SINGLE TECHNIQUE
# ══════════════════════════════════════════════════════════════════════════════
if mode == "Single Technique":
    st.markdown(_page_header_html("Single Technique", demo_mode), unsafe_allow_html=True)
    st.markdown(_rocm_panel_html(demo_mode, health), unsafe_allow_html=True)
    st.markdown(_status_bar_html(demo_mode, "Single Technique"), unsafe_allow_html=True)

    # Input row
    col_tid, col_ctx, col_btn = st.columns([2, 2, 1], gap="small", vertical_alignment="bottom")
    with col_tid:
        technique_id = st.text_input("Technique ID", value=st.session_state.technique_id, placeholder="e.g. T1059.001")
    with col_ctx:
        context_note = st.text_input("Context (optional)", value=st.session_state.context_note, placeholder="e.g. Windows endpoint, SOC tier-2")
    with col_btn:
        btn_label = "REPLAY DEMO" if demo_mode else "RUN PIPELINE"
        run_clicked = st.button(btn_label, type="primary", use_container_width=True)

    if run_clicked:
        tid = (technique_id or "T1059.001").strip().upper()
        st.session_state.technique_id = tid
        st.session_state.context_note = context_note
        st.session_state.apt_mode = False
        st.session_state.chain_mode = False
        with st.status("Orchestrating 4-agent pipeline…", expanded=True) as status:
            st.write(f"Target: **{tid}**")
            st.write("🔴 Threat Agent — high-fidelity ATT&CK simulation…")
            st.write("🔵 Detection Agent — Sigma rule + SIEM correlation…")
            st.write("🟢 Response Agent — analyst response runbook…")
            st.write("🟣 Validator Agent — coverage & safety gates…")
            red, blue, verifier, metrics = run_agents(tid, demo_mode)
            st.session_state.red = red
            st.session_state.blue = blue
            st.session_state.verifier = verifier
            st.session_state.metrics = metrics
            status.update(label=f"✓ Pipeline complete — {tid}", state="complete", expanded=False)

    if st.session_state.get("red") and not st.session_state.get("apt_mode") and not st.session_state.get("chain_mode"):
        tid = st.session_state.technique_id
        red = st.session_state.red
        blue = st.session_state.blue
        verifier = st.session_state.get("verifier")
        metrics = st.session_state.get("metrics")

        # Pipeline metrics
        m_html = _pipeline_metrics_html(metrics, demo_mode)
        if m_html:
            st.markdown(m_html, unsafe_allow_html=True)

        # Demo mode: show evidence downloads before agent panels
        if demo_mode:
            st.markdown(_section_header("Bundled Evidence", "Captured from AMD MI300X", "#F59E0B"), unsafe_allow_html=True)
            _render_rocm_evidence()

        # Agent panels
        st.markdown(_section_header("Agent Evidence", "Transparent Multi-Agent Trace", "#8B5CF6"), unsafe_allow_html=True)
        display_agent_panels(red, blue, verifier, tid, demo_mode)

        # Artifact cards (observables, response, realtime)
        st.markdown(_section_header("Defensive Deliverables", "Operationalized ATT&CK Intelligence", "#22C55E"), unsafe_allow_html=True)
        _render_operational_outputs(red, blue)

        # Downloads
        _render_downloads(red, blue, verifier, tid)

    elif not run_clicked:
        st.info("Enter a Technique ID above and press RUN PIPELINE to engage the 4-agent pipeline.")


# ══════════════════════════════════════════════════════════════════════════════
# MODE: APT GROUP
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "APT Group":
    st.markdown(_page_header_html("APT Group"), unsafe_allow_html=True)
    st.markdown(_rocm_panel_html(demo_mode, health), unsafe_allow_html=True)
    st.markdown(_status_bar_html(demo_mode, "APT Group"), unsafe_allow_html=True)

    col_actor, col_limit, col_btn = st.columns([2, 2, 1], gap="small", vertical_alignment="bottom")
    with col_actor:
        apt_input = st.text_input("Threat Actor", placeholder="e.g. APT28, Lazarus, Cozy Bear")
    with col_limit:
        tech_limit = st.selectbox("Technique Limit", ["Top 5 techniques", "Top 10 techniques", "Top 12 techniques"], index=0)
    with col_btn:
        apt_clicked = st.button("RUN ACTOR PROFILE", type="primary", use_container_width=True)

    limit_n = int(tech_limit.split()[1])

    if apt_clicked:
        if not apt_input.strip():
            st.warning("Enter an APT group name to continue.")
        else:
            info = get_group_info(apt_input)
            techniques = get_apt_techniques(apt_input)[:limit_n]
            if not techniques:
                st.error(f'Group "{apt_input}" not found in MITRE ATT&CK database.')
            else:
                st.session_state.apt_mode = True
                st.session_state.apt_group = info
                st.session_state.apt_results = []
                prog = st.progress(0)
                for i, tech in enumerate(techniques):
                    with st.spinner(f"[{i+1}/{len(techniques)}] {tech['technique_id']} — {tech['name']}"):
                        red, blue, verifier, metrics = run_agents(tech["technique_id"], demo_mode)
                        st.session_state.apt_results.append({"technique": tech, "red": red, "blue": blue, "verifier": verifier, "metrics": metrics})
                    prog.progress((i + 1) / len(techniques))

    if st.session_state.get("apt_mode") and st.session_state.get("apt_results"):
        group = st.session_state.apt_group
        results = st.session_state.apt_results
        n = len(results)

        # Actor card
        st.markdown(_apt_actor_card(group, n), unsafe_allow_html=True)

        # Metrics row
        scores = []
        for r in results:
            s = _verifier_summary(r.get("verifier") or "")
            scores.append(s["coverage_score"])
        avg_cov = round(sum(scores) / len(scores)) if scores else 0
        st.markdown(_metric_row([
            (str(n), "Techniques", "#EF4444"),
            ("12", "Tactics", "#8B5CF6"),
            (f"{avg_cov}%", "Avg Coverage", "#22C55E"),
            (f"0 / {n}", "Running", "#F59E0B"),
            (str(n), "Sigma Rules", "#3B82F6"),
        ]), unsafe_allow_html=True)

        # Technique list overview
        st.markdown(
            '<div style="font-size:10px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;'
            'color:#8B5CF6;font-family:Inter,sans-serif;margin:14px 0 8px">BATCH RUN · 4-AGENT PIPELINE PER TECHNIQUE</div>',
            unsafe_allow_html=True,
        )
        rows_html = ""
        for r in results:
            t = r["technique"]
            s = _verifier_summary(r.get("verifier") or "")
            rows_html += _trow_html(t["technique_id"], t["name"], f"done · {s['coverage_score']}%", "DONE", "done")
        st.markdown(rows_html, unsafe_allow_html=True)

        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

        # Expandable detail per technique
        for i, result in enumerate(results):
            t = result["technique"]
            with st.expander(f"[{i+1:02d}]  {t['technique_id']}  —  {t['name']}", expanded=(i == 0)):
                m_html = _pipeline_metrics_html(result.get("metrics"), demo_mode)
                if m_html:
                    st.markdown(m_html, unsafe_allow_html=True)
                display_agent_panels(result["red"], result["blue"], result.get("verifier"), t["technique_id"], demo_mode)
                if verbose_output:
                    _render_operational_outputs(result["red"], result["blue"])

        st.divider()
        col_pdf, col_json, _ = st.columns([1, 1, 2], gap="small")
        combined_red = "\n\n---\n\n".join(r["red"] for r in results)
        combined_blue = "\n\n---\n\n".join(r["blue"] for r in results)
        with col_pdf:
            try:
                pdf_bytes = generate_pdf(group.get("name", "APT"), combined_red, combined_blue)
                st.markdown(_pdf_download_link(f"Export Actor PDF — {group.get('name','')}", pdf_bytes, f"apt_{group.get('name','actor').replace(' ','_')}.pdf"), unsafe_allow_html=True)
            except Exception:
                pass
        with col_json:
            bundle = json.dumps([{"technique": r["technique"], "coverage": _verifier_summary(r.get("verifier") or "")["coverage_score"]} for r in results], indent=2)
            st.download_button("Download JSON Bundle", data=bundle.encode(), file_name=f"apt_{group.get('name','bundle').replace(' ','_')}.json", mime="application/json", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# MODE: KILL CHAIN
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Kill Chain":
    st.markdown(_page_header_html("Kill Chain"), unsafe_allow_html=True)
    st.markdown(_rocm_panel_html(demo_mode, health), unsafe_allow_html=True)
    st.markdown(_status_bar_html(demo_mode, "Kill Chain"), unsafe_allow_html=True)

    col_tid, col_depth, col_btn = st.columns([2, 2, 1], gap="small", vertical_alignment="bottom")
    with col_tid:
        start_tid = st.text_input("Starting Technique", placeholder="e.g. T1566.001 (Spearphishing Attachment)", value="T1566.001")
    with col_depth:
        chain_depth = st.selectbox("Chain Depth", ["2 hops", "3 hops", "4 hops", "5 hops"], index=2)
    with col_btn:
        chain_clicked = st.button("CHAIN PIPELINE", type="primary", use_container_width=True)

    depth_n = int(chain_depth.split()[0])

    if chain_clicked:
        if not start_tid.strip():
            st.warning("Enter a starting technique ID.")
        else:
            from chain import get_next_techniques
            chain = [{"technique_id": start_tid.strip().upper(), "name": "Initial Technique"}]
            chain.extend(get_next_techniques(start_tid.strip().upper()))
            chain = chain[:depth_n]
            st.session_state.chain_mode = True
            st.session_state.chain_results = []
            prog = st.progress(0)
            for i, tech in enumerate(chain):
                with st.spinner(f"Chain step {i+1}/{len(chain)}: {tech['technique_id']}"):
                    red, blue, verifier, metrics = run_agents(tech["technique_id"], demo_mode)
                    st.session_state.chain_results.append({"step": i+1, "technique": tech, "red": red, "blue": blue, "verifier": verifier, "metrics": metrics})
                prog.progress((i + 1) / len(chain))

    if st.session_state.get("chain_mode") and st.session_state.get("chain_results"):
        results = st.session_state.chain_results
        steps = [r["technique"] for r in results]
        n = len(results)

        # Chain flow visualization
        st.markdown(_chain_flow_html(steps), unsafe_allow_html=True)

        # Metrics
        scores = [_verifier_summary(r.get("verifier") or "")["coverage_score"] for r in results]
        avg_cov = round(sum(scores) / len(scores)) if scores else 0
        total_agents = n * 4
        st.markdown(_metric_row([
            (str(n), "Chain Hops", "#EF4444"),
            (str(total_agents), "Agent Calls", "#8B5CF6"),
            (f"{avg_cov}%", "Coverage", "#22C55E"),
            ("—", "Reaction Time", "#F59E0B"),
        ]), unsafe_allow_html=True)

        # Technique rows overview
        rows_html = ""
        for r in results:
            t = r["technique"]
            s = _verifier_summary(r.get("verifier") or "")
            rows_html += _trow_html(t["technique_id"], t.get("name", ""), f"done · {s['coverage_score']}%", f"STEP {r['step']}", "done")
        st.markdown(rows_html, unsafe_allow_html=True)
        st.markdown('<div style="height:14px"></div>', unsafe_allow_html=True)

        # Expandable detail per hop
        for result in results:
            t = result["technique"]
            with st.expander(f"[STEP {result['step']:02d}]  {t['technique_id']}  —  {t.get('name', '')}", expanded=(result["step"] == 1)):
                m_html = _pipeline_metrics_html(result.get("metrics"), demo_mode)
                if m_html:
                    st.markdown(m_html, unsafe_allow_html=True)
                display_agent_panels(result["red"], result["blue"], result.get("verifier"), t["technique_id"], demo_mode)
                if verbose_output:
                    _render_operational_outputs(result["red"], result["blue"])

        st.divider()
        col_dl, _ = st.columns([1, 3], gap="small")
        combined_red = "\n\n---\n\n".join(r["red"] for r in results)
        combined_blue = "\n\n---\n\n".join(r["blue"] for r in results)
        chain_name = " → ".join(r["technique"]["technique_id"] for r in results)
        with col_dl:
            try:
                pdf_bytes = generate_pdf(chain_name, combined_red, combined_blue)
                st.markdown(_pdf_download_link("Download Kill Chain Report", pdf_bytes, "kill_chain_report.pdf"), unsafe_allow_html=True)
            except Exception:
                pass


# ══════════════════════════════════════════════════════════════════════════════
# MODE: TOPOLOGY LAB
# ══════════════════════════════════════════════════════════════════════════════
elif mode == "Topology Lab":
    st.markdown(_page_header_html("Topology Lab"), unsafe_allow_html=True)
    st.markdown(_rocm_panel_html(demo_mode, health), unsafe_allow_html=True)
    st.markdown(_status_bar_html(demo_mode, "Topology Lab"), unsafe_allow_html=True)

    col_tid, col_path, col_btn = st.columns([2, 2, 1], gap="small", vertical_alignment="bottom")
    with col_tid:
        seed = st.text_input("Starting Technique", value="T1566.001", placeholder="e.g. T1566.001, T1059.001, T1078")
    paths = generate_attack_paths(seed.strip() or "T1566.001")
    with col_path:
        selected_label = st.selectbox("Attack Path", [p["label"] for p in paths])
    with col_btn:
        simulate_clicked = st.button("SIMULATE", type="primary", use_container_width=True)

    selected_path = next(p for p in paths if p["label"] == selected_label)
    topology = generate_topology(seed.strip() or "T1566.001")
    score = score_path_detection(selected_path)

    # Metrics
    st.markdown(_metric_row([
        (str(len(topology["nodes"])), "Sandbox Nodes", "#8B5CF6"),
        (str(len(selected_path["hops"])), "Attack Hops", "#EF4444"),
        (f'{score["coverage"]}%', "Detection Coverage", "#22C55E"),
        (f'{score["avg_reaction_seconds"]}s', "Avg Reaction", "#F59E0B"),
    ]), unsafe_allow_html=True)

    # Topology panel
    st.markdown(_topology_html(topology, selected_path), unsafe_allow_html=True)

    # Attack timeline (hop cards)
    st.markdown(_section_header("Attack Timeline", "Known ATT&CK Path to Defensive Reaction", "#EF4444"), unsafe_allow_html=True)
    for idx, hop in enumerate(selected_path["hops"], start=1):
        st.markdown(_hop_card_html(hop, idx), unsafe_allow_html=True)

    # Realtime readiness + validation score
    col_rt, col_gap = st.columns([2, 1], gap="small")
    rt_body = "<ul style='margin:0;padding-left:14px;list-style:none'>" + "".join(
        f'<li style="font-size:11px;color:#CBD5E1;line-height:1.55;margin-bottom:4px;position:relative;padding-left:14px">'
        f'<span style="position:absolute;left:0;color:#22C55E;font-family:JetBrains Mono,monospace">→</span>'
        f'{html.escape(hop["realtime_signal"])}</li>'
        for hop in selected_path["hops"]
    ) + "</ul>"
    with col_rt:
        st.markdown(_artifact_card("Realtime Detection Readiness", "Streaming alert conditions per hop.", "#3B82F6", rt_body), unsafe_allow_html=True)

    missing_body = (
        "<ul style='margin:0;padding-left:14px;list-style:none'>" + "".join(
            f'<li style="font-size:11px;color:#FCA5A5;line-height:1.55;margin-bottom:4px;position:relative;padding-left:14px">'
            f'<span style="position:absolute;left:0;color:#EF4444;font-family:JetBrains Mono,monospace">!</span>'
            f'{html.escape(item)}</li>'
            for item in score["missing"]
        ) + "</ul>"
        if score["missing"]
        else '<span style="font-size:12px;color:#86EFAC">No major detection gaps in this sandbox path.</span>'
    )
    with col_gap:
        st.markdown(
            _artifact_card("Validation Score", f'{score["telemetry_sources"]} telemetry signals mapped.', "#22C55E", missing_body),
            unsafe_allow_html=True,
        )
