# AegisOps AI - lablab.ai Submission Form

This file is the source of truth for the lablab.ai hackathon submission form.
Copy each section into the matching field on the submission page.

---

## Project Title

AegisOps AI - MITRE to Detection Copilot

## Short Description

AegisOps AI is a 4-agent purple-team system that turns known MITRE ATT&CK behavior into Sigma-style detections, SOC response guidance, and validation coverage using LangGraph, vLLM, ROCm, and AMD MI300X.

## Long Description

Security teams have more MITRE ATT&CK threat intelligence than they can operationalize into high-quality detections. ATT&CK documents adversary behavior, but translating techniques into observable telemetry, Sigma-style detection logic, SOC response guidance, and validation checks is still mostly manual. This creates generic rules, noisy alerts, missed coverage, and a bottleneck around scarce detection engineering expertise.

**AegisOps AI** is a 4-agent purple-team detection engineering system that closes that gap. A user can enter a MITRE ATT&CK technique ID, APT group, kill chain, or sandbox topology, and a LangGraph state machine runs four specialized agents end to end:

1. **Threat / Red Agent** - creates high-fidelity authorized simulation artifacts for known ATT&CK behavior, including phases, detection-useful command patterns, observables, telemetry, and process behavior.
2. **Detection / Blue Agent** - converts those exact observables into Sigma-style detection logic, field mappings, Event IDs, and realtime SIEM/EDR detection plans.
3. **Response Agent** - generates triage, containment, hunting, mitigation, escalation, and reporting actions tied to the detected telemetry.
4. **Validation Agent** - checks coverage, identifies covered and missing observables, validates structure, and keeps the scope bounded to known ATT&CK behavior.

The live inference path is designed for AMD Instinct MI300X using vLLM in a ROCm container on AMD Developer Cloud. The Streamlit UI includes an AMD/ROCm proof panel showing endpoint health, model status, latency, throughput/benchmark output, and downloadable evidence artifacts such as `rocm_smi.json`, `vllm_info.txt`, and `rocm_benchmark.json`.

**Why it matters:** generic threat intelligence produces generic detections. AegisOps AI uses high-fidelity known ATT&CK behavior as precision input, then turns it into field-mapped detections, response guidance, and validation coverage. The result is a repeatable workflow that helps SOC analysts, detection engineers, threat hunters, MDR/MSSP providers, and purple-team consultants move from threat knowledge to defensive readiness faster.

Current modes include:

- **Single Technique** - full 4-agent run for a MITRE ATT&CK technique such as T1059.001 PowerShell.
- **APT Group** - campaign-style workflow for threat actor behavior.
- **Kill Chain** - chained techniques across multiple stages.
- **Topology Lab** - sandbox network path with hop-by-hop telemetry, detection, response, and reaction timing.

AegisOps AI is not a generic chatbot and not an exploit generator. It is a purple-team detection workflow engine: known attacker behavior becomes validated defensive readiness.

## Cover Image

`assets/cover.png` - 1820 x 1024, 16:9, PNG.

## Video

- Format: MP4, 1920 x 1080, 30 fps, under 5 minutes.
- Script: [`docs/video_script.md`](docs/video_script.md).
- Hosting: upload to YouTube unlisted or directly to lablab.ai.
- Final URL: `<paste after recording>`

## Slide Presentation PDF

[`docs/AegisOps_AI_Slides.pdf`](docs/AegisOps_AI_Slides.pdf) - 14 slides, 16:9.

## Public GitHub Repository

https://github.com/ztothez/aegisops-ai

## Application URL

https://huggingface.co/spaces/ztothez/aegisops-ai

The Hugging Face Space runs in Demo Mode for reliable judging. The live AMD MI300X / ROCm vLLM endpoint can be connected by setting `VLLM_BASE_URL`, `VLLM_API_KEY`, and `MODEL_NAME` as Space secrets. When configured, the UI changes from amber DEMO mode to green LIVE endpoint mode.

## Track

AI Agents & Agentic Workflows

## Technology Tags

LangChain, LLaMA, AMD ROCm, Streamlit, AMD Developer Cloud, HuggingFace Spaces, HuggingFace Hub

Additional technologies used in the implementation:
LangGraph, vLLM, AMD Instinct MI300X, MITRE ATT&CK v14, Sigma-style rules, Python, JSON/PDF reports.

## Category Tags

Cybersecurity, AI Agents, Security Operations, Detection Engineering, Threat Intelligence, Purple Teaming, Multi-Agent Systems.

## Team

Team: ZtotheZ  
Builder: Roosa Yöruusu  
Username: ztothez

---

## Judging Criteria Mapping

### Presentation

- 16:9 cover image: `assets/cover.png`.
- Slide PDF: `docs/AegisOps_AI_Slides.pdf`.
- Video script targets under 5 minutes.
- The deck covers problem, solution, architecture, AMD/ROCm proof, demo flow, business value, originality, responsible scope, and roadmap.

### Business Value

- Addresses the detection engineering bottleneck in SOC teams, MDR/MSSP providers, purple-team consultancies, and public-sector security teams.
- Helps turn scarce detection engineering expertise into a repeatable AI-assisted workflow.
- Potential revenue models include SaaS subscriptions, team/seat licensing, enterprise on-prem deployment, MDR/MSSP white-label licensing, per-report consultant workflows, and SIEM/EDR integration marketplace.
- Strong fit for teams that need ATT&CK-aligned detection coverage but cannot send sensitive infrastructure context to generic cloud copilots.

### Application of Technology

- Streamlit product UI with multiple demo modes.
- LangGraph-style 4-agent pipeline: Threat → Detection → Response → Validation.
- vLLM inference path on ROCm / AMD MI300X.
- Local MITRE ATT&CK v14 enterprise dataset.
- Sigma-style detection output and structured JSON/PDF reports.
- AMD evidence artifacts: `rocm_smi.json`, `vllm_info.txt`, and `rocm_benchmark.json`.
- UI surfaces endpoint health, model status, latency, and benchmark/proof artifacts.

### Originality

- Purpose-built ATT&CK-to-detection workflow, not a generic chatbot.
- High-fidelity known ATT&CK simulation is used as precision input for defensive detection engineering.
- Validation Agent checks coverage and gaps rather than only generating text.
- Topology Lab maps sandbox attack paths into telemetry, detection conditions, and response timing.
- On-prem AMD/ROCm path supports security-sensitive SOC inference workflows.