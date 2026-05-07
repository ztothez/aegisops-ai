#!/usr/bin/env python3
"""Benchmark the live AMD MI300X / ROCm vLLM endpoint.

Sends N concurrent chat-completion requests against the configured vLLM server,
records per-request latency + token counts, and writes a structured summary to
``assets/rocm_benchmark.json`` so the Streamlit UI and README can display real,
reproducible AMD ROCm performance evidence for the hackathon submission.

Usage:
    python scripts/rocm_benchmark.py [--concurrency 4] [--requests 12] [--prompt-tokens 512]

Reads VLLM_BASE_URL, VLLM_API_KEY, MODEL_NAME from the environment / .env.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv


PROMPT = (
    "You are a senior detection engineer. In two short sentences, summarize how a "
    "Sigma rule for MITRE ATT&CK T1059.001 (PowerShell) should reason about parent "
    "process lineage and command-line obfuscation. Be concrete."
)


def _post_chat(client: httpx.Client, base_url: str, api_key: str, model: str) -> dict:
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0.2,
        "max_tokens": 256,
    }
    started = time.perf_counter()
    resp = client.post(
        base_url.rstrip("/") + "/chat/completions",
        json=payload,
        headers=headers,
        timeout=120.0,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000.0
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage") or {}
    completion = data["choices"][0]["message"]["content"]
    return {
        "latency_ms": elapsed_ms,
        "prompt_tokens": int(usage.get("prompt_tokens") or 0),
        "completion_tokens": int(usage.get("completion_tokens") or 0),
        "total_tokens": int(usage.get("total_tokens") or 0),
        "completion_chars": len(completion),
    }


def _percentile(values: list[float], pct: float) -> Optional[float]:
    if not values:
        return None
    sorted_values = sorted(values)
    k = (len(sorted_values) - 1) * (pct / 100.0)
    lo = int(k)
    hi = min(lo + 1, len(sorted_values) - 1)
    frac = k - lo
    return round(sorted_values[lo] * (1 - frac) + sorted_values[hi] * frac, 2)


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Benchmark AegisOps AI vLLM endpoint on AMD MI300X / ROCm")
    parser.add_argument("--requests", type=int, default=12, help="total request count")
    parser.add_argument("--concurrency", type=int, default=4, help="parallel workers")
    parser.add_argument("--output", type=str, default=None, help="output JSON path (default: assets/rocm_benchmark.json)")
    args = parser.parse_args()

    base_url = os.getenv("VLLM_BASE_URL")
    api_key = os.getenv("VLLM_API_KEY", "")
    model = os.getenv("MODEL_NAME")
    if not base_url or not model:
        print("ERROR: VLLM_BASE_URL and MODEL_NAME must be set (use .env or shell env).")
        return 1

    output = Path(args.output) if args.output else Path(__file__).resolve().parent.parent / "assets" / "rocm_benchmark.json"
    output.parent.mkdir(parents=True, exist_ok=True)

    print(f"Benchmarking {args.requests} requests @ concurrency={args.concurrency}")
    print(f"  endpoint: {base_url}")
    print(f"  model:    {model}")

    results: list[dict] = []
    errors = 0
    started_wall = time.perf_counter()
    with httpx.Client() as client:
        with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
            futures = [
                pool.submit(_post_chat, client, base_url, api_key, model)
                for _ in range(args.requests)
            ]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as exc:  # noqa: BLE001
                    errors += 1
                    print(f"  request failed: {type(exc).__name__}: {exc}")

    wall_seconds = max(time.perf_counter() - started_wall, 1e-6)
    if not results:
        print("ERROR: no successful requests; nothing written.")
        return 2

    latencies = [r["latency_ms"] for r in results]
    completion_tokens = sum(r["completion_tokens"] for r in results)
    total_tokens = sum(r["total_tokens"] for r in results)
    tps = round(completion_tokens / wall_seconds, 2)

    summary = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": base_url,
        "model": model,
        "runtime": "vLLM on ROCm container",
        "gpu": "AMD Instinct MI300X (AMD Developer Cloud)",
        "concurrency": args.concurrency,
        "requests": args.requests,
        "successful": len(results),
        "failed": errors,
        "wall_clock_seconds": round(wall_seconds, 3),
        "latency_ms_p50": _percentile(latencies, 50),
        "latency_ms_p95": _percentile(latencies, 95),
        "latency_ms_avg": round(statistics.fmean(latencies), 2),
        "latency_ms_min": round(min(latencies), 2),
        "latency_ms_max": round(max(latencies), 2),
        "tokens_per_second": tps,
        "completion_tokens_total": completion_tokens,
        "total_tokens": total_tokens,
        "prompt": PROMPT,
    }

    output.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {output}")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
