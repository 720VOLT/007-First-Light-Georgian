@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo *** 007 FIRST LIGHT - GEORGIAN LOCALIZATION ***
echo.
if not exist "%~dp0GeorgianInstaller.exe" (
  echo ERROR: GeorgianInstaller.exe is missing. Extract the whole ZIP first.
  pause
  exit /b 1
)
"%~dp0GeorgianInstaller.exe" install
set "result=%ERRORLEVEL%"
if not "%result%"=="0" (
  echo.
  echo Installation did not complete. Read the error above.
  pause
  exit /b %result%
)
echo.
echo Finished. Launch the game, leave language set to English, and enable subtitles.
pause
