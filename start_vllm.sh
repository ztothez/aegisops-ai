#!/usr/bin/env bash

# AegisOps AI - AMD ROCm vLLM Startup Script
#
# Usage:
#   ./start_vllm.sh <droplet-ip> <hf-token> [model] [ssh_key_path] [ssh_user] [ssh_port] [mode]
#
# Example:
#   ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct ~/.ssh/id_ed25519 root 22 start
#
# mode:
#   start   capture evidence, open port 8000, start vLLM if needed
#   capture capture evidence only; do not open firewall or start vLLM
#
# Outputs:
#   assets/rocm_smi.json
#   assets/rocm_smi.txt
#   assets/vllm_info.txt

set -Eeuo pipefail

IP="${1:-}"
HF_TOKEN="${2:-}"
MODEL="${3:-meta-llama/Llama-3.3-70B-Instruct}"
SSH_KEY_PATH="${4:-}"
SSH_USER="${5:-root}"
SSH_PORT="${6:-22}"
MODE="${7:-start}"
PORT=8000

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSETS_DIR="${SCRIPT_DIR}/assets"
ENV_FILE="${SCRIPT_DIR}/.env"
ENDPOINT="http://${IP}:${PORT}/v1"

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
  ./start_vllm.sh <droplet-ip> <hf-token> [model] [ssh_key_path] [ssh_user] [ssh_port] [mode]

Example:
  ./start_vllm.sh 134.199.199.167 hf_xxx meta-llama/Llama-3.3-70B-Instruct ~/.ssh/id_ed25519 root 22 start

Notes:
  - ssh_key_path must be your PRIVATE key file, not the .pub public key.
  - If SSH says "Connection refused", the droplet SSH service or cloud firewall is broken/unreachable.
EOF
}

if [[ -z "${IP}" ]]; then
    usage
    fail "Missing droplet IP."
fi

if [[ "${MODE}" != "start" && "${MODE}" != "capture" ]]; then
    usage
    fail "Invalid mode: ${MODE}. Expected: start or capture."
fi

if [[ "${MODE}" == "start" && -z "${HF_TOKEN}" ]]; then
    usage
    fail "Missing Hugging Face token. It is required in start mode."
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

log "[0/7] Checking SSH access to ${SSH_USER}@${IP}:${SSH_PORT}..."

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

log "[1/7] Protecting SSH access before touching firewall..."
ssh_must "ufw allow ${SSH_PORT}/tcp || true"

log "[2/7] Checking Docker and ROCm container..."

ssh_must "command -v docker >/dev/null"

ROCM_CONTAINER="$(ssh_must "docker ps --format '{{.Names}}' | head -n 1" | tr -d '\r' || true)"

if [[ -z "${ROCM_CONTAINER}" ]]; then
    fail "No running Docker container found. Start the ROCm/vLLM container first, then rerun this script."
fi

log "    Using container: ${ROCM_CONTAINER}"

log "[3/7] Opening port ${PORT} on ${IP}..."

if [[ "${MODE}" == "start" ]]; then
    ssh_must "ufw allow ${PORT}/tcp || true"
else
    log "    mode=capture, skipping firewall changes."
fi

log "[4/7] Capturing ROCm GPU evidence into ${ASSETS_DIR}/ ..."

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

log "[5/7] Recording vLLM + model metadata ..."

VLLM_VERSION="$(
    ssh_run "docker exec ${ROCM_CONTAINER} bash -lc 'vllm --version 2>/dev/null || python3 -m vllm.entrypoints.openai.api_server --help >/dev/null 2>&1 && echo vllm-installed || echo unknown'" 2>/dev/null \
    || echo "unknown"
)"

{
    echo "captured_at:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "host:          ${IP}"
    echo "endpoint:      ${ENDPOINT}"
    echo "model:         ${MODEL}"
    echo "vllm_version:  ${VLLM_VERSION}"
    echo "container:     ${ROCM_CONTAINER}"
    echo "runtime:       ROCm container, vLLM OpenAI-compatible server"
    echo "gpu:           AMD Instinct MI300X / ROCm environment"
} > "${ASSETS_DIR}/vllm_info.txt"

log "    Wrote vllm_info.txt."

log "[6/7] Starting vLLM inside ROCm container ..."

if [[ "${MODE}" == "capture" ]]; then
    log "    mode=capture, skipping vLLM start."
elif curl -fsS --max-time 5 "${ENDPOINT}/models" >/dev/null 2>&1; then
    log "    vLLM already reachable at ${ENDPOINT}; skipping start."
else
    log "    vLLM not reachable, starting inside container..."

    HF_TOKEN_Q="$(quote_remote "${HF_TOKEN}")"
    MODEL_Q="$(quote_remote "${MODEL}")"

    ssh_must "docker exec -d \
        -e HUGGING_FACE_HUB_TOKEN=${HF_TOKEN_Q} \
        -e HF_TOKEN=${HF_TOKEN_Q} \
        ${ROCM_CONTAINER} \
        bash -lc 'mkdir -p /tmp/aegisops-vllm && \
        nohup vllm serve ${MODEL_Q} \
            --host 0.0.0.0 \
            --port ${PORT} \
            --dtype float16 \
            --max-model-len 65536 \
            --gpu-memory-utilization 0.95 \
            > /tmp/aegisops-vllm/vllm.log 2>&1 &'"

    log "    vLLM start command sent."
    log "    Remote logs:"
    log "      ssh ${SSH_KEY_PATH:+-i ${SSH_KEY_PATH}} -p ${SSH_PORT} ${SSH_USER}@${IP} \"docker exec ${ROCM_CONTAINER} tail -f /tmp/aegisops-vllm/vllm.log\""
fi

log "[7/7] Waiting for vLLM /v1/models to come online ..."

if [[ "${MODE}" == "capture" ]]; then
    log "    mode=capture, skipping wait."
else
    ATTEMPTS=90
    SLEEP_S=10

    for i in $(seq 1 "${ATTEMPTS}"); do
        if curl -fsS --max-time 5 "${ENDPOINT}/models" >/dev/null 2>&1; then
            log "    vLLM is reachable after $((i * SLEEP_S))s."
            break
        fi

        if [[ "${i}" -eq "${ATTEMPTS}" ]]; then
            log ""
            log "    WARNING: vLLM did not respond within $((ATTEMPTS * SLEEP_S))s."
            log ""
            log "    Check remote logs with:"
            log "      ssh ${SSH_KEY_PATH:+-i ${SSH_KEY_PATH}} -p ${SSH_PORT} ${SSH_USER}@${IP} \"docker exec ${ROCM_CONTAINER} tail -100 /tmp/aegisops-vllm/vllm.log\""
            log ""
            log "    Also test from your machine:"
            log "      curl ${ENDPOINT}/models"
        fi

        sleep "${SLEEP_S}"
    done
fi

log "Updating local .env with the AMD Developer Cloud endpoint ..."

upsert_env "VLLM_BASE_URL" "${ENDPOINT}"
upsert_env "VLLM_API_KEY" "EMPTY"
upsert_env "MODEL_NAME" "${MODEL}"

log ""
log "Done."
log "  Endpoint:  ${ENDPOINT}"
log "  Model:     ${MODEL}"
log "  Evidence:  ${ASSETS_DIR}/rocm_smi.json, rocm_smi.txt, vllm_info.txt"
log ""
log "Run the app:"
log "  streamlit run app.py"