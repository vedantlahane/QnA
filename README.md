# QnA – Animated, AI-assisted document answers

![Working](https://img.shields.io/badge/status-working-brightgreen)

QnA is a full-stack workspace that lets teams upload structured or unstructured documents and interrogate them through a conversational agent. The backend blends Django REST Framework with LangChain/LangGraph tooling, while the frontend pairs React + TypeScript with motion-first UI powered by GSAP and Framer Motion.

## 🖼️ Preview

<div align="center">
	<img src="frontend/public/Axon1.png" alt="QnA dashboard hero" width="30%" />
	<img src="frontend/public/Axon2.png" alt="Document management view" width="30%" />
	<img src="frontend/public/Axon3.png" alt="Conversation flow" width="30%" />
</div>

---

## 🧱 Tech stack

| Layer | Technologies |
| --- | --- |
| Backend | Django 5 · Django REST Framework · Token auth · LangChain · LangGraph · FAISS |
| Frontend | React 19 · Vite · TypeScript · GSAP · Framer Motion |
| Tooling | Pytest/Django test runner · ESLint · Vite build |

---

## ✨ Highlights

- Secure auth (register, login, logout, profile) with token-based APIs.
- Document ingestion for PDF, CSV, and SQLite/SQL dumps with automatic RAG tool registration.
- In-app database connector to swap between local SQLite files and hosted SQL instances per account.
- Animated dashboard: GSAP hero treatments and Framer Motion for conversations, document cards, and chat flows.
- Conversation manager with persistent history, document attachments, and streaming-friendly agent responses (falls back to a stub model when API keys are missing so tests still pass).
- Tavily web search tool wired into the LangGraph agent for fresh context.

---

## 🚀 Quick start

### 0. Requirements

- Python **3.13+**
- Node.js **18+** (or newer LTS)
- Valid **OpenAI** and **Tavily** API keys (keep them secret; never commit real keys – use sample placeholders when sharing)

### 1. Clone

```bash
git clone <repository-url>
cd QnA
```

### 2. Backend setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env            # create if one doesn’t exist
# populate OPENAI/TAVILY/DJANGO keys (keep the file out of source control)
# adjust database settings in .env if you prefer a hosted SQL instance

python manage.py migrate
python manage.py collectstatic --noinput  # required before deployment so assets land in STATIC_ROOT
python manage.py runserver
```

### 3. Frontend setup

```bash
cd ../frontend
npm install

cp .env.example .env            # optional helper
echo "VITE_API_BASE_URL=http://localhost:8000/api" >> .env

npm run dev                     # launches on http://localhost:5173
```

### 4. URLs

- Web app: http://localhost:5173
- API root: http://localhost:8000/api/
- Django admin: http://localhost:8000/admin/

---

## 🔐 Environment variables

### Backend (`backend/.env`)

```env
OPENAI_API_KEY=sk-...
OPEN_AI_API_KEY=sk-...         # maintained for libraries expecting this variant
TAVILY_API_KEY=tvly-...
DJANGO_SECRET_KEY=super-secret
DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
# Database (pick one of the following configurations)
# 1. Local SQLite (default): optional overrides
SQLITE_DB_NAME=db.sqlite3       # filename relative to backend/ (default)
SQLITE_DB_PATH=/abs/path/to/db  # alternative absolute/relative path
# 2. External SQL database (PostgreSQL/MySQL/etc.)
DATABASE_URL=postgres://user:pass@host:5432/dbname
DATABASE_CONN_MAX_AGE=600       # optional persistent connection lifespan in seconds
DATABASE_SSL_REQUIRE=True       # set to true/false depending on hosting requirements
# Static files
STATIC_ROOT=staticfiles        # optional – leave blank to fall back to backend/staticfiles
STATIC_URL=/static/            # must include the leading/trailing slash
```

> **Static asset tip:** `collectstatic` writes into `STATIC_ROOT`. When deploying (or when running the Ansible playbook), ensure this directory exists and is writable. Set `STATIC_ROOT` to an absolute path if the default `backend/staticfiles` does not live on the same filesystem.

> **Security tip:** Keep `.env` files out of commits. Rotate keys immediately if they are exposed.

### Frontend (`frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

When deploying, point `VITE_API_BASE_URL` at the public API host.

---

## 🧪 Quality checks

Run these after making changes to ensure everything still works:

```bash
# Backend (from backend/)
source venv/bin/activate
python manage.py test qna_app

# Frontend (from frontend/)
npm run lint
npm run build
```

The backend test suite uses a stub LLM when OpenAI credentials are missing, so CI can run without external calls.

---

## 📁 Key directories

```
QnA/
├── backend/
│   ├── backend/          # Django settings and URLs
│   ├── qna_app/          # REST endpoints, serializers, tests
│   ├── data_app/         # Agent orchestration + tools
│   ├── media/uploads/    # User uploads (gitignored)
│   └── requirements.txt
└── frontend/
	├── src/
	│   ├── components/   # AuthPanel, ConversationSidebar, etc.
	│   ├── api.ts        # Typed API client
	│   └── App.tsx       # Animated dashboard shell
	├── public/
	└── package.json
```

---

## 🌐 API surface

All endpoints are prefixed with `/api/`.

### Auth
- `POST /auth/register/`
- `POST /auth/login/`
- `POST /auth/logout/`
- `GET  /auth/me/`

### Documents
- `GET    /files/` – list the current user’s uploads
- `POST   /files/` – upload a new file (multipart form-data)
- `DELETE /files/{id}/`

### Conversations & chat
- `GET  /conversations/`
- `GET  /conversations/{id}/`
- `POST /chat/` – send a prompt (optionally with `conversation_id`, `title`, and `document_ids`)

Responses return conversation objects with nested messages for easy frontend consumption.

---

## 🖥️ Frontend UX notes

- The header “Atlas Q&A” hero animates in via GSAP timeline sequencing.
- Conversations, documents, and messages animate with Framer Motion.
- File selection chips show processed state; unprocessed files are automatically disabled until ingestion completes.
- Without valid OpenAI/Tavily keys, the UI still works and displays a graceful fallback response (“LLM backend is not configured”).

---

## 🛠️ Developer tips

- Regenerate migrations when models change: `python manage.py makemigrations qna_app`.
- Clear FAISS/vector stores (in `backend/data/`) if you need a clean slate.
- Use `npm run preview` to smoke-test the production build locally.
- When adding new environment variables, document them here to keep onboarding smooth.

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

Made with ❤️ by the QnA team – animated insight from your documents.
