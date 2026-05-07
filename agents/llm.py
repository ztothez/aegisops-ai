"""LLM client wiring for AegisOps AI.

The live inference path is designed for AMD Instinct MI300X via vLLM running
inside a ROCm container on AMD Developer Cloud. This module also exposes a
lightweight health probe so the Streamlit UI can show real, verifiable proof
that the live ROCm endpoint is reachable.
"""

from __future__ import annotations

import os
import time
from typing import Any, Iterable, Optional, TypedDict

import httpx
from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI


load_dotenv()


REQUIRED_ENV_VARS = ("VLLM_BASE_URL", "VLLM_API_KEY", "MODEL_NAME")


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value not in (None, "") else default


def _primary_config() -> dict:
    return {
        "base_url": _env("PRIMARY_BASE_URL", _env("VLLM_BASE_URL")),
        "api_key": _env("PRIMARY_API_KEY", _env("VLLM_API_KEY", "EMPTY")),
        "model": _env("PRIMARY_MODEL", _env("MODEL_NAME")),
        "role": "primary",
    }


def _qwen_config() -> dict:
    return {
        "base_url": _env("QWEN_BASE_URL"),
        "api_key": _env("QWEN_API_KEY", "EMPTY"),
        "model": _env("QWEN_MODEL_NAME"),
        "role": "qwen",
    }


def _select_model_config(role: str | None = None) -> dict:
    mode = (_env("MODEL_MODE", "llama") or "llama").lower()
    role_name = (role or "generator").lower()

    primary = _primary_config()
    qwen = _qwen_config()
    qwen_ready = bool(qwen.get("base_url") and qwen.get("model"))

    if mode == "qwen" and qwen_ready:
        return qwen

    if mode == "hybrid" and role_name in {"validator", "validation", "verifier"} and qwen_ready:
        return qwen

    return primary


class LiveHealth(TypedDict, total=False):
    reachable: bool
    base_url: Optional[str]
    model: Optional[str]
    latency_ms: Optional[int]
    error: Optional[str]


def has_live_llm_config() -> bool:
    cfg = _primary_config()
    return bool(cfg.get("base_url") and cfg.get("api_key") and cfg.get("model"))


def build_chat(role: str | None = None) -> ChatOpenAI:
    cfg = _select_model_config(role)

    missing = [
        name for name, value in {
            "base_url": cfg.get("base_url"),
            "api_key": cfg.get("api_key"),
            "model": cfg.get("model"),
        }.items()
        if not value
    ]

    if missing:
        raise RuntimeError(
            "Live AMD/vLLM inference is not configured. "
            f"Missing fields for role={role or 'default'}: {', '.join(missing)}. "
            "Enable Demo Mode or configure VLLM/PRIMARY/QWEN environment variables."
        )

    chat = ChatOpenAI(
        base_url=cfg["base_url"],
        api_key=cfg["api_key"],
        model=cfg["model"],
        temperature=0.2,
    )

    setattr(chat, "_aegisops_model_role", cfg.get("role"))
    setattr(chat, "_aegisops_requested_role", role or "default")
    setattr(chat, "_aegisops_base_url", cfg.get("base_url"))

    return chat

def get_model_routing_status() -> dict:
    mode = (_env("MODEL_MODE", "llama") or "llama").lower()
    primary = _primary_config()
    qwen = _qwen_config()
    qwen_ready = bool(qwen.get("base_url") and qwen.get("model"))

    return {
        "model_mode": mode,
        "primary": {
            "configured": bool(primary.get("base_url") and primary.get("model")),
            "base_url": primary.get("base_url"),
            "model": primary.get("model"),
        },
        "qwen": {
            "configured": qwen_ready,
            "base_url": qwen.get("base_url"),
            "model": qwen.get("model"),
        },
        "routes": {
            "threat": "qwen" if mode == "qwen" and qwen_ready else "primary",
            "detection": "qwen" if mode == "qwen" and qwen_ready else "primary",
            "response": "qwen" if mode == "qwen" and qwen_ready else "primary",
            "validator": "qwen" if mode in {"qwen", "hybrid"} and qwen_ready else "primary",
        },
    }

def live_health(timeout_s: float = 4.0) -> LiveHealth:
    """Ping the live vLLM /models endpoint and report reachability + latency.

    Returns a structured payload suitable for direct rendering in the UI. Never
    raises - failures are folded into the ``reachable`` flag and ``error`` field
    so the status panel can stay informative without breaking the app.
    """
    cfg = _primary_config()
    base_url = cfg.get("base_url")
    api_key = cfg.get("api_key")
    model = cfg.get("model")

    if not base_url or not model:
        return LiveHealth(
            reachable=False,
            base_url=base_url,
            model=model,
            latency_ms=None,
            error="Primary live model endpoint or model name is not configured",
        )

    url = base_url.rstrip("/") + "/models"
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    started = time.perf_counter()
    try:
        with httpx.Client(timeout=timeout_s) as client:
            resp = client.get(url, headers=headers)
        latency_ms = int((time.perf_counter() - started) * 1000)
        if resp.status_code != 200:
            return LiveHealth(
                reachable=False,
                base_url=base_url,
                model=model,
                latency_ms=latency_ms,
                error=f"HTTP {resp.status_code}",
            )

        data = resp.json()
        served_models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
        served_model = served_models[0] if served_models else model
        return LiveHealth(
            reachable=True,
            base_url=base_url,
            model=served_model,
            latency_ms=latency_ms,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 - surface any failure cleanly
        latency_ms = int((time.perf_counter() - started) * 1000)
        return LiveHealth(
            reachable=False,
            base_url=base_url,
            model=model,
            latency_ms=latency_ms,
            error=type(exc).__name__,
        )


class AgentMetric(TypedDict, total=False):
    agent: str
    latency_ms: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model: Optional[str]
    model_role: Optional[str]
    requested_role: Optional[str]
    base_url: Optional[str]


def _extract_token_usage(message: Any) -> dict:
    """Best-effort extraction of token usage from a LangChain AIMessage."""
    usage = {}
    metadata = getattr(message, "response_metadata", {}) or {}
    candidates = (
        metadata.get("token_usage"),
        metadata.get("usage"),
        getattr(message, "usage_metadata", None),
    )
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        prompt = candidate.get("prompt_tokens") or candidate.get("input_tokens")
        completion = candidate.get("completion_tokens") or candidate.get("output_tokens")
        total = candidate.get("total_tokens")
        if prompt is not None or completion is not None or total is not None:
            usage = {
                "prompt_tokens": int(prompt or 0),
                "completion_tokens": int(completion or 0),
                "total_tokens": int(total or (int(prompt or 0) + int(completion or 0))),
            }
            break
    return usage


def invoke_with_metrics(
    chat: ChatOpenAI,
    messages: Iterable[BaseMessage],
    agent_name: str,
) -> tuple[str, AgentMetric]:
    """Invoke the live LLM and return (content, structured metric).

    Latency is wall-clock around the network round trip. Token counts come from
    the OpenAI-compatible response metadata (vLLM populates these). Failures are
    propagated so the caller can surface them; metric latency still gets
    recorded for partial visibility.
    """
    started = time.perf_counter()
    response = chat.invoke(list(messages))
    latency_ms = int((time.perf_counter() - started) * 1000)

    usage = _extract_token_usage(response)
    metric: AgentMetric = {
        "agent": agent_name,
        "latency_ms": latency_ms,
        "model": getattr(chat, "model_name", None) or os.getenv("MODEL_NAME"),
        "model_role": getattr(chat, "_aegisops_model_role", None),
        "requested_role": getattr(chat, "_aegisops_requested_role", None),
        "base_url": getattr(chat, "_aegisops_base_url", None),
        "prompt_tokens": int(usage.get("prompt_tokens", 0)),
        "completion_tokens": int(usage.get("completion_tokens", 0)),
        "total_tokens": int(usage.get("total_tokens", 0)),
    }
    content = response.content if hasattr(response, "content") else str(response)
    return content, metric


def merge_metrics(state: dict, metric: AgentMetric) -> dict:
    """Append a per-agent metric onto the LangGraph state's metrics list."""
    existing = state.get("metrics") or {}
    agents_list = list(existing.get("agents") or [])
    agents_list.append(metric)
    totals = {
        "agents": agents_list,
        "total_latency_ms": sum(int(m.get("latency_ms") or 0) for m in agents_list),
        "total_tokens": sum(int(m.get("total_tokens") or 0) for m in agents_list),
        "model": metric.get("model"),
    }
    return totals
