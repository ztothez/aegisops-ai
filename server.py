"""
AegisOps AI — FastAPI backend (complete)
Modes: Single Technique, APT Group, Kill Chain, Topology Lab
SSE streaming + CORS + health + PDF/Sigma export

Run:
    uvicorn server:api --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import re
import sys
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

# Internal AegisOps imports
from agents.llm import live_health, get_model_routing_status
from demo_output import DEMO_INVOKE_RESULT
from graph import app as pipeline
from export import generate_pdf

api = FastAPI(title="AegisOps AI", version="5.0")

api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

assets_dir = ROOT / "assets"
if assets_dir.exists():
    api.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

@api.get("/", response_class=HTMLResponse)
async def index():
    f = ROOT / "index.html"
    return HTMLResponse(f.read_text(encoding="utf-8") if f.exists() else "<h1>AegisOps AI API Server is Running</h1>")

# ── Health ────────────────────────────────────────────────────────────────────
@api.get("/health")
async def health():
    return JSONResponse(dict(live_health()))

@api.get("/model-routing")
async def model_routing():
    return JSONResponse(get_model_routing_status())

# ── Artifact helpers ──────────────────────────────────────────────────────────
def _extract_fenced(text: str, lang: str) -> str:
    m = re.search(rf"```{lang}\s*(.*?)\s*```", text or "", re.DOTALL | re.IGNORECASE)
    return m.group(1).strip() if m else ""

def _splunk_spl(red: str, tid: str) -> str:
    try:
        payload = _extract_fenced(red, "json")
        obs = json.loads(payload).get("observables", []) if payload else []
        obs = [str(o) for o in obs if o]
    except Exception:
        obs = []
    if not obs:
        return f'index=windows | eval mitre_technique="{tid}" | stats count by host, user'
    clause = " OR ".join(f'"{o}"' for o in obs[:10])
    return f'index=windows ({clause}) | eval mitre_technique="{tid}" | stats count by host'

def _parse_verifier(verifier: str) -> dict:
    try:
        m = re.search(r'```json\s*(.*?)\s*```', verifier, re.DOTALL)
        d = json.loads(m.group(1) if m else verifier)
        return {
            "coverage":          d.get("coverage_score", 0),
            "product_readiness": d.get("product_readiness_score", 0),
            "real_world":        d.get("real_world_applicability_score", 0),
            "safety_verdict":    d.get("safety_verdict", "PASS"),
            "verdict":           d.get("verdict", "PASS"),
            "covered_observables":     d.get("covered_observables", []),
            "missing_observables":     d.get("missing_observables", []),
            "production_gaps":         d.get("production_gaps", []),
            "improvement_suggestions": d.get("improvement_suggestions", []),
        }
    except Exception:
        return {"coverage": 0, "product_readiness": 0, "real_world": 0,
                "safety_verdict": "PENDING", "verdict": "PENDING",
                "covered_observables": [], "missing_observables": [],
                "production_gaps": [], "improvement_suggestions": []}

def _build_response(result: dict, tid: str) -> dict:
    red = result.get("red_output", "")
    blue = result.get("blue_output", "")
    return {
        "status": "success",
        "technique_id": tid,
        "verifier_model": result.get("verifier_model", "Unknown verifier model"),
        "verifier_model_role": result.get("verifier_model_role", "unknown"),
        "outputs": {
            "red": red,
            "blue": blue,
            "response": result.get("response_output", ""),
            "verifier": result.get("verifier_output", ""),
        },
        "artifacts": {
            "sigma":    _extract_fenced(blue, "yaml"),
            "splunk":   _splunk_spl(red, tid),
            "raw_red":  red,
            "raw_blue": blue,
        },
        "scores":  _parse_verifier(result.get("verifier_output", "")),
        "metrics": result.get("metrics", {}),
    }

# ── Mode Resolution ───────────────────────────────────────────────────────────
def _resolve_techniques(mode: str, technique_id: str) -> list[str]:
    """Return list of technique IDs to run based on the selected mode."""
    tid = technique_id.split("·")[0].strip().upper()
    if mode == "single":
        return [tid]
    if mode == "apt":
        try:
            from apt import get_apt_techniques
            techniques = get_apt_techniques(technique_id) 
            return [t["technique_id"] for t in techniques] or [tid]
        except Exception:
            return [tid]
    if mode == "chain":
        try:
            from chain import get_next_techniques
            chain = [tid] + [t["technique_id"] for t in get_next_techniques(tid)]
            return chain[:3]  # limit to 3 for demo purposes
        except Exception:
            return [tid]
    if mode == "topology":
        try:
            from topology import generate_attack_paths
            paths = generate_attack_paths(tid)
            if paths:
                return paths[0]["seed_techniques"][:3]
        except Exception:
            pass
        return [tid]
    return [tid]

# ── Streaming (SSE) ───────────────────────────────────────────────────────────
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

async def _stream_demo(technique_id: str) -> AsyncIterator[str]:
    result = DEMO_INVOKE_RESULT
    stages = [
        ("red",      "red_output",      "Threat Agent",     3.8),
        ("blue",     "blue_output",     "Detection Agent",  3.2),
        ("response", "response_output", "Response Agent",   2.4),
        ("verifier", "verifier_output", "Validation Agent", 1.9),
    ]
    yield _sse("start", {
        "demo": True,
        "technique_id": technique_id,
        "pipeline_version": "aegisops-production-hybrid-v1",
    })

    for key, field, label, delay in stages:
        yield _sse("agent_start", {"agent": key, "label": label})
        await asyncio.sleep(delay)
        yield _sse("agent_done", {
            "agent": key,
            "label": label,
            "output": result.get(field, ""),
        })

    full = _build_response(result, technique_id)
    yield _sse("done", {
        "demo": True,
        "metrics": full["metrics"],
        "artifacts": full["artifacts"],
        "scores": full["scores"],
        "verifier_model": full.get("verifier_model"),
        "verifier_model_role": full.get("verifier_model_role"),
    })


def _run_node(node_name: str, state: dict) -> dict:
    from agents.red_agent import run_red_agent
    from agents.blue_agent import run_blue_agent
    from agents.response_agent import run_response_agent
    from agents.verifier_agent import run_verifier_agent
    return {
        "red_agent":      run_red_agent,
        "blue_agent":     run_blue_agent,
        "response_agent": run_response_agent,
        "verifier_agent": run_verifier_agent,
    }[node_name](state)

async def _stream_live(technique_id: str, mode: str) -> AsyncIterator[str]:
    techniques = _resolve_techniques(mode, technique_id)
    yield _sse("start", {"demo": False, "technique_id": technique_id, "mode": mode,
                         "techniques": techniques,
                         "pipeline_version": "aegisops-production-hybrid-v1"})

    all_results = []
    loop = asyncio.get_event_loop()

    for i, tid in enumerate(techniques):
        if len(techniques) > 1:
            yield _sse("technique_start", {"technique_id": tid, "index": i, "total": len(techniques)})

        agent_order = [
            ("red_agent",      "red",      "red_output",      "Threat Agent"),
            ("blue_agent",     "blue",     "blue_output",     "Detection Agent"),
            ("response_agent", "response", "response_output", "Response Agent"),
            ("verifier_agent", "verifier", "verifier_output", "Validation Agent"),
        ]
        state: dict = {"technique_id": tid}

        for node_name, key, field, label in agent_order:
            yield _sse("agent_start", {"agent": key, "label": label, "technique_id": tid})
            try:
                result = await loop.run_in_executor(
                    None, lambda s=state, n=node_name: _run_node(n, s)
                )
                state.update(result)
                yield _sse("agent_done", {
                    "agent": key, "label": label,
                    "output": state.get(field, ""),
                    "technique_id": tid,
                })
            except Exception as exc:
                yield _sse("agent_error", {"agent": key, "label": label, "error": str(exc), "technique_id": tid})
                return

        all_results.append(state)
        # Yield a sub-completion for multi-technique chains
        full_sub = _build_response(state, tid)
        yield _sse("done", {
            "demo": False,
            "metrics": full_sub["metrics"],
            "artifacts": full_sub["artifacts"],
            "scores": full_sub["scores"],
            "verifier_model": full_sub.get("verifier_model"),
            "verifier_model_role": full_sub.get("verifier_model_role"),
        })

# ── Endpoints ─────────────────────────────────────────────────────────────────
@api.post("/run")
async def run_streaming(request: Request):
    body = await request.json()
    demo      = body.get("demo", True)
    technique = body.get("technique_id", "T1059.001").strip()
    mode      = body.get("mode", "single").lower().replace(" ", "_")
    
    mode_map = {"single_technique": "single", "apt_group": "apt",
                "kill_chain": "chain", "topology_lab": "topology"}
    mode = mode_map.get(mode, mode)

    async def generate():
        if demo:
            async for chunk in _stream_demo(technique):
                yield chunk
        else:
            async for chunk in _stream_live(technique, mode):
                yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

class DrillRequest(BaseModel):
    technique_id: str = "T1059.001"
    demo_mode: bool = True

@api.post("/api/run-drill")
async def run_drill(req: DrillRequest):
    """Legacy non-streaming endpoint for single runs."""
    if req.demo_mode:
        result = DEMO_INVOKE_RESULT
    else:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, lambda: pipeline.invoke({"technique_id": req.technique_id})
        )
    return _build_response(result, req.technique_id)

@api.post("/export/pdf")
async def export_pdf(request: Request):
    body = await request.json()
    tid = body.get("technique_id", "T1059.001")
    pdf = generate_pdf(tid, body.get("red_output", ""), body.get("blue_output", ""))
    return StreamingResponse(iter([pdf]), media_type="application/pdf",
                             headers={"Content-Disposition": f"attachment; filename=aegisops_{tid}.pdf"})

@api.post("/export/sigma")
async def export_sigma(request: Request):
    body = await request.json()
    sigma = _extract_fenced(body.get("blue_output", ""), "yaml")
    tid = body.get("technique_id", "rule")
    return StreamingResponse(iter([sigma.encode()]), media_type="text/plain",
                             headers={"Content-Disposition": f"attachment; filename=sigma_{tid}.yml"})

@api.get("/topology")
async def get_topology(seed: str = "T1566.001"):
    from topology import generate_topology, generate_attack_paths
    topo = generate_topology(seed)
    paths = generate_attack_paths(seed)
    return JSONResponse({"topology": topo, "paths": paths})

@api.get("/intel/group")
async def get_intel_group(name: str = "APT28"):
    from apt import get_group_info, get_apt_techniques
    info = get_group_info(name)
    techniques = get_apt_techniques(name)
    return JSONResponse({"group": info, "techniques": techniques})