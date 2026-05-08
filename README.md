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