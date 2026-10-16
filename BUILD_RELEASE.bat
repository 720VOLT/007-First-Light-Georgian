@echo off
setlocal
cd /d "%~dp0"
echo.
echo 007 FIRST LIGHT - GEORGIAN OFFLINE RELEASE BUILDER
 echo.
echo Publisher/developer ONLY - players do NOT need to run this file.
echo The build downloads the Windows runtime and dependency wheels ONCE.
echo The resulting release ZIP requires no network and no system Python.
echo.
py -3 build_offline_release.py
if errorlevel 1 (
  echo.
  echo Build failed. See the error above.
  pause
  exit /b 1
)
echo.
echo Release is ready inside the dist folder. Test before uploading to Nexus.
pause
