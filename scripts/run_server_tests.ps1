param(
    [string]$CondaEnv = "dllm"
)

$ErrorActionPreference = "Stop"

Write-Host "Running server federation tests in conda env: $CondaEnv"

# Keep server-side waits short in tests so failures surface quickly.
$env:DLLM_SERVER_REQUEST_TIMEOUT_SEC = "3"
$env:DLLM_SERVER_JOB_MAX_WAIT_SEC = "3"
$env:DLLM_SERVER_JOB_POLL_INTERVAL_MS = "50"
$env:DLLM_SERVER_CLUSTER_REQUEST_FORWARD_AFTER_SEC = "0"
$env:DLLM_SERVER_CLUSTER_REQUEST_FORWARD_TIMEOUT_SEC = "1.5"
$env:DLLM_SERVER_CLUSTER_GOSSIP_TIMEOUT_SEC = "1.0"
$env:DLLM_SERVER_CLUSTER_PROBE_TIMEOUT_SEC = "0.8"

conda run -n $CondaEnv python -m pip install -q pytest
conda run -n $CondaEnv pytest -q tests/test_server_federation.py
