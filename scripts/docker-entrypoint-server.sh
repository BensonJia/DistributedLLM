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
    key="$(printf '%s' "${key}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -n "${key}" ] || continue

    # Allow quoted values but do not execute file content.
    case "${val}" in
      \"*\") val="${val#\"}"; val="${val%\"}" ;;
      \'*\') val="${val#\'}"; val="${val%\'}" ;;
    esac

    export "${key}=${val}"
  done < "${file_path}"
}

# Local file takes precedence over inherited container env.
if [ -f ".server_env" ]; then
  load_env_file "./.server_env"
elif [ -f ".env" ]; then
  load_env_file "./.env"
fi

exec uvicorn server.main:app --host 0.0.0.0 --port "${DLLM_SERVER_PORT:-8000}"
