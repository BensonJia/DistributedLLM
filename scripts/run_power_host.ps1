param(
    [string]$Port = "9002"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$env:DLLM_POWER_LISTEN_PORT = $Port
python -m uvicorn power_host.main:app --host 0.0.0.0 --port $Port
