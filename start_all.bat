@echo off
echo ====================================================
echo Starting Vulture Bot (Full Stack)
echo ====================================================
start cmd /k "start_backend.bat"
start cmd /k "start_frontend.bat"
echo Services are launching:
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5005
echo ====================================================
