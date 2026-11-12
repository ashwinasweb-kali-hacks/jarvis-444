@echo off
title JARVIS-OS Workshop Daemon (HTTPS / VR)
cd /d "E:\jarvis"
set JARVIS_TLS=1
echo ========================================================
echo    J.A.R.V.I.S. - HTTPS MODE (HEADLESS VR READY)
echo ========================================================
echo Starting JARVIS daemon with a local self-signed certificate.
echo Your browser will warn ONCE. Choose "Advanced" then "Proceed".
echo After that the page is a secure context and WebXR works.
echo.
echo LAN address for the headset: https://<this-pc-ip>:8765/
echo (Your certificate already covers every local IP, so no mismatch.)
echo ========================================================
start "" /b "C:\Users\ARUMUGAM\AppData\Local\Programs\Python\Python314\python.exe" -m jarvis.daemon
timeout /t 3 /nobreak >nul
echo Opening secure HUD on https://127.0.0.1:8765/ ...
start https://127.0.0.1:8765/
echo.
echo Keep this window open. Ctrl+C or close it to stop the daemon.
echo ========================================================
pause
