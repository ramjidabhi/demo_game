@echo off
title Cyber Viper Game Server
cls
echo ================================================================
echo             CYBER VIPER - NEON ARCADE GAME SERVER
echo ================================================================
echo.
echo  Backend:   Python (Multi-threaded HTTP Server)
echo  Database:  SQLite3 (game_history.db)
echo  URL:       http://localhost:8000
echo.
echo  [IMPORTANT] Keep this Command Prompt window OPEN while playing!
echo  If you close this window, the server will stop.
echo ================================================================
echo.
echo Starting server...
start http://localhost:8000
python server.py
echo.
echo Server has stopped.
pause
