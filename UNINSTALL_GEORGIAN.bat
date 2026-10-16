@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo *** 007 FIRST LIGHT - RESTORE ORIGINAL FILES ***
echo.
if not exist "%~dp0GeorgianInstaller.exe" (
  echo ERROR: GeorgianInstaller.exe is missing. Extract the whole ZIP first.
  pause
  exit /b 1
)
"%~dp0GeorgianInstaller.exe" uninstall
set "result=%ERRORLEVEL%"
if not "%result%"=="0" (
  echo.
  echo Restoration did not complete. KEEP the recovery backups.
  pause
  exit /b %result%
)
echo.
echo Restored!
pause
