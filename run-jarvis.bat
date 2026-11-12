@echo off
title JARVIS-OS Workshop Daemon
cd /d "E:\jarvis"
echo ========================================================
echo        J.A.R.V.I.S. - STARK INDUSTRIES WORKSHOP
echo ========================================================
echo Starting JARVIS AI Daemon (OAuth + Neural Speech)...
start "" /b "C:\Users\ARUMUGAM\AppData\Local\Programs\Python\Python314\python.exe" -m jarvis.daemon
timeout /t 2 /nobreak >nul
echo Opening Workshop Glass HUD on http://127.0.0.1:8765/ ...
start http://127.0.0.1:8765/
echo.
echo JARVIS is active and standing by.
echo Keep this window open in background.
echo ========================================================
pause
