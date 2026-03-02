param(
    [string]$EnvFile = ".server_env"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$envPath = Join-Path $root $EnvFile
$defaultNeighborUrl = "http://111.230.32.219:8000"

function Get-RandomHex([int]$length = 48) {
    $bytes = New-Object byte[] ($length / 2)
    [System.Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return ($bytes | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Parse-EnvFile([string]$path) {
    $map = @{}
    if (-not (Test-Path $path)) { return $map }
    foreach ($line in Get-Content $path) {
        $trim = $line.Trim()
        if (-not $trim -or $trim.StartsWith("#")) { continue }
        $idx = $trim.IndexOf("=")
        if ($idx -lt 1) { continue }
        $k = $trim.Substring(0, $idx)
        $v = $trim.Substring($idx + 1)
        $map[$k] = $v
    }
    return $map
}

$existing = Parse-EnvFile $envPath

$dockerImageName = if ($env:DOCKER_IMAGE_NAME) { $env:DOCKER_IMAGE_NAME } elseif ($existing["DOCKER_IMAGE_NAME"]) { $existing["DOCKER_IMAGE_NAME"] } else { "dllm-server:latest" }
$dockerContainerName = if ($env:DOCKER_CONTAINER_NAME) { $env:DOCKER_CONTAINER_NAME } elseif ($existing["DOCKER_CONTAINER_NAME"]) { $existing["DOCKER_CONTAINER_NAME"] } else { "dllm-server" }
$dockerWebContainerName = if ($env:DOCKER_WEB_CONTAINER_NAME) { $env:DOCKER_WEB_CONTAINER_NAME } elseif ($existing["DOCKER_WEB_CONTAINER_NAME"]) { $existing["DOCKER_WEB_CONTAINER_NAME"] } else { "dllm-web" }
$serverPort = if ($env:DLLM_SERVER_PORT) { $env:DLLM_SERVER_PORT } elseif ($existing["DLLM_SERVER_PORT"]) { $existing["DLLM_SERVER_PORT"] } else { "8000" }
$webPort = if ($env:DLLM_WEB_PORT) { $env:DLLM_WEB_PORT } elseif ($existing["DLLM_WEB_PORT"]) { $existing["DLLM_WEB_PORT"] } else { "5173" }
$dbUrl = if ($env:DLLM_SERVER_DB_URL) { $env:DLLM_SERVER_DB_URL } elseif ($existing["DLLM_SERVER_DB_URL"]) { $existing["DLLM_SERVER_DB_URL"] } else { "sqlite:///./data/server.db" }
$apiKey = if ($env:DLLM_SERVER_API_KEYS_BOOTSTRAP) { $env:DLLM_SERVER_API_KEYS_BOOTSTRAP } elseif ($existing["DLLM_SERVER_API_KEYS_BOOTSTRAP"]) { $existing["DLLM_SERVER_API_KEYS_BOOTSTRAP"] } else { "dev-key-123" }
$clusterEnabled = if ($env:DLLM_SERVER_CLUSTER_ENABLED) { $env:DLLM_SERVER_CLUSTER_ENABLED } elseif ($existing["DLLM_SERVER_CLUSTER_ENABLED"]) { $existing["DLLM_SERVER_CLUSTER_ENABLED"] } else { "true" }
$viteApiKey = if ($env:VITE_API_KEY) { $env:VITE_API_KEY } elseif ($existing["VITE_API_KEY"]) { $existing["VITE_API_KEY"] } else { "dev-key-123" }
$viteUseMock = if ($env:VITE_USE_MOCK) { $env:VITE_USE_MOCK } elseif ($existing["VITE_USE_MOCK"]) { $existing["VITE_USE_MOCK"] } else { "false" }
$nodeIp = if ($env:NODE_IP) { $env:NODE_IP } elseif ($existing["NODE_IP"]) { $existing["NODE_IP"] } else { "127.0.0.1" }
$nodeInternalIp = if ($env:NODE_INTERNAL_IP) { $env:NODE_INTERNAL_IP } elseif ($existing["NODE_INTERNAL_IP"]) { $existing["NODE_INTERNAL_IP"] } else { "127.0.0.1" }
$clusterSelfUrl = "http://$nodeIp`:$serverPort"
$viteApiBase = if ($env:VITE_API_BASE) { $env:VITE_API_BASE } elseif ($existing["VITE_API_BASE"]) { $existing["VITE_API_BASE"] } else { "http://$nodeIp`:$serverPort" }
$corsAllowOrigins = if ($env:DLLM_SERVER_CORS_ALLOW_ORIGINS) { $env:DLLM_SERVER_CORS_ALLOW_ORIGINS } elseif ($existing["DLLM_SERVER_CORS_ALLOW_ORIGINS"]) { $existing["DLLM_SERVER_CORS_ALLOW_ORIGINS"] } else { "http://$nodeIp`:$webPort,http://$nodeInternalIp`:$webPort,http://127.0.0.1:$webPort,http://localhost:$webPort" }
$corsAllowCredentials = if ($env:DLLM_SERVER_CORS_ALLOW_CREDENTIALS) { $env:DLLM_SERVER_CORS_ALLOW_CREDENTIALS } elseif ($existing["DLLM_SERVER_CORS_ALLOW_CREDENTIALS"]) { $existing["DLLM_SERVER_CORS_ALLOW_CREDENTIALS"] } else { "false" }

$internalToken = if ($existing["DLLM_SERVER_INTERNAL_TOKEN"]) { $existing["DLLM_SERVER_INTERNAL_TOKEN"] } elseif ($env:DLLM_SERVER_INTERNAL_TOKEN) { $env:DLLM_SERVER_INTERNAL_TOKEN } else { Get-RandomHex 48 }
$nodeId = "node-$(Get-Date -Format 'yyyyMMddHHmmss')-$([System.Guid]::NewGuid().ToString('N').Substring(0,8))"

$seedUrls = @($defaultNeighborUrl)
if ($existing["DLLM_SERVER_CLUSTER_SEED_URLS"]) {
    $seedUrls += $existing["DLLM_SERVER_CLUSTER_SEED_URLS"].Split(",")
}
if ($env:DLLM_SERVER_CLUSTER_SEED_URLS) {
    $seedUrls += $env:DLLM_SERVER_CLUSTER_SEED_URLS.Split(",")
}
$seedUrls = $seedUrls | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Select-Object -Unique
$clusterSeedUrls = ($seedUrls -join ",")

$envLines = @(
    "DLLM_SERVER_DB_URL=$dbUrl"
    "DLLM_SERVER_API_KEYS_BOOTSTRAP=$apiKey"
    "DLLM_SERVER_INTERNAL_TOKEN=$internalToken"
    "DLLM_SERVER_CLUSTER_ENABLED=$clusterEnabled"
    "DLLM_SERVER_CLUSTER_NODE_ID=$nodeId"
    "DLLM_SERVER_CLUSTER_SELF_URL=$clusterSelfUrl"
    "DLLM_SERVER_CLUSTER_SEED_URLS=$clusterSeedUrls"
    "DLLM_SERVER_CORS_ALLOW_ORIGINS=$corsAllowOrigins"
    "DLLM_SERVER_CORS_ALLOW_CREDENTIALS=$corsAllowCredentials"
    "DLLM_SERVER_PORT=$serverPort"
    "NODE_IP=$nodeIp"
    "NODE_INTERNAL_IP=$nodeInternalIp"
    "DOCKER_IMAGE_NAME=$dockerImageName"
    "DOCKER_CONTAINER_NAME=$dockerContainerName"
    "DOCKER_WEB_CONTAINER_NAME=$dockerWebContainerName"
    "DLLM_WEB_PORT=$webPort"
    "VITE_API_BASE=$viteApiBase"
    "VITE_API_KEY=$viteApiKey"
    "VITE_USE_MOCK=$viteUseMock"
)

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllLines($envPath, $envLines, $utf8NoBom)

$dataDir = Join-Path $root "data/server"
New-Item -ItemType Directory -Path $dataDir -Force | Out-Null

$composeArgs = @("--env-file", $envPath, "-f", "docker-compose.server.yml", "up", "-d", "--build")
docker compose version *> $null
if ($LASTEXITCODE -eq 0) {
    docker compose @composeArgs
} else {
    docker-compose @composeArgs
}

Write-Host "Deploy complete."
Write-Host "Node ID: $nodeId"
Write-Host "Internal token persisted at $envPath"
