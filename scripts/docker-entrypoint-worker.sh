#!/usr/bin/env sh
set -eu

cd /app

load_env_file() {
  file_path="$1"
  [ -f "${file_path}" ] || return 0

  while IFS= read -r raw_line || [ -n "${raw_line}" ]; do
    case "${raw_line}" in
      ''|\#*) continue ;;
    esac

    line="${raw_line}"
    case "${line}" in
      export\ *) line="${line#export }" ;;
    esac

    key="${line%%=*}"
    val="${line#*=}"
    key="$(printf '%s' "${key}" | tr -d '\r' | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    val="$(printf '%s' "${val}" | tr -d '\r')"
    [ -n "${key}" ] || continue

    case "${val}" in
      \"*\") val="${val#\"}"; val="${val%\"}" ;;
      \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac

    export "${key}=${val}"
  done < "${file_path}"
}

if [ -f ".worker_env" ]; then
  load_env_file "./.worker_env"
elif [ -f ".env" ]; then
  load_env_file "./.env"
fi

exec uvicorn worker.main:app --host 0.0.0.0 --port "${DLLM_WORKER_LISTEN_PORT:-9001}"
