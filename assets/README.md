# AegisOps AI - AMD MI300X / ROCm Evidence

This folder ships verifiable evidence that the AegisOps AI live inference path
runs on AMD Instinct MI300X via vLLM inside a ROCm container on AMD Developer
Cloud. The Streamlit UI links to these files directly from the "ROCm Live"
panel at the top of every mode.

## Files

| File | Source | Description |
|------|--------|-------------|
| `cover.png` | Generated locally | 16:9 cover image required by lablab.ai submission |
| `rocm_smi.json` | `start_vllm.sh` -> `docker exec rocm rocm-smi --json` | Machine-readable ROCm GPU snapshot from the live MI300X |
| `rocm_smi.txt` | `start_vllm.sh` -> `docker exec rocm rocm-smi` | Human readable ROCm GPU snapshot |
| `vllm_info.txt` | `start_vllm.sh` | vLLM version, model id, endpoint, capture timestamp |
| `rocm_benchmark.json` | `python scripts/rocm_benchmark.py` | p50 / p95 latency, tokens/sec from real concurrent requests against the MI300X endpoint |

## How the evidence is produced

```bash
# 1. Spin up an AMD Developer Cloud MI300X instance with the ROCm image
# 2. From your local machine, run the startup script. It SSHs to the instance,
#    captures rocm-smi + vllm version into ./assets/, starts vLLM, and waits on
#    /v1/models to come online.
./start_vllm.sh <droplet-ip> <hf-token>

# 3. With the endpoint up, run the benchmark to populate rocm_benchmark.json
python scripts/rocm_benchmark.py --requests 12 --concurrency 4
```

Both files are then committed and rendered live in the Streamlit UI's ROCm
status panel and referenced from the project README and slide deck.
