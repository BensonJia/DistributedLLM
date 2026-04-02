#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

exec uvicorn power_host.main:app --host 0.0.0.0 --port "${DLLM_POWER_LISTEN_PORT:-9002}"

