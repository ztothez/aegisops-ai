#!/usr/bin/env bash

# AegisOps AI - AMD ROCm vLLM Startup Script
#
# Supports:
#   - Llama-only generator mode
#   - Qwen-only validator/reasoning mode
#   - Hybrid dual-model mode:
#       Llama 3.3 70B on port 8000
#       Qwen/QwQ on port 8001
#
# New usage:
#   ./start_vllm.sh <droplet-ip> <hf-token> [primary_model] [qwen_model] [ssh_key_path] [ssh_user] [ssh_port] [mode]
#
# Example hybrid:
#   ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct Qwen/QwQ-32B ~/.ssh/id_ed25519 root 22 hybrid
#
# Example llama-only:
#   ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct Qwen/QwQ-32B ~/.ssh/id_ed25519 root 22 llama
#
# Backward-compatible old usage:
#   ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct ~/.ssh/id_ed25519 root 22 start
#
# Modes:
#   start   alias for llama-only; captures evidence, opens port 8000, starts primary vLLM
#   llama   captures evidence, opens port 8000, starts primary vLLM
#   qwen    captures evidence, opens port 8001, starts Qwen vLLM
#   hybrid  captures evidence, opens ports 8000/8001, starts both vLLM servers
#   capture captures evidence only; does not open firewall or start vLLM
#
# Outputs:
#   assets/rocm_smi.json
#   assets/rocm_smi.txt
#   assets/vllm_info.txt
#
# Local .env updated with:
#   MODEL_MODE
#   VLLM_BASE_URL
#   VLLM_API_KEY
#   MODEL_NAME
#   PRIMARY_BASE_URL
#   PRIMARY_API_KEY
#   PRIMARY_MODEL
#   QWEN_BASE_URL
#   QWEN_API_KEY
#   QWEN_MODEL_NAME

set -Eeuo pipefail

IP="${1:-}"
HF_TOKEN="${2:-}"
PRIMARY_MODEL="${3:-meta-llama/Llama-3.3-70B-Instruct}"

DEFAULT_QWEN_MODEL="Qwen/QwQ-32B"

# -------------------------------------------------------------------
# Positional argument compatibility layer
#
# New style:
#   4 = qwen_model
#   5 = ssh_key_path
#   6 = ssh_user
#   7 = ssh_port
#   8 = mode
#
# Old style:
#   4 = ssh_key_path
#   5 = ssh_user
#   6 = ssh_port
#   7 = mode
#
# This detects old style if arg4 looks like a local SSH key path.
# -------------------------------------------------------------------

ARG4="${4:-}"
ARG5="${5:-}"
ARG6="${6:-}"
ARG7="${7:-}"
ARG8="${8:-}"

expand_tilde() {
    local path="$1"
    if [[ "${path}" == "~/"* ]]; then
        echo "${HOME}/${path#~/}"
    else
        echo "${path}"
    fi
}

looks_like_ssh_key_path() {
    local value="$1"
    local expanded
    expanded="$(expand_tilde "${value}")"

    [[ -z "${value}" ]] && return 1

    if [[ -f "${expanded}" ]]; then
        return 0
    fi

    if [[ "${value}" == "~/"* || "${value}" == "/"* || "${value}" == "."* ]]; then
        return 0
    fi

    return 1
}

if looks_like_ssh_key_path "${ARG4}"; then
    # Old style
    QWEN_MODEL="${DEFAULT_QWEN_MODEL}"
    SSH_KEY_PATH="$(expand_tilde "${ARG4}")"
    SSH_USER="${ARG5:-root}"
    SSH_PORT="${ARG6:-22}"
    MODE="${ARG7:-start}"
else
    # New style
    QWEN_MODEL="${ARG4:-${DEFAULT_QWEN_MODEL}}"
    SSH_KEY_PATH="$(expand_tilde "${ARG5:-}")"
    SSH_USER="${ARG6:-root}"
    SSH_PORT="${ARG7:-22}"
    MODE="${ARG8:-start}"
fi

PRIMARY_PORT=8000
QWEN_PORT=8001

PRIMARY_ENDPOINT="http://${IP}:${PRIMARY_PORT}/v1"
QWEN_ENDPOINT="http://${IP}:${QWEN_PORT}/v1"

# Backward compatibility for old app/code paths.
ENDPOINT="${PRIMARY_ENDPOINT}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="${SCRIPT_DIR}/assets"
ENV_FILE="${SCRIPT_DIR}/.env"

mkdir -p "${ASSETS_DIR}"

log() {
    echo "$*"
}

fail() {
    echo ""
    echo "ERROR: $*" >&2
    echo ""
    exit 1
}

usage() {
    cat <<EOF
Usage:
  ./start_vllm.sh <droplet-ip> <hf-token> [primary_model] [qwen_model] [ssh_key_path] [ssh_user] [ssh_port] [mode]

Examples:
  # Hybrid Llama + Qwen
  ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct Qwen/QwQ-32B ~/.ssh/id_ed25519 root 22 hybrid

  # Llama-only
  ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct Qwen/QwQ-32B ~/.ssh/id_ed25519 root 22 llama

  # Qwen-only
  ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct Qwen/QwQ-32B ~/.ssh/id_ed25519 root 22 qwen

  # Backward-compatible old style, llama-only
  ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct ~/.ssh/id_ed25519 root 22 start

Modes:
  start   alias for llama-only
  llama   start primary model on port 8000
  qwen    start Qwen model on port 8001
  hybrid  start primary model on port 8000 and Qwen on port 8001
  capture capture evidence only

Notes:
  - ssh_key_path must be your PRIVATE key file, not the .pub public key.
  - Ports 8000 and/or 8001 must be reachable from where your Streamlit app runs.
  - Do not commit .env if it contains tokens or private endpoints.
EOF
}

if [[ -z "${IP}" ]]; then
    usage
    fail "Missing droplet IP."
fi

case "${MODE}" in
    start|llama|qwen|hybrid|capture)
        ;;
    *)
        usage
        fail "Invalid mode: ${MODE}. Expected: start, llama, qwen, hybrid, or capture."
        ;;
esac

if [[ "${MODE}" != "capture" && -z "${HF_TOKEN}" ]]; then
    usage
    fail "Missing Hugging Face token. It is required unless mode=capture."
fi

CONTROL_PATH="${SCRIPT_DIR}/.ssh_mux_${SSH_USER}_${IP}_${SSH_PORT}"
KNOWN_HOSTS_FILE="${SCRIPT_DIR}/.known_hosts_aegisops"

SSH_OPTS=(
    -o StrictHostKeyChecking=no
    -o UserKnownHostsFile="${KNOWN_HOSTS_FILE}"
    -o ConnectTimeout=10
    -o ServerAliveInterval=10
    -o ServerAliveCountMax=3
    -o ControlMaster=auto
    -o ControlPersist=15m
    -o ControlPath="${CONTROL_PATH}"
    -p "${SSH_PORT}"
)

if [[ -n "${SSH_KEY_PATH}" ]]; then
    if [[ ! -f "${SSH_KEY_PATH}" ]]; then
        fail "SSH private key file not found: ${SSH_KEY_PATH}"
    fi

    chmod 600 "${SSH_KEY_PATH}" 2>/dev/null || true

    SSH_OPTS+=(
        -o IdentitiesOnly=yes
        -i "${SSH_KEY_PATH}"
    )
fi

cleanup_ssh_mux() {
    ssh "${SSH_OPTS[@]}" -O exit "${SSH_USER}@${IP}" >/dev/null 2>&1 || true
}

trap cleanup_ssh_mux EXIT

ssh_run() {
    local tries=4
    local delay=2
    local n=1

    while true; do
        if ssh "${SSH_OPTS[@]}" "${SSH_USER}@${IP}" "$@"; then
            return 0
        fi

        if [[ "${n}" -ge "${tries}" ]]; then
            return 1
        fi

        log "    SSH failed attempt ${n}/${tries}; retrying in ${delay}s..."
        sleep "${delay}"

        n=$((n + 1))
        delay=$((delay * 2))
    done
}

ssh_must() {
    ssh_run "$@" || fail "SSH command failed: $*"
}

quote_remote() {
    printf "%q" "$1"
}

upsert_env() {
    local key="$1"
    local value="$2"

    touch "${ENV_FILE}"

    if grep -q "^${key}=" "${ENV_FILE}"; then
        sed -i "s|^${key}=.*|${key}=${value}|" "${ENV_FILE}"
    else
        echo "${key}=${value}" >> "${ENV_FILE}"
    fi
}

wait_for_endpoint() {
    local name="$1"
    local endpoint="$2"
    local attempts="${3:-90}"
    local sleep_s="${4:-10}"

    log "    Waiting for ${name} at ${endpoint}/models ..."

    for i in $(seq 1 "${attempts}"); do
        if curl -fsS --max-time 5 "${endpoint}/models" >/dev/null 2>&1; then
            log "    ${name} is reachable after $((i * sleep_s))s."
            return 0
        fi

        if [[ "${i}" -eq "${attempts}" ]]; then
            log ""
            log "    WARNING: ${name} did not respond within $((attempts * sleep_s))s."
            log "    Test from your machine:"
            log "      curl ${endpoint}/models"
            log ""
            return 1
        fi

        sleep "${sleep_s}"
    done
}

start_vllm_model() {
    local label="$1"
    local model="$2"
    local port="$3"
    local endpoint="$4"
    local gpu_mem="$5"
    local max_len="$6"
    local log_file="$7"

    if curl -fsS --max-time 5 "${endpoint}/models" >/dev/null 2>&1; then
        log "    ${label} already reachable at ${endpoint}; skipping start."
        return 0
    fi

    log "    ${label} not reachable, starting inside container..."
    log "    Model: ${model}"
    log "    Port:  ${port}"
    log "    VRAM cap: ${gpu_mem}"
    log "    Max model length: ${max_len}"

    local hf_token_q
    local model_q

    hf_token_q="$(quote_remote "${HF_TOKEN}")"
    model_q="$(quote_remote "${model}")"

    ssh_must "docker exec -d \
        -e HUGGING_FACE_HUB_TOKEN=${hf_token_q} \
        -e HF_TOKEN=${hf_token_q} \
        ${ROCM_CONTAINER} \
        bash -lc 'mkdir -p /tmp/aegisops-vllm && \
        nohup vllm serve ${model_q} \
            --host 0.0.0.0 \
            --port ${port} \
            --dtype float16 \
            --max-model-len ${max_len} \
            --gpu-memory-utilization ${gpu_mem} \
            > ${log_file} 2>&1 &'"

    log "    ${label} vLLM start command sent."
    log "    Remote logs:"
    log "      ssh ${SSH_KEY_PATH:+-i ${SSH_KEY_PATH}} -p ${SSH_PORT} ${SSH_USER}@${IP} \"docker exec ${ROCM_CONTAINER} tail -f ${log_file}\""
}

log "[0/8] Configuration"
log "    IP:              ${IP}"
log "    SSH user:        ${SSH_USER}"
log "    SSH port:        ${SSH_PORT}"
log "    Mode:            ${MODE}"
log "    Primary model:   ${PRIMARY_MODEL}"
log "    Qwen model:      ${QWEN_MODEL}"
log "    Primary endpoint:${PRIMARY_ENDPOINT}"
log "    Qwen endpoint:   ${QWEN_ENDPOINT}"

log ""
log "[1/8] Checking SSH access to ${SSH_USER}@${IP}:${SSH_PORT}..."

if ! ssh_run "echo ssh-ok >/dev/null"; then
    cat >&2 <<EOF

ERROR: Cannot SSH into the droplet.

The remote host refused SSH on port ${SSH_PORT}.

This usually means one of these:
  1. The droplet is powered off, rebooting, or crashed.
  2. sshd is not running on the droplet.
  3. Port ${SSH_PORT} is blocked by the provider firewall.
  4. You are using the wrong IP.
  5. The droplet changed SSH port.
  6. The VM firewall accidentally blocks SSH.

Try this manually:

  ssh ${SSH_KEY_PATH:+-i "${SSH_KEY_PATH}"} -p ${SSH_PORT} ${SSH_USER}@${IP}

If that also says "Connection refused", fix the droplet from the cloud console first.
This script cannot start vLLM without SSH access.

EOF
    exit 1
fi

log "    SSH OK."

log "[2/8] Protecting SSH access before touching firewall..."
ssh_must "ufw allow ${SSH_PORT}/tcp || true"

log "[3/8] Checking Docker and ROCm container..."

ssh_must "command -v docker >/dev/null"

ROCM_CONTAINER="$(ssh_must "docker ps --format '{{.Names}}' | head -n 1" | tr -d '\r' || true)"

if [[ -z "${ROCM_CONTAINER}" ]]; then
    fail "No running Docker container found. Start the ROCm/vLLM container first, then rerun this script."
fi

log "    Using container: ${ROCM_CONTAINER}"

log "[4/8] Opening vLLM ports on ${IP}..."

if [[ "${MODE}" == "capture" ]]; then
    log "    mode=capture, skipping firewall changes."
else
    if [[ "${MODE}" == "start" || "${MODE}" == "llama" || "${MODE}" == "hybrid" ]]; then
        ssh_must "ufw allow ${PRIMARY_PORT}/tcp || true"
        log "    Opened/allowed port ${PRIMARY_PORT}."
    fi

    if [[ "${MODE}" == "qwen" || "${MODE}" == "hybrid" ]]; then
        ssh_must "ufw allow ${QWEN_PORT}/tcp || true"
        log "    Opened/allowed port ${QWEN_PORT}."
    fi
fi

log "[5/8] Capturing ROCm GPU evidence into ${ASSETS_DIR}/ ..."

ROCM_JSON_TMP="$(mktemp)"
ROCM_TEXT_TMP="$(mktemp)"

if ssh_run "docker exec ${ROCM_CONTAINER} bash -lc 'rocm-smi --showproductname --showmeminfo vram --showuse --json 2>/dev/null || rocm-smi --showproductname --showmeminfo vram --showuse -J 2>/dev/null || rocm-smi --json 2>/dev/null || rocm-smi -J 2>/dev/null'" \
    > "${ROCM_JSON_TMP}" \
    && python3 -m json.tool "${ROCM_JSON_TMP}" >/dev/null 2>&1; then

    cp "${ROCM_JSON_TMP}" "${ASSETS_DIR}/rocm_smi.json"
    log "    Wrote native rocm_smi.json."

    if ssh_run "docker exec ${ROCM_CONTAINER} bash -lc 'rocm-smi --showproductname --showmeminfo vram --showuse 2>/dev/null || rocm-smi 2>/dev/null || echo rocm-smi unavailable'" \
        > "${ASSETS_DIR}/rocm_smi.txt"; then
        log "    Wrote rocm_smi.txt."
    else
        echo "rocm-smi snapshot unavailable" > "${ASSETS_DIR}/rocm_smi.txt"
        log "    WARNING: rocm-smi text snapshot unavailable."
    fi

else
    log "    Native rocm-smi JSON unavailable in container; preserving ROCm text output as structured JSON."

    ssh_run "docker exec ${ROCM_CONTAINER} bash -lc 'rocm-smi --showproductname --showmeminfo vram --showuse 2>/dev/null || rocm-smi 2>/dev/null || echo rocm-smi unavailable'" \
        > "${ROCM_TEXT_TMP}" \
        || echo "rocm-smi snapshot unavailable" > "${ROCM_TEXT_TMP}"

    cp "${ROCM_TEXT_TMP}" "${ASSETS_DIR}/rocm_smi.txt"

    python3 - "${ROCM_TEXT_TMP}" "${ASSETS_DIR}/rocm_smi.json" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

txt_path = Path(sys.argv[1])
json_path = Path(sys.argv[2])

raw = txt_path.read_text(errors="replace")

def find_int(pattern):
    match = re.search(pattern, raw)
    return int(match.group(1)) if match else None

def find_text(pattern):
    match = re.search(pattern, raw)
    return match.group(1).strip() if match else None

vram_total = find_int(r"VRAM Total Memory \(B\):\s*([0-9]+)")
vram_used = find_int(r"VRAM Total Used Memory \(B\):\s*([0-9]+)")
gpu_use = find_int(r"GPU use \(%\):\s*([0-9]+)")
vendor = find_text(r"Card Vendor:\s*(.+)")
sku = find_text(r"Card SKU:\s*(.+)")
model = find_text(r"Card Model:\s*(.+)")
gfx = find_text(r"GFX Version:\s*(.+)")
node_id = find_text(r"Node ID:\s*(.+)")
guid = find_text(r"GUID:\s*(.+)")

data = {
    "captured_at": datetime.now(timezone.utc).isoformat(),
    "source": "rocm-smi text snapshot converted to JSON",
    "status": "ok",
    "note": "Native rocm-smi JSON output was unavailable in this container, so text output was converted into structured JSON evidence.",
    "gpu": {
        "index": 0,
        "vendor": vendor,
        "card_model": model,
        "card_sku": sku,
        "gfx_version": gfx,
        "node_id": node_id,
        "guid": guid,
        "gpu_use_percent": gpu_use,
        "vram_total_bytes": vram_total,
        "vram_used_bytes": vram_used,
        "vram_total_gib": round(vram_total / (1024 ** 3), 2) if vram_total else None,
        "vram_used_gib": round(vram_used / (1024 ** 3), 2) if vram_used else None,
    },
    "raw_text": raw,
}

json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
PY

    log "    Wrote converted rocm_smi.json."
    log "    Wrote rocm_smi.txt."
fi

rm -f "${ROCM_JSON_TMP}" "${ROCM_TEXT_TMP}"

log "[6/8] Recording vLLM + model metadata ..."

VLLM_VERSION="$(
    ssh_run "docker exec ${ROCM_CONTAINER} bash -lc 'vllm --version 2>/dev/null || python3 -m vllm.entrypoints.openai.api_server --help >/dev/null 2>&1 && echo vllm-installed || echo unknown'" 2>/dev/null \
    || echo "unknown"
)"

{
    echo "captured_at:       $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "host:              ${IP}"
    echo "mode:              ${MODE}"
    echo "primary_endpoint:  ${PRIMARY_ENDPOINT}"
    echo "primary_model:     ${PRIMARY_MODEL}"
    echo "qwen_endpoint:     ${QWEN_ENDPOINT}"
    echo "qwen_model:        ${QWEN_MODEL}"
    echo "vllm_version:      ${VLLM_VERSION}"
    echo "container:         ${ROCM_CONTAINER}"
    echo "runtime:           ROCm container, vLLM OpenAI-compatible server"
    echo "gpu:               AMD Instinct MI300X / ROCm environment"
} > "${ASSETS_DIR}/vllm_info.txt"

log "    Wrote vllm_info.txt."

log "[7/8] Starting vLLM inside ROCm container ..."

if [[ "${MODE}" == "capture" ]]; then
    log "    mode=capture, skipping vLLM start."
else
    # Llama/default generation path.
    if [[ "${MODE}" == "start" || "${MODE}" == "llama" || "${MODE}" == "hybrid" ]]; then
        if [[ "${MODE}" == "hybrid" ]]; then
            # More conservative to leave memory for Qwen.
            PRIMARY_GPU_MEM="${PRIMARY_GPU_MEMORY_UTILIZATION:-0.60}"
            PRIMARY_MAX_LEN="${PRIMARY_MAX_MODEL_LEN:-4096}"
        else
            # Original-ish single-model behavior, but less extreme than 65536/0.95.
            # You can override these with env vars if needed.
            PRIMARY_GPU_MEM="${PRIMARY_GPU_MEMORY_UTILIZATION:-0.90}"
            PRIMARY_MAX_LEN="${PRIMARY_MAX_MODEL_LEN:-8192}"
        fi

        start_vllm_model \
            "Primary/Llama generator" \
            "${PRIMARY_MODEL}" \
            "${PRIMARY_PORT}" \
            "${PRIMARY_ENDPOINT}" \
            "${PRIMARY_GPU_MEM}" \
            "${PRIMARY_MAX_LEN}" \
            "/tmp/aegisops-vllm/primary-vllm.log"
    fi

    # Qwen validator/reasoning path.
    if [[ "${MODE}" == "qwen" || "${MODE}" == "hybrid" ]]; then
        if [[ "${MODE}" == "hybrid" ]]; then
            QWEN_GPU_MEM="${QWEN_GPU_MEMORY_UTILIZATION:-0.30}"
            QWEN_MAX_LEN="${QWEN_MAX_MODEL_LEN:-4096}"
        else
            QWEN_GPU_MEM="${QWEN_GPU_MEMORY_UTILIZATION:-0.85}"
            QWEN_MAX_LEN="${QWEN_MAX_MODEL_LEN:-8192}"
        fi

        start_vllm_model \
            "Qwen validator/reasoning model" \
            "${QWEN_MODEL}" \
            "${QWEN_PORT}" \
            "${QWEN_ENDPOINT}" \
            "${QWEN_GPU_MEM}" \
            "${QWEN_MAX_LEN}" \
            "/tmp/aegisops-vllm/qwen-vllm.log"
    fi
fi

log "[8/8] Waiting for vLLM /v1/models endpoint(s) to come online ..."

if [[ "${MODE}" == "capture" ]]; then
    log "    mode=capture, skipping wait."
else
    if [[ "${MODE}" == "start" || "${MODE}" == "llama" || "${MODE}" == "hybrid" ]]; then
        wait_for_endpoint "Primary/Llama generator" "${PRIMARY_ENDPOINT}" 90 10 || true
    fi

    if [[ "${MODE}" == "qwen" || "${MODE}" == "hybrid" ]]; then
        wait_for_endpoint "Qwen validator/reasoning model" "${QWEN_ENDPOINT}" 90 10 || true
    fi
fi

log "Updating local .env with the AMD Developer Cloud endpoint(s) ..."

if [[ "${MODE}" == "hybrid" ]]; then
    APP_MODEL_MODE="hybrid"
elif [[ "${MODE}" == "qwen" ]]; then
    APP_MODEL_MODE="qwen"
else
    APP_MODEL_MODE="llama"
fi

# Compatibility variables for existing app code.
if [[ "${APP_MODEL_MODE}" == "qwen" ]]; then
    upsert_env "VLLM_BASE_URL" "${QWEN_ENDPOINT}"
    upsert_env "VLLM_API_KEY" "EMPTY"
    upsert_env "MODEL_NAME" "${QWEN_MODEL}"
else
    upsert_env "VLLM_BASE_URL" "${PRIMARY_ENDPOINT}"
    upsert_env "VLLM_API_KEY" "EMPTY"
    upsert_env "MODEL_NAME" "${PRIMARY_MODEL}"
fi

# New routing variables for dual-model agent code.
upsert_env "MODEL_MODE" "${APP_MODEL_MODE}"

upsert_env "PRIMARY_BASE_URL" "${PRIMARY_ENDPOINT}"
upsert_env "PRIMARY_API_KEY" "EMPTY"
upsert_env "PRIMARY_MODEL" "${PRIMARY_MODEL}"

upsert_env "QWEN_BASE_URL" "${QWEN_ENDPOINT}"
upsert_env "QWEN_API_KEY" "EMPTY"
upsert_env "QWEN_MODEL_NAME" "${QWEN_MODEL}"

log ""
log "Done."
log "  Mode:              ${APP_MODEL_MODE}"
log "  Primary endpoint:  ${PRIMARY_ENDPOINT}"
log "  Primary model:     ${PRIMARY_MODEL}"
log "  Qwen endpoint:     ${QWEN_ENDPOINT}"
log "  Qwen model:        ${QWEN_MODEL}"
log "  Evidence:          ${ASSETS_DIR}/rocm_smi.json, rocm_smi.txt, vllm_info.txt"
log ""
log "Useful tests:"
log "  curl ${PRIMARY_ENDPOINT}/models"
log "  curl ${QWEN_ENDPOINT}/models"
log ""
log "Remote logs:"
log "  ssh ${SSH_KEY_PATH:+-i ${SSH_KEY_PATH}} -p ${SSH_PORT} ${SSH_USER}@${IP} \"docker exec ${ROCM_CONTAINER} tail -100 /tmp/aegisops-vllm/primary-vllm.log\""
log "  ssh ${SSH_KEY_PATH:+-i ${SSH_KEY_PATH}} -p ${SSH_PORT} ${SSH_USER}@${IP} \"docker exec ${ROCM_CONTAINER} tail -100 /tmp/aegisops-vllm/qwen-vllm.log\""
log ""
log "Run the app:"
log "  streamlit run app.py"