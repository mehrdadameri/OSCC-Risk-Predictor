@echo off
setlocal
cd /d "%~dp0"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
  echo Local environment was not found.
  echo Running installer first...
  call "%~dp0install.bat"
)

echo.
echo Starting OSCC Survival Risk Predictor...
echo The browser should open at http://localhost:8502
echo Keep this window open while using the app.
echo.
"%PYTHON_EXE%" "%~dp0run_app.py"
pause

