# PowerShell Runner for Cyber Viper
Clear-Host
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "            CYBER VIPER - NEON ARCADE GAME SERVER" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host " Backend:   Python (Multi-threaded HTTP Server)" -ForegroundColor White
Write-Host " Database:  SQLite3 (game_history.db)" -ForegroundColor White
Write-Host " URL:       http://localhost:8000" -ForegroundColor White
Write-Host ""
Write-Host " [IMPORTANT] Keep this PowerShell window OPEN while playing!" -ForegroundColor Magenta
Write-Host " If you close this window, the server will stop." -ForegroundColor Magenta
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Opening web browser..." -ForegroundColor Green
Start-Process "http://localhost:8000"
python server.py
Write-Host "Server has stopped." -ForegroundColor Red
Pause
