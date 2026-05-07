# AegisOps AI — Merged Deck Speaker Notes

## Slide 1 — Cover
Hi judges, I'm presenting AegisOps AI — a MITRE-to-detection copilot for purple-team detection engineering. The thesis is simple: generic threat intelligence produces generic detections; high-fidelity known ATT&CK simulation produces precise detections. This deck shows the problem, the 4-agent solution, the AMD MI300X/vLLM implementation, and how the demo turns known attacker behavior into validated defensive readiness.

## Slide 2 — Problem
The problem is not that security teams lack threat intelligence. They have more than ever. The problem is that ATT&CK knowledge does not automatically become detection readiness. Teams still need scarce senior detection engineers to translate techniques into field-mapped SIEM and EDR logic. Generic intel creates generic detections, and generic detections create alert noise, missed incidents, and burned-out analysts.

## Slide 3 — Gap
This slide shows the missing layer. MITRE gives the taxonomy, Sigma gives examples, and SIEMs receive raw alerts. But the hard part is the transformation in the middle: known behavior to telemetry, telemetry to detections, detections to response, and response to validation. AegisOps AI automates that operationalization layer.

## Slide 4 — Solution
The solution is a four-agent pipeline. The Threat Agent produces high-fidelity known ATT&CK behavior. The Detection Agent converts that exact behavior into Sigma-style detection logic. The Response Agent turns detections into SOC actions. The Validation Agent checks whether the detection actually covers the simulated observables. This is a workflow engine, not a chatbot.

## Slide 5 — Key Insight / Originality
This is the originality slide. Many tools start from a vague threat description and return a vague answer. AegisOps AI starts by generating a high-fidelity known ATT&CK simulation, because the more precise the input behavior, the more precise the detection, response, and validation become. The red detail is not the final product; it is the precision input for defense.

## Slide 6 — Technical Architecture
On application of technology, this is where we prove it is not a prompt wrapper. The system uses Streamlit for the interface, LangGraph for the 4-agent state machine, an OpenAI-compatible client to vLLM, a ROCm container, and AMD MI300X for inference. MITRE ATT&CK is shipped locally, and each agent exchanges structured context rather than free-form chat.

## Slide 7 — AMD MI300X / ROCm Proof
This slide is specifically for the AMD requirement. It shows how the project proves MI300X usage: benchmark JSON, rocm-smi capture, vLLM info, and Streamlit panels for live endpoint status, per-agent latency, and token usage. The workflow is credit-efficient: develop locally, run final proof on AMD, save artifacts, then snapshot the instance.

## Slide 8 — Demo Flow
This is the live demo flow. In under five minutes, open the app, prove the AMD/vLLM endpoint is live, run T1059.001, inspect the red simulation, inspect the Sigma and realtime detection logic, show response and validation, then switch to Topology Lab to demonstrate hop-by-hop telemetry and reaction timing. This gives judges proof of both product clarity and technical implementation.

## Slide 9 — Single Technique Demo
In Single Technique mode, the user enters T1059.001. AegisOps AI outputs the detection-useful observables, maps them to Windows 4688, PowerShell 4104 and Sysmon 1, writes a Sigma-style condition, generates response guidance, and stamps coverage. This is the fastest way to show the product working end-to-end.

## Slide 10 — Topology Lab Demo
Topology Lab makes the system visual. It models a sandbox path from external actor to mail gateway, workstation, file server, and SIEM/EDR. At every hop, the system shows telemetry, ATT&CK mapping, detection condition, and response signal. This proves the idea is not just text generation; it can reason across an environment path.

## Slide 11 — Business Value / Market
For business value, the key is scarce expertise. Detection engineering requires senior skill, but every SOC needs better detections. AegisOps AI scales the workflow across enterprise SOCs, MSSPs, MDR providers, purple-team consultants, and public sector teams. Revenue can be SaaS, seat-based, on-prem, white-label, per-report, or eventually through SIEM and EDR marketplaces.

## Slide 12 — Competitive Differentiation
The competitive advantage is that AegisOps AI is purpose-built for detection engineering. Traditional tools are manual and disconnected. Generic AI chatbots summarize ATT&CK but do not produce a validated detection workflow. AegisOps AI moves from known behavior to Sigma logic, response, validation, topology, AMD inference, and structured export.

## Slide 13 — Responsible Scope
Because this is a purple-team system, we keep high fidelity, but we bound it professionally. Known ATT&CK behavior, telemetry, detection-useful patterns, Sigma rules, response, and validation are in scope. Zero-day generation, malware authoring, real target exploitation, and unauthorized engagement are out of scope. This keeps the project technically deep while clearly defensive.

## Slide 14 — Roadmap / Closing
The roadmap takes this from hackathon demo to SOC platform. Now we have Single Technique mode, Topology Lab, the 4-agent pipeline, AMD MI300X inference, and structured exports. Phase 2 adds SIEM and EDR integrations and testing against sample logs. Phase 3 becomes an enterprise SOC platform with coverage dashboards, collaboration, report history, and continuous validation. The closing line is the whole pitch: AegisOps AI turns known attacker behavior into validated defensive readiness. Thank you.
