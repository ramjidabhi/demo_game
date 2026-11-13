$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

Write-Host "`nStarting CYBER VIPER + SonarQube + Prometheus + Grafana..." -ForegroundColor Cyan
docker compose -f ".\devops-tools\docker-compose.yml" up -d --build

if ($LASTEXITCODE -ne 0) {
    throw "DevSecOps stack could not be started. Review the Docker Compose error above."
}

Write-Host "`nCYBER VIPER DevSecOps stack started." -ForegroundColor Green
Write-Host "Game:       http://localhost:8000"
Write-Host "SonarQube:  http://localhost:9000"
Write-Host "Prometheus: http://localhost:9090"
Write-Host "Grafana:    http://localhost:3000"
Write-Host "Grafana first-login defaults: admin / admin (change it when prompted)." -ForegroundColor Yellow
