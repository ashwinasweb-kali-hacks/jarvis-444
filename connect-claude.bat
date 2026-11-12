@echo off
title Connect Claude Account via OAuth
cd /d "E:\jarvis"
echo ========================================================
echo        CONNECT CLAUDE ACCOUNT VIA OAUTH
echo ========================================================
echo Launching official Claude.ai OAuth login in your browser...
echo.
& "C:\Users\ARUMUGAM\AppData\Local\Programs\Python\Python314\python.exe" -m jarvis.claude_oauth
pause
