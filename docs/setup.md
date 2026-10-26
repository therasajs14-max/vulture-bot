# Vulture Bot — Setup & Operations Guide

## 1. Quick Start (Local Development)

### Prerequisites
- Python 3.12+
- Node.js 18+ and npm
- (Optional) Ollama running locally (`ollama run mistral:latest`)

### Backend Setup
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Backend will start on `http://localhost:8000`. Swagger API documentation is available at `http://localhost:8000/docs`.

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

## 2. AI Provider Configuration

### Free Local AI: Ollama
- Run Ollama locally: `ollama serve`
- Pull mistral: `ollama pull mistral:latest`
- In `.env`:
  ```ini
  AI_PROVIDER=ollama
  OLLAMA_BASE_URL=http://localhost:11434
  OLLAMA_MODEL=mistral:latest
  ```

### Google Gemini API
- Get your free API key from [Google AI Studio](https://aistudio.google.com/)
- In `.env`:
  ```ini
  AI_PROVIDER=gemini
  GEMINI_API_KEY=your_gemini_api_key_here
  GEMINI_MODEL=gemini-1.5-flash
  ```

## 3. Email Provider Modes

- `EMAIL_PROVIDER=mock`: Safe zero-cost mode for local testing. Records sent emails in the database and audit trail without connecting to real mail servers.
- `EMAIL_PROVIDER=smtp`: Production SMTP server (TLS on port 587).
- `EMAIL_PROVIDER=gmail`: Direct Gmail API integration via OAuth.
