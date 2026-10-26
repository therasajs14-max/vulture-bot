# Vulture Bot — Architecture Documentation

## 1. System Overview

Vulture Bot is designed as a reusable, modular AI platform featuring document intelligence, multi-provider LLM support, and an administrative approval engine for email broadcast automation.

```
       +---------------------------------------------+
       |             Next.js 14 Frontend             |
       |  (Tailwind CSS, Lucide, SSE EventSource)    |
       +----------------------+----------------------+
                              | HTTP / SSE
                              v
       +---------------------------------------------+
       |             FastAPI Backend                 |
       |                                             |
       |  [ Auth & Sessions ]     [ File Parsers ]   |
       |  - Google OAuth 2.0      - CSV / Excel      |
       |  - Signed HttpOnly       - PDF (PyMuPDF)    |
       |  - Role checking         - DOCX / XML / TXT |
       |                                             |
       |  [ AI Service Layer ]    [ Approval Engine ]|
       |  - Ollama (mistral)      - Content Hashing  |
       |  - Google Gemini         - Invalidation     |
       |  - Controlled Tools      - Idempotency      |
       |                                             |
       |  [ Email Service ]                          |
       |  - Mock Provider (Local/Safe)               |
       |  - SMTP / Gmail API                         |
       |  - Safe Personalization Engine              |
       +----------------------+----------------------+
                              |
                     +--------+--------+
                     |                 |
                     v                 v
            +----------------+ +---------------+
            | SQLite/Postgres| | Local Uploads |
            |  Database      | |  Directory    |
            +----------------+ +---------------+
```

## 2. Core Security Invariants

1. **AI Cannot Approve or Send**:
   - The AI Assistant can only draft tasks and propose selection queries.
   - Dispatch requires explicit admin cryptographic approval (`ApprovalRecord`) tied to a SHA-256 hash of the recipients and content.
   - Any modification to draft text or recipient query resets the approval status to `draft` and marks previous approval as `invalidated`.

2. **Template Personalization Protection**:
   - Only explicitly declared placeholders (`{name}`, `{department}`, `{year}`, `{register_number}`) are replaced.
   - Dynamic code evaluation (`eval`, SQL commands, exec) is strictly prohibited.
   - Formula injection protection: Any cell or exported data starting with `=`, `+`, `-`, or `@` is prepended with `'`.

3. **Untrusted File Pipeline**:
   - Uploaded files are streamed to isolated disk paths with random UUID prefixes.
   - HTML content is sanitized; executable macros are ignored.
   - Memory and file-size quotas are enforced on the upload stream.
