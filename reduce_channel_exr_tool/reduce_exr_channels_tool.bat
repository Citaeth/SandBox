@echo off
setlocal EnableDelayedExpansion

set "PYTHON_SCRIPT=reduce_channel_tool.py"
set /p USER_PATH=Enter the full name of the shot you want to filter the last TA Layer Export version:
CALL "O:\software\config\rez\rez_init.bat"
CALL rez env location_Bunker project_ numpy sg openimageio opencolorio multi_publish2 python-3 -- python "%PYTHON_SCRIPT%" "%USER_PATH%"

echo.
echo [Done]
pause
