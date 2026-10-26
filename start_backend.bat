@echo off
echo ====================================================
echo Starting Vulture Bot Backend (FastAPI)
echo ====================================================
cd backend
.\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause
