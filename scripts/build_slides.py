#!/usr/bin/env python3
"""Build the AegisOps AI hackathon slide deck PDF.

Generates a clean, dark-themed, 16:9 PDF covering every lablab.ai judging axis:
problem -> solution -> 4-agent architecture -> AMD/ROCm proof -> demo flow ->
business value -> originality -> roadmap -> ask. Reproducible from source so
the deck always matches the README and code.

Usage:
    python scripts/build_slides.py
    # writes docs/AegisOps_AI_Slides.pdf
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from reportlab.lib.colors import HexColor
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


REPO = Path(__file__).resolve().parent.parent
ASSETS = REPO / "assets"
DOCS = REPO / "docs"
OUTPUT = DOCS / "AegisOps_AI_Slides.pdf"

# 16:9 at print-friendly resolution
PAGE_W, PAGE_H = 13.333 * inch, 7.5 * inch

BG = HexColor("#020617")
PANEL = HexColor("#0E1223")
BORDER = HexColor("#334155")
FG = HexColor("#F8FAFC")
FG_MUTED = HexColor("#94A3B8")
FG_DIM = HexColor("#64748B")
PURPLE = HexColor("#8B5CF6")
RED = HexColor("#EF4444")
BLUE = HexColor("#3B82F6")
GREEN = HexColor("#22C55E")
AMBER = HexColor("#F59E0B")
CYAN = HexColor("#06B6D4")


def _try_register_inter() -> tuple[str, str]:
    """Use Inter if available, otherwise fall back to Helvetica."""
    candidates = [
        ("Inter", "/usr/share/fonts/truetype/inter/Inter-Regular.ttf", "/usr/share/fonts/truetype/inter/Inter-Bold.ttf"),
        ("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]
    for family, regular, bold in candidates:
        if Path(regular).exists() and Path(bold).exists():
            try:
                pdfmetrics.registerFont(TTFont(family, regular))
                pdfmetrics.registerFont(TTFont(f"{family}-Bold", bold))
                return family, f"{family}-Bold"
            except Exception:
                continue
    return "Helvetica", "Helvetica-Bold"


REGULAR, BOLD = _try_register_inter()


def _draw_background(c: canvas.Canvas) -> None:
    c.setFillColor(BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)


def _draw_chrome(c: canvas.Canvas, slide_no: int, total: int, title: str) -> None:
    # Top brand bar
    c.setFillColor(PANEL)
    c.rect(0, PAGE_H - 0.55 * inch, PAGE_W, 0.55 * inch, fill=1, stroke=0)
    c.setFillColor(FG)
    c.setFont(BOLD, 13)
    c.drawString(0.5 * inch, PAGE_H - 0.36 * inch, "AegisOps AI")
    c.setFillColor(PURPLE)
    c.setFont(BOLD, 13)
    c.drawString(0.5 * inch + c.stringWidth("AegisOps ", BOLD, 13), PAGE_H - 0.36 * inch, "AI")
    c.setFillColor(FG_DIM)
    c.setFont(REGULAR, 9)
    c.drawString(1.65 * inch, PAGE_H - 0.36 * inch, "MITRE TO DETECTION COPILOT  ·  AMD DEVELOPER HACKATHON 2026")
    c.setFillColor(FG_DIM)
    c.drawRightString(PAGE_W - 0.5 * inch, PAGE_H - 0.36 * inch, f"{slide_no:02d} / {total:02d}  ·  {title}")

    # Bottom border line
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.5)
    c.line(0.5 * inch, 0.45 * inch, PAGE_W - 0.5 * inch, 0.45 * inch)

    c.setFillColor(FG_DIM)
    c.setFont(REGULAR, 8)
    c.drawString(0.5 * inch, 0.27 * inch, "github.com/ztothez/aegisops-ai")
    c.drawRightString(PAGE_W - 0.5 * inch, 0.27 * inch, "Track 1 · AI Agents & Agentic Workflows")


def _draw_title(c: canvas.Canvas, eyebrow: str, title: str, accent=PURPLE) -> float:
    c.setFillColor(accent)
    c.setFont(BOLD, 10)
    c.drawString(0.55 * inch, PAGE_H - 1.0 * inch, eyebrow.upper())
    c.setFillColor(FG)
    c.setFont(BOLD, 28)
    c.drawString(0.55 * inch, PAGE_H - 1.45 * inch, title)
    return PAGE_H - 1.75 * inch  # body baseline


def _draw_paragraph(c: canvas.Canvas, x: float, y: float, w: float, text: str, size: int = 11, color=FG_MUTED, leading: float = 1.45) -> float:
    c.setFillColor(color)
    c.setFont(REGULAR, size)
    words = text.split()
    line: list[str] = []
    line_w = 0.0
    space_w = c.stringWidth(" ", REGULAR, size)
    line_height = size * leading
    for word in words:
        word_w = c.stringWidth(word, REGULAR, size)
        if line and line_w + space_w + word_w > w:
            c.drawString(x, y, " ".join(line))
            y -= line_height
            line, line_w = [word], word_w
        else:
            line_w = word_w if not line else line_w + space_w + word_w
            line.append(word)
    if line:
        c.drawString(x, y, " ".join(line))
        y -= line_height
    return y


def _draw_bullets(c: canvas.Canvas, x: float, y: float, w: float, items: Sequence[str], size: int = 11, accent=PURPLE) -> float:
    bullet_w = 0.18 * inch
    for item in items:
        c.setFillColor(accent)
        c.setFont(BOLD, size)
        c.drawString(x, y, "›")
        next_y = _draw_paragraph(c, x + bullet_w, y, w - bullet_w, item, size=size)
        y = next_y - 0.06 * inch
    return y


def _draw_pill(c: canvas.Canvas, x: float, y: float, label: str, fg, bg) -> float:
    pad_x = 0.12 * inch
    pad_y = 0.06 * inch
    c.setFont(BOLD, 9)
    text_w = c.stringWidth(label, BOLD, 9)
    w = text_w + 2 * pad_x
    h = 9 + 2 * pad_y
    c.setFillColor(bg)
    c.setStrokeColor(fg)
    c.roundRect(x, y, w, h, 4, fill=1, stroke=1)
    c.setFillColor(fg)
    c.drawString(x + pad_x, y + pad_y + 1, label)
    return x + w + 0.08 * inch


def _draw_card(c: canvas.Canvas, x: float, y: float, w: float, h: float, eyebrow: str, lines: Sequence[str], accent=PURPLE) -> None:
    c.setFillColor(PANEL)
    c.setStrokeColor(BORDER)
    c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
    c.setStrokeColor(accent)
    c.setLineWidth(2)
    c.line(x, y + h, x + w, y + h)
    c.setFillColor(accent)
    c.setFont(BOLD, 9)
    c.drawString(x + 0.18 * inch, y + h - 0.32 * inch, eyebrow.upper())
    cy = y + h - 0.62 * inch
    c.setFillColor(FG)
    c.setFont(REGULAR, 10)
    for line in lines:
        c.drawString(x + 0.18 * inch, cy, line)
        cy -= 0.22 * inch


def _slide_cover(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    cover = ASSETS / "cover.png"
    if cover.exists():
        c.drawImage(str(cover), 0, 0, width=PAGE_W, height=PAGE_H, preserveAspectRatio=True, mask="auto", anchor="c")
    # Title overlay band
    band_h = 1.6 * inch
    c.setFillColorRGB(0.012, 0.024, 0.090, alpha=0.85)
    c.rect(0, 0, PAGE_W, band_h, fill=1, stroke=0)
    c.setFillColor(FG)
    c.setFont(BOLD, 30)
    c.drawString(0.6 * inch, band_h - 0.55 * inch, "AegisOps AI")
    c.setFillColor(PURPLE)
    c.setFont(BOLD, 30)
    c.drawString(0.6 * inch + c.stringWidth("AegisOps ", BOLD, 30), band_h - 0.55 * inch, "")
    c.setFillColor(FG_MUTED)
    c.setFont(REGULAR, 12)
    c.drawString(0.6 * inch, band_h - 0.85 * inch, "MITRE to Detection Copilot · 4-Agent Purple Team Pipeline · vLLM on ROCm · AMD MI300X")
    c.setFillColor(FG_DIM)
    c.setFont(REGULAR, 10)
    c.drawString(0.6 * inch, 0.35 * inch, "AMD Developer Hackathon 2026  ·  Track 1: AI Agents & Agentic Workflows")
    c.drawRightString(PAGE_W - 0.6 * inch, 0.35 * inch, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    c.drawRightString(PAGE_W - 0.6 * inch, band_h - 0.85 * inch, f"{slide_no:02d} / {total:02d}")


def _slide_problem(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Problem")
    y = _draw_title(c, "the gap", "Threat intel doesn't become detection fast enough.", RED)
    y = _draw_paragraph(c, 0.55 * inch, y, PAGE_W - 1.1 * inch,
        "Security teams have more MITRE ATT&CK intel than they can operationalize. "
        "Converting a technique into precise SIEM/EDR detection logic + response playbooks "
        "needs rare dual offensive/defensive expertise.", size=12)
    y -= 0.25 * inch
    _draw_bullets(c, 0.7 * inch, y, PAGE_W - 1.4 * inch, [
        "A typical purple-team engagement: $20,000-$50,000 and 2-3 weeks per scenario.",
        "Sensitive infrastructure data cannot be sent to cloud AI APIs.",
        "Generic threat intel produces generic, low-precision detection rules.",
        "Blue teams don't see how red teams actually execute techniques in the wild.",
    ], size=12, accent=RED)


def _slide_solution(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Solution")
    y = _draw_title(c, "aegisops ai", "High-fidelity simulation -> high-precision defense.", GREEN)
    y = _draw_paragraph(c, 0.55 * inch, y, PAGE_W - 1.1 * inch,
        "AegisOps AI is a 4-agent purple-team copilot. Drop in a MITRE ATT&CK technique ID "
        "(or APT group, kill chain, or sandbox topology) and get back observables, Sigma rules, "
        "realtime SIEM/EDR alert logic, and a SOC response playbook in minutes.", size=12)
    y -= 0.2 * inch
    # Pipeline cards row
    card_w = (PAGE_W - 1.5 * inch) / 4
    card_h = 1.6 * inch
    cy = 1.0 * inch
    cards = [
        ("Red / Threat", "Authorized high-fidelity simulation, observables, telemetry, exploit code patterns.", RED),
        ("Detection / Blue", "Sigma rule + Real-Time Detection Plan grounded in the exact red artifacts.", BLUE),
        ("Response", "Triage, containment, hunt, mitigation, escalation, reporting - mapped to telemetry.", GREEN),
        ("Validation", "Coverage score, covered/missing observables, scope check, improvement suggestions.", PURPLE),
    ]
    for i, (title, desc, color) in enumerate(cards):
        x = 0.55 * inch + i * (card_w + 0.12 * inch)
        _draw_card(c, x, cy, card_w, card_h, title, [], accent=color)
        # body
        body_w = card_w - 0.36 * inch
        _draw_paragraph(c, x + 0.18 * inch, cy + card_h - 0.55 * inch, body_w, desc, size=10)


def _slide_architecture(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Architecture")
    y = _draw_title(c, "stack", "LangGraph 4-agent state machine on vLLM + ROCm + MI300X.", BLUE)
    y -= 0.05 * inch
    # Two-column: left text, right ascii-style stack
    text_x = 0.55 * inch
    text_w = (PAGE_W - 1.1 * inch) * 0.5 - 0.2 * inch
    y2 = _draw_bullets(c, text_x, y, text_w, [
        "Streamlit UI with 4 modes: Single Technique, APT Group, Kill Chain, Topology Lab.",
        "LangGraph: stateful directed pipeline (Red -> Blue -> Response -> Validation).",
        "MITRE ATT&CK v14 enterprise-attack.json shipped locally - no external API call for threat intel.",
        "OpenAI-compatible client -> vLLM OpenAI server -> ROCm container -> AMD Instinct MI300X.",
        "Per-agent latency + token usage instrumented and rendered live in the UI.",
    ], size=11, accent=BLUE)

    # Right: stack visual
    sx = text_x + text_w + 0.4 * inch
    sw = (PAGE_W - 1.1 * inch) * 0.5 - 0.2 * inch
    layers = [
        ("Streamlit UI", FG, "#0E1223"),
        ("LangGraph 4-agent pipeline", PURPLE, "#1A1230"),
        ("ChatOpenAI (langchain-openai)", BLUE, "#0F1B30"),
        ("vLLM OpenAI API server", AMBER, "#2A1A0A"),
        ("ROCm container (AMD)", RED, "#2A0F0F"),
        ("AMD Instinct MI300X (192GB HBM3)", GREEN, "#0F2A18"),
    ]
    layer_h = 0.45 * inch
    sy = PAGE_H - 1.9 * inch
    for label, fg, bg_hex in layers:
        c.setFillColor(HexColor(bg_hex))
        c.setStrokeColor(fg)
        c.roundRect(sx, sy, sw, layer_h, 5, fill=1, stroke=1)
        c.setFillColor(fg)
        c.setFont(BOLD, 11)
        c.drawString(sx + 0.15 * inch, sy + layer_h / 2 - 4, label)
        sy -= layer_h + 0.08 * inch


def _slide_amd_proof(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "AMD MI300X · ROCm Proof")
    y = _draw_title(c, "verifiable amd evidence", "Live vLLM on ROCm. Every claim is in the repo.", AMBER)
    bench_path = ASSETS / "rocm_benchmark.json"
    smi_path = ASSETS / "rocm_smi.json"
    bench_lines = ["Benchmark not captured yet - run scripts/rocm_benchmark.py on the MI300X."]
    if bench_path.exists():
        try:
            data = json.loads(bench_path.read_text())
            bench_lines = [
                f"endpoint: {data.get('endpoint','-')}",
                f"model:    {data.get('model','-')}",
                f"runtime:  {data.get('runtime','-')}",
                f"gpu:      {data.get('gpu','-')}",
                f"requests: {data.get('successful',0)}/{data.get('requests',0)} (concurrency {data.get('concurrency','-')})",
                f"p50:      {data.get('latency_ms_p50','-')} ms   p95: {data.get('latency_ms_p95','-')} ms",
                f"throughput: {data.get('tokens_per_second','-')} tokens/sec",
                f"captured: {data.get('captured_at','-')}",
            ]
        except Exception:
            pass
    smi_state = "captured" if smi_path.exists() else "pending - run start_vllm.sh on the MI300X"

    _draw_card(c, 0.55 * inch, 1.0 * inch, (PAGE_W - 1.4 * inch) / 2, 4.4 * inch,
               "rocm_benchmark.json (live)", bench_lines, accent=AMBER)
    _draw_card(c, 0.55 * inch + (PAGE_W - 1.4 * inch) / 2 + 0.3 * inch, 1.0 * inch,
               (PAGE_W - 1.4 * inch) / 2, 4.4 * inch,
               "rocm_smi.json + vllm_info.txt",
               [
                   f"rocm_smi.json: {smi_state}",
                   "Captured by ./start_vllm.sh from the live ROCm container",
                   "vllm_info.txt: vLLM version, model id, endpoint, capture timestamp",
                   "All files committed in /assets/ for reproducible judging",
                   "Streamlit UI links to these files from the ROCm Live panel",
               ], accent=GREEN)


def _slide_demo_flow(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Demo Flow")
    y = _draw_title(c, "live demo arc - under 5 minutes", "Realistic ATT&CK behavior becomes precise detection.", CYAN)
    _draw_bullets(c, 0.7 * inch, y, PAGE_W - 1.4 * inch, [
        "Open AegisOps AI. Top panel shows LIVE - vLLM on ROCm | MI300X with /v1/models latency.",
        "Run Single Technique with T1059.001 (PowerShell). Show per-agent latency + token cards.",
        "Inspect Red/Threat output: simulation phases, exploit code section, observables, telemetry.",
        "Inspect Detection output: Sigma YAML + Real-Time Detection Plan grounded in those observables.",
        "Inspect Response + Validation: triage, containment, coverage score, covered/missing observables.",
        "Switch to Topology Lab: 9-node sandbox, 3 lateral-movement paths, hop-by-hop reaction time.",
    ], size=12, accent=CYAN)


def _slide_business_value(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Business Value")
    y = _draw_title(c, "market & roi", "Replace 2-3 weeks of purple-team work with minutes of inference.", GREEN)
    # Two-column grid of cards
    cw = (PAGE_W - 1.4 * inch) / 2
    ch = 1.7 * inch
    gap = 0.2 * inch
    # left col
    _draw_card(c, 0.55 * inch, PAGE_H - 4.0 * inch, cw, ch,
               "ROI per scenario",
               [
                   "Today: $20,000-$50,000 / 2-3 weeks / 2-3 senior consultants",
                   "AegisOps AI: minutes per technique, one operator, no cloud dependency",
                   "Each Sigma rule + response playbook is exportable to PDF for SOC handoff",
               ], accent=GREEN)
    _draw_card(c, 0.55 * inch + cw + gap, PAGE_H - 4.0 * inch, cw, ch,
               "Revenue model",
               [
                   "SaaS: $500-$2,000 / month per SOC team",
                   "On-prem AMD GPU deployment for data-sovereignty buyers (banks, gov, MSSP)",
                   "Add-on: detection-pack subscription per ATT&CK update wave",
               ], accent=PURPLE)
    _draw_card(c, 0.55 * inch, PAGE_H - 4.0 * inch - ch - gap, cw, ch,
               "Market & TAM",
               [
                   "Penetration testing: $1.7B (2023), growing 13% annually",
                   "Purple teaming = fastest-growing segment (continuous validation)",
                   "TAM (MSSPs + Enterprise SOC needing on-prem AI): ~$340M",
               ], accent=AMBER)
    _draw_card(c, 0.55 * inch + cw + gap, PAGE_H - 4.0 * inch - ch - gap, cw, ch,
               "Customers",
               [
                   "MSSPs running purple-team exercises across many clients",
                   "Enterprise SOC teams without dual red/blue expertise",
                   "Detection engineering teams automating Sigma generation",
                   "Red-team consultancies productizing repeatable reports",
               ], accent=BLUE)


def _slide_originality(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Originality")
    y = _draw_title(c, "what makes this different", "Not a chatbot. Not a wrapper. A purple-team workflow engine.", PURPLE)
    _draw_bullets(c, 0.7 * inch, y, PAGE_W - 1.4 * inch, [
        "4-agent stateful pipeline (Red -> Blue -> Response -> Validation) with structured outputs at every hop.",
        "Topology Lab: sandbox lateral-movement visualization mapped hop-by-hop to detection + reaction time.",
        "Realtime Detection Plan: each technique produces streaming SIEM/EDR alert logic, not just a static rule.",
        "On-prem AMD/ROCm path: sensitive infra context never leaves operator-controlled MI300X.",
        "Validation Agent enforces scope: zero-day generation explicitly OUT, known ATT&CK behavior IN.",
        "Per-agent live latency + token observability surfaced directly in the UI - judges see ROCm working.",
    ], size=12, accent=PURPLE)


def _slide_safety(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Safety & Scope")
    y = _draw_title(c, "responsible offensive ai", "High fidelity, professionally bounded.", AMBER)
    cw = (PAGE_W - 1.4 * inch) / 2
    ch = 3.2 * inch
    _draw_card(c, 0.55 * inch, 1.0 * inch, cw, ch,
               "In scope",
               [
                   "Known MITRE ATT&CK behavior simulation",
                   "Detection-useful command patterns with placeholders",
                   "Sigma + Real-Time Detection Plans",
                   "Response, hunt, containment guidance",
                   "Validation scoring + coverage analysis",
               ], accent=GREEN)
    _draw_card(c, 0.55 * inch + cw + 0.3 * inch, 1.0 * inch, cw, ch,
               "Out of scope",
               [
                   "Zero-day exploit generation",
                   "Novel malware authoring",
                   "Real target exploitation instructions",
                   "Unbounded offensive automation",
                   "Live engagement against unauthorized targets",
               ], accent=RED)


def _slide_roadmap(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Roadmap")
    y = _draw_title(c, "next 90 days", "From hackathon prototype to MSSP-ready product.", BLUE)
    _draw_bullets(c, 0.7 * inch, y, PAGE_W - 1.4 * inch, [
        "Multi-model routing on AMD - Qwen for reasoning, Llama for generation, served from one ROCm host.",
        "Direct Sigma deployment to Splunk, Elastic, Microsoft Sentinel.",
        "Domain fine-tuned detection model trained on MITRE + Sigma corpus on MI300X.",
        "SOC handoff bundle: ZIP of Sigma rules, MITRE CSV, executive summary, PDF report.",
        "ATT&CK coverage heatmap visualizing tactic/technique gaps across customer estate.",
        "Continuous validation runner: scheduled re-runs as ATT&CK and detection rules drift.",
    ], size=12, accent=BLUE)


def _slide_ask(c: canvas.Canvas, slide_no: int, total: int) -> None:
    _draw_background(c)
    _draw_chrome(c, slide_no, total, "Ask")
    y = _draw_title(c, "judging axes", "Built to score 5/5 on every criterion.", PURPLE)
    cw = (PAGE_W - 1.5 * inch) / 4
    ch = 2.4 * inch
    cy = PAGE_H - 4.5 * inch
    cards = [
        ("Presentation", ["Cover image (16:9)", "Slide deck PDF (this)", "Sub-5-min video script", "Live demo URL"]),
        ("Business Value", ["$1.7B market, 13% CAGR", "Clear SaaS + on-prem revenue", "MSSP + Enterprise SOC ICP", "Replaces $20-50K work"]),
        ("Application of Tech", ["Live vLLM on ROCm MI300X", "rocm-smi + benchmark JSON", "Per-agent latency in UI", "LangGraph + Llama 3.3 70B"]),
        ("Originality", ["4-agent purple-team flow", "Topology Lab visualization", "Realtime Detection Plan", "On-prem AMD/ROCm story"]),
    ]
    accents = [CYAN, GREEN, AMBER, PURPLE]
    for i, ((title, lines), accent) in enumerate(zip(cards, accents)):
        x = 0.55 * inch + i * (cw + 0.12 * inch)
        _draw_card(c, x, cy, cw, ch, title, lines, accent=accent)
    # Bottom CTA
    c.setFillColor(FG)
    c.setFont(BOLD, 14)
    c.drawCentredString(PAGE_W / 2, 0.85 * inch, "Try it live - link in submission · github.com/ztothez/aegisops-ai")


def build() -> Path:
    DOCS.mkdir(parents=True, exist_ok=True)
    slides = [
        _slide_cover,
        _slide_problem,
        _slide_solution,
        _slide_architecture,
        _slide_amd_proof,
        _slide_demo_flow,
        _slide_business_value,
        _slide_originality,
        _slide_safety,
        _slide_roadmap,
        _slide_ask,
    ]
    total = len(slides)
    c = canvas.Canvas(str(OUTPUT), pagesize=(PAGE_W, PAGE_H))
    c.setTitle("AegisOps AI - AMD Developer Hackathon 2026")
    c.setAuthor("AegisOps AI")
    c.setSubject("Multi-agent purple-team copilot on AMD MI300X via vLLM + ROCm")
    for i, slide in enumerate(slides, start=1):
        slide(c, i, total)
        c.showPage()
    c.save()
    print(f"Wrote {OUTPUT}  ({total} slides, 16:9)")
    return OUTPUT


if __name__ == "__main__":
    build()
