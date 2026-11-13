$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "Stopping CYBER VIPER DevSecOps containers (persistent volumes are preserved)..." -ForegroundColor Cyan
docker compose -f ".\devops-tools\docker-compose.yml" down

if ($LASTEXITCODE -ne 0) {
    throw "Docker Compose could not stop the stack."
}

Write-Host "Stack stopped. Persistent application, SonarQube, Prometheus and Grafana data were preserved." -ForegroundColor Green
