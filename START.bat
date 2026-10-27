@echo off
setlocal
cd /d "%~dp0"
set "PATH=%~dp0runtime\jre\bin;%~dp0python;%PATH%"
set "PYTHONUTF8=1"
"%~dp0python\python.exe" "%~dp0launch.py" %*
if errorlevel 1 (
  echo.
  echo GLIA Center ATP Studio could not start. Please keep this window for the error details.
  echo See docs\user-guide.html
  pause
)
endlocal
