@echo off
echo ==========================================
echo   Phillip Jong Message Manager
echo ==========================================
echo.
echo [1] Sync/Update Messages (Download new)
echo [2] Launch Local Gallery
echo [3] Exit
echo.
set /p opt="Select an option (1-3): "

if "%opt%"=="1" (
    echo Syncing...
    python sync.py
    pause
    goto end
)
if "%opt%"=="2" (
    echo Launching gallery server on http://localhost:5000 ...
    echo (Keep this window open while browsing)
    start "" "http://localhost:5000"
    python server.py
    goto end
)
:end
exit
