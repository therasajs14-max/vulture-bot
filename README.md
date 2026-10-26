# Vulture Bot 🦅

> Production-Ready, Multi-Purpose AI Chatbot with Document Intelligence, Student Data Analysis, and Admin-Approved Email Automation.

![Status](https://img.shields.io/badge/Status-Production--Ready-success)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14+-black?logo=next.js&logoColor=white)
![Ollama](https://img.shields.io/badge/AI-Ollama%20%2F%20Gemini-blue)

---

## Key Features

1. **Multi-Purpose AI Assistant**:
   - Streamed natural language chat using either local Ollama (`mistral:latest`, `llama3.1`) or Google Gemini (`gemini-1.5-flash`).
   - Coding assistance, document summarization, reasoning, and data analysis.

2. **File Intelligence & Parser Registry**:
   - Multi-format ingestion: CSV, Excel (.xlsx, .xls), PDF (PyMuPDF), DOCX, TXT, JSON, XML.
   - Automatic column heuristics detection: Name, Register Number, Department, Year, Semester, Section, Email, Phone.
   - Data validation with RFC email checking, duplicate flagging, missing field tracking, and import confirmation summaries.

3. **Natural Language Student Filtering**:
   - Ask in natural language: *"Show all final-year AI & DS students"* or *"Filter students with missing email addresses"*.
   - Filter by department, academic year, class section, and valid email status.
   - Safe CSV/Excel export protected against spreadsheet formula injection.

4. **Task & Email Generation**:
   - Convert instructions into clear, professional announcements and guidelines.
   - Safe template engine with verified placeholders (`{name}`, `{department}`, `{register_number}`).

5. **Mandatory Server-Side Admin Approval**:
   - Complete workflow: `Draft -> Recipient Validation -> Preview -> Admin Approval -> Sending -> Results`.
   - Approval bound cryptographically to content hash (`SHA-256`) and recipient count.
   - Modifying draft text or filters automatically invalidates approval.
   - Idempotency keys prevent duplicate dispatches.
   - Audit trail records all administrative actions.

---

## Quick Start

### 1. Backend
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2. Frontend
```powershell
cd frontend
npm run dev
```

Visit [http://localhost:3000](http://localhost:3000) to start chatting.
API documentation available at [http://localhost:8000/docs](http://localhost:8000/docs).
