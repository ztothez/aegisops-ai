---
title: AegisOps AI
emoji: 🛡️
colorFrom: indigo
colorTo: red
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AegisOps AI
### MITRE to Detection Copilot

> **Generic threat intelligence produces generic detections. High-fidelity known ATT&CK simulation produces precise observables, realtime detection logic, and response guidance.**

AegisOps AI is a multi-agent AI system that transforms MITRE ATT&CK techniques and known adversary behavior into production-ready defensive artifacts — Sigma detection rules, realtime SIEM/EDR alert logic, SOC response guidance, and validation scores. The public Space runs in reliable Demo Mode; the live inference path is designed for AMD Developer Cloud using vLLM on ROCm.

[![Live Demo](https://img.shields.io/badge/Live%20Demo-HuggingFace-orange)](https://huggingface.co/spaces/ztothez/aegisops-ai)
[![AMD MI300X](https://img.shields.io/badge/AMD-MI300X-red)](https://www.amd.com)
[![ROCm](https://img.shields.io/badge/ROCm-vLLM-red)](https://rocm.docs.amd.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-blue)](https://langchain-ai.github.io/langgraph/)
[![MITRE ATT&CK](https://img.shields.io/badge/MITRE-ATT%26CK%20v14-green)](https://attack.mitre.org/)

![AegisOps AI cover](assets/cover.png)

---

## The Problem

Security teams face a critical gap: converting threat intelligence into actionable detections is slow, expensive, and requires rare dual expertise in both offensive and defensive security.

- A typical purple team engagement costs **$20,000–$50,000** and takes **2–3 weeks**
- Cloud AI cannot be used — sensitive infrastructure data cannot leave the machine
- Generic threat intel produces generic, low-precision detection rules
- Blue teams don't know how red teams actually execute techniques

**Result:** Most organizations have incomplete detection coverage against known adversary behavior.

---

## The Solution

AegisOps AI runs a **4-agent pipeline** that takes a MITRE ATT&CK technique ID and produces a complete defensive readiness package — in minutes, not weeks. In Demo Mode, precomputed artifacts make judging reliable; in live mode, the same pipeline calls an OpenAI-compatible vLLM endpoint designed to run on AMD Developer Cloud with ROCm.

```
User Input (MITRE Technique ID or APT Group)
        ↓
Red/Threat Agent       → High-fidelity authorized simulation artifacts
        ↓
Detection Agent        → Sigma rules targeting exact observables
        ↓
Response Agent         → SOC triage, containment, and escalation guidance
        ↓
Validation Agent       → Coverage score, gaps, and quality check
        ↓
Final Output           → UI + JSON + PDF report
```

**Core insight:** High-fidelity simulation enables high-precision defense. The Detection Agent consumes the exact command patterns, process lineage, event IDs, file paths, registry keys, and network indicators from the Threat Agent — producing detection rules that match real attacker behavior, not generic patterns.

---

## Key Features

### 4 Simulation Modes

**Single Technique**
Enter any MITRE ATT&CK technique ID (e.g. T1059.001). The 4-agent pipeline produces:
- Authorized purple-team simulation with representative command patterns
- Process lineage, event IDs, file/registry/network indicators
- Sigma-style detection rule targeting exact observables
- Realtime SIEM/EDR streaming alert logic
- SOC response guidance: triage, containment, hunting, escalation
- Validation score with coverage percentage and gap analysis

**APT Group Mode**
Enter a threat actor name (e.g. APT28, Lazarus, Cozy Bear). The system:
- Fetches all techniques attributed to that group from MITRE ATT&CK v14
- Runs the full 4-agent pipeline for each technique sequentially
- Produces a complete adversary profile with multi-technique detection coverage
- Exports a combined PDF report for SOC handoff

**Kill Chain Mode**
Enter a starting technique and the system automatically chains subsequent techniques:
- T1566.001 → T1204.002 → T1059.001 (Phishing → User Execution → PowerShell)
- Each hop runs the full 4-agent pipeline
- Visual chain flow showing the complete attack sequence
- Combined detection and response guidance across the full chain

**Hunting — Topology Lab**
Visual sandbox environment showing how lateral movement becomes realtime detection:
- 7-node sandbox network topology
- 3 selectable attack paths:
  - Phishing to PowerShell to C2
  - Valid Account to Domain Credential Access
  - Public App Exploit to Web Shell to Exfiltration
- Hop-by-hop telemetry mapping with reaction time estimates (~15s avg)
- Streaming SIEM/EDR alert conditions for each hop
- 100% detection coverage across mapped paths

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   AegisOps AI                       │
│                                                     │
│  ┌──────────────┐    ┌──────────────────────────┐   │
│  │  FastAPI +   │    │                          │   │
│  │ HuggingFace  │    │  LangGraph Graph         │   │
│  │   Spaces     │───▶│                          │   │
│  │  SOC Console │    │  Red/Threat Agent        │   │
│  │   4 Modes    │    │       ↓                  │   │
│  └──────────────┘    │  Detection/Blue Agent    │   │
│                      │       ↓                  │   │
│  ┌──────────────┐    │  Response Agent          │   │
│  │ MITRE ATT&CK │    │       ↓                  │   │
│  │  v14 Local   │───▶│  Validation Agent        │   │
│  │  enterprise- │    │  (Qwen verifier sidecar) │   │
│  │  attack.json │    └──────────────────────────┘   │
│  └──────────────┘                ↓                  │
│                      ┌──────────────────────────┐   │
│                      │   vLLM + ROCm            │   │
│                      │   AMD MI300X (192GB)     │   │
│                      │   Llama 3.3 70B          │   │
│                      └──────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

**Agent Roles:**

| Agent | Input | Output |
|-------|-------|--------|
| Red/Threat Agent | Technique ID + MITRE context | Simulation artifacts, observables, telemetry |
| Detection Agent | Red Agent output | Sigma rule, realtime alert logic |
| Response Agent | Detection output | SOC triage, containment, hunting, escalation |
| Validation Agent | Red + Detection output | Six-dimension coverage score, PASS/WARN/FAIL |

---

## Why AMD + Local Inference

Security teams cannot send sensitive infrastructure data to cloud AI APIs. Internal network topology, real CVE contexts, and active incident data are too sensitive for external exposure.

**Why AMD Developer Cloud + ROCm matters for the live path:**
- MI300X-class memory is suitable for serving large open-source models such as Llama 70B.
- vLLM on ROCm provides an OpenAI-compatible API for the LangGraph agent pipeline.
- AMD Developer Cloud enables a private inference endpoint for security-sensitive SOC workflows.
- The architecture is designed so sensitive topology and incident context can stay inside the operator-controlled environment.

### ROCm Utilization (verifiable, not hand-waved)

AegisOps AI uses ROCm as the AMD GPU runtime layer for live inference:

```
FastAPI + HuggingFace Spaces UI
  → LangGraph agent pipeline
  → ChatOpenAI-compatible client
  → vLLM OpenAI API server
  → ROCm container
  → AMD Instinct MI300X
```

The SOC Console UI surfaces real ROCm proof at the top of every pipeline run:

- A live `/v1/models` health probe with measured latency (green `LIVE` pill when reachable).
- Per-agent latency and prompt/completion token counts for every Threat → Detection → Response → Validation hop.
- Direct links to the bundled evidence files captured from the live MI300X.

Reproduce the evidence on AMD Developer Cloud:

```bash
# Brings up vLLM on the MI300X, captures rocm-smi + vllm version into ./assets/
./start_vllm.sh <droplet-ip> <hf-token>

# Records p50 / p95 latency and tokens-per-second from real concurrent requests
python scripts/rocm_benchmark.py --requests 12 --concurrency 4
```

Evidence files committed to the repo:

- [`assets/rocm_smi.json`](assets/rocm_smi.json) — machine-readable ROCm GPU snapshot
- [`assets/rocm_smi.txt`](assets/rocm_smi.txt) — human-readable `rocm-smi` snapshot
- [`assets/vllm_info.txt`](assets/vllm_info.txt) — vLLM version, model, endpoint, capture timestamp
- [`assets/rocm_benchmark.json`](assets/rocm_benchmark.json) — p50: 4723ms, p95: 4892ms, throughput: 89.09 tok/s
- [`assets/README.md`](assets/README.md) — full description of every evidence file

Demo Mode remains available on Hugging Face Spaces for reliable public judging when the AMD/vLLM secrets are not configured. The UI still surfaces the bundled ROCm evidence in Demo Mode, so judges always see the AMD provenance.

---

## Tech Stack

| Component | Technology | Why |
|-----------|-----------|-----|
| Agent Orchestration | LangGraph | Stateful multi-agent graph with sequential execution |
| Inference | vLLM on ROCm | Live AMD endpoint with OpenAI-compatible API |
| Model | Llama 3.3 70B + Qwen2.5-3B | Generation + verifier sidecar, well-documented on ROCm |
| GPU | AMD Instinct MI300X | Live inference hardware on AMD Developer Cloud |
| Threat Intel | MITRE ATT&CK v14 | Local enterprise-attack.json, no external API calls |
| Frontend | FastAPI + HuggingFace Spaces | SOC Console UI, Docker deployment |
| Export | ReportLab | PDF report generation for SOC handoff |

---

## Business Value

**Target customers:**
- MSSPs — run purple team exercises for clients at scale
- Enterprise SOC teams — continuous detection validation without dual red/blue expertise
- Detection Engineering teams — automate Sigma rule generation from threat intelligence
- Red team consultancies — generate professional reports automatically

**ROI:**
- Typical purple team engagement: $20,000–$50,000, 2–3 weeks, 2–3 senior consultants
- AegisOps AI: minutes per technique, one operator, no cloud dependency

**Revenue model:**
- SaaS: $500–2,000/month per SOC team
- On-premise AMD GPU deployment for enterprise data sovereignty requirements

**Market:**
- Global penetration testing market: $1.7B (2023), growing 13% annually
- Purple teaming is the fastest growing segment as organizations move to continuous security validation
- TAM: $340M (MSSPs + Enterprise SOC teams requiring on-premise AI)

---

## Safety and Scope

AegisOps AI operates within a clearly defined scope:

**In scope:**
- Known MITRE ATT&CK behavior simulation
- Detection-useful command patterns with placeholders
- Layered Sigma/SIEM detection logic
- Response and containment guidance
- Six-dimension validation scoring

**Out of scope:**
- Zero-day exploit generation
- Novel malware creation
- Real target exploitation instructions
- Unbounded offensive automation

All simulation artifacts use professional placeholders (`<DOMAIN>`, `<HOST>`, `<BASE64_PLACEHOLDER>`) and are framed as authorized purple-team validation artifacts.

---

## Quickstart

### Requirements
- Python 3.10+
- Docker
- AMD Developer Cloud account with MI300X access (or Together.ai for testing)
- HuggingFace token with Llama 3.3 70B access

### Local Development

```bash
git clone https://github.com/ztothez/aegisops-ai
cd aegisops-ai
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### Configure `.env`

```env
VLLM_BASE_URL=http://your-amd-instance-ip:8000/v1
VLLM_API_KEY=your_key
MODEL_NAME=meta-llama/Llama-3.3-70B-Instruct
```

### Run locally (FastAPI + uvicorn)

```bash
uvicorn app:app --host 0.0.0.0 --port 7860 --reload
```

### Run with Docker

```bash
docker build -t aegisops-ai .
docker run -p 7860:7860 --env-file .env aegisops-ai
```

### AMD/ROCm live inference path

```bash
# After creating an MI300X instance with a ROCm/vLLM image
./start_vllm.sh <droplet-ip> <hf-token>
```

The startup script:
1. Opens port `8000`
2. Verifies ROCm GPU access with `rocm-smi`
3. Starts vLLM inside the ROCm container
4. Updates `.env` with the AMD Developer Cloud endpoint

### Demo mode (no GPU required)

When `VLLM_BASE_URL` is not configured, the app runs in Demo Mode using precomputed artifacts. On Hugging Face Spaces, Demo Mode is the default public path. AMD provenance is preserved through the bundled evidence files in `assets/`.

---

## Demo Flow

1. Open AegisOps AI. System status shows either `LIVE - vLLM on ROCm | MI300X | Llama-3.3-70B-Instruct` (green) or `OFFLINE - DEMO FALLBACK ACTIVE` (amber) with bundled AMD evidence.
2. Run **Single Technique** with `T1059.001`. Live monitor streams agent events. Per-agent latency cards render on completion.
3. Check **Alerts** — Red Team / Blue Team side-by-side: Office-lineage simulation on the left, layered detection strategy on the right.
4. Check **Cases** — SOC Response Guidance and Pipeline Validation JSON with six-dimension scores.
5. Check **Reports** — Coverage 97%, Verdict PASS, Safety PASS, Audited by Qwen Validator. Download PDF.
6. Check **Exports** — Sigma YAML, Splunk SPL, SOC Playbook, VECTR JSON, Validation JSON, PDF bundle.
7. Switch to **Hunting** — Topology Lab: 7 nodes, 3 hops, 100% detection coverage, ~15s avg reaction.

Total run time: under 5 minutes.

---

## Submission Assets

- **Cover image (16:9)**: [`assets/cover.png`](assets/cover.png)
- **Slide deck PDF**: [`docs/AegisOps_AI_Slides.pdf`](docs/AegisOps_AI_Slides.pdf)
- **Video script**: [`docs/video_script.md`](docs/video_script.md)
- **Submission form copy**: [`SUBMISSION.md`](SUBMISSION.md)
- **Public GitHub repo**: https://github.com/ztothez/aegisops-ai
- **Live demo**: https://huggingface.co/spaces/ztothez/aegisops-ai

---

## Roadmap

- **SIEM integration** — Direct Sigma rule deployment to Splunk/Elastic/Sentinel
- **EDR connector** — CrowdStrike, Defender for Endpoint
- **Sample-log testing** — Validate detections against synthetic log fixtures
- **Fine-tuned detection model** — Domain-specific model trained on MITRE + Sigma corpus on AMD GPU
- **ATT&CK coverage heatmap** — Visual coverage dashboard by tactic/technique
- **Continuous validation** — Scheduled re-runs as ATT&CK knowledge base updates
- **APT Group simulation mode** — Full adversary profile with multi-technique detection coverage

---

## Track

**AMD Developer Hackathon 2026 — AI Agents & Agentic Workflows**

AegisOps AI demonstrates sophisticated agentic behavior: 4 coordinated LangGraph agents with stateful sequential passing, tool use (MITRE ATT&CK v14 local dataset), structured output validation, and multi-mode orchestration. The public demo is hosted on Hugging Face Spaces; the live inference path runs on AMD Instinct MI300X via vLLM on ROCm using AMD Developer Cloud, with reproducible evidence captured into [`assets/`](assets/) by [`start_vllm.sh`](start_vllm.sh) and [`scripts/rocm_benchmark.py`](scripts/rocm_benchmark.py).