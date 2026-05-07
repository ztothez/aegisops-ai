# AegisOps AI — Video Script (4 min 30 s target, hard cap 5 min)

This script is a one-take, scene-by-scene shot list with on-screen action and narration. It is optimized for the lablab.ai presentation rubric: problem, solution, value, originality, AMD usage, and live proof in under 5 minutes.

Recording recipe:
- Resolution: 1920x1080, 30 fps, MP4 (H.264).
- Capture the full browser tab in the live Streamlit app.
- Use a single voice-over track recorded after screen capture.
- Tools: OBS or QuickTime + Audacity for VO; DaVinci Resolve / iMovie for cuts.
- Keep B-roll minimal; use hard cuts, no transitions.
- Do not show terminal history or any Hugging Face token.

Total target: 4:30. Buffer: 0:30 for breath room.

---

## 00:00 - 00:25 — Cold open: the gap

On screen:
- AegisOps AI cover image.
- Cut to the problem/value slide.

Narration:
> "Security teams have more MITRE ATT&CK threat intel than they can realistically turn into detection. A single purple-team engagement can cost tens of thousands of dollars and take weeks. And cloud copilots are not always an option when the context is sensitive. AegisOps AI fixes that."

---

## 00:25 - 00:55 — Solution

On screen:
- Cut to the live Streamlit app.
- Show the top banner: LIVE vLLM on ROCm / MI300X / model name.
- Hover or pause over the green live badge and `/v1/models` latency.

Narration:
> "AegisOps AI is a four-agent purple-team copilot. You give it a MITRE ATT&CK technique, and a Threat agent, Detection agent, Response agent, and Validation agent run as a LangGraph workflow. Right now, the app is connected to a live vLLM endpoint running on ROCm on AMD hardware. Every inference in this demo runs through that endpoint."

---

## 00:55 - 02:15 — Single technique demo: T1059.001 PowerShell

On screen:
1. Click Single Technique mode.
2. Type `T1059.001`.
3. Press Run Simulation.
4. As output streams in, scroll past the per-agent latency and token cards.
5. Show the Observables card.
6. Show the Detection / Sigma YAML.
7. Show the Response Guidance.
8. Show the Real-Time Detection card.
9. Show the Validation panel with coverage score, covered observables, and missing observables.

Narration:
> "Let's run technique T1059.001 — PowerShell. The Threat agent simulates attacker behavior in defensive terms and emits structured observables, telemetry, and suspicious command patterns. The Detection agent consumes those artifacts and produces a Sigma rule plus a real-time detection plan for SIEM and EDR alerting. The Response agent generates triage, containment, hunting, and escalation steps. Finally, the Validation agent scores coverage and flags missing observables. The per-agent latency and token cards show this is live inference, not a static mockup. This is the core idea: high-fidelity simulation producing high-precision defense."

---

## 02:15 - 03:00 — Topology Lab: originality

On screen:
1. Click Topology Lab mode.
2. Pick the second attack path from the dropdown.
3. Pan across the sandbox topology.
4. Scroll through hop cards showing telemetry, SIEM detection, SOC response, and reaction time.

Narration:
> "This is the Topology Lab. Instead of only generating text, AegisOps AI renders a sandbox network and walks a lateral-movement path hop by hop. Each hop is mapped to telemetry, detection logic, response action, and reaction time. This is what makes it more than a chatbot: it is a workflow engine that turns ATT&CK behavior into measurable defensive coverage."

---

## 03:00 - 03:35 — AMD MI300X / ROCm proof shot

On screen:
1. Open a terminal pane next to the browser.
2. Run:

```bash
cat assets/vllm_info.txt
