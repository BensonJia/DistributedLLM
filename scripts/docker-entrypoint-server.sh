#!/usr/bin/env sh
set -eu

cd /app

# Local file takes precedence over inherited container env.
if [ -f ".server_env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "./.server_env"
  set +a
elif [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  . "./.env"
  set +a
fi

exec uvicorn server.main:app --host 0.0.0.0 --port "${DLLM_SERVER_PORT:-8000}"
