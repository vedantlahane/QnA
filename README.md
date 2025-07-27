# QnA

QnA/
├── backend/                    # Backend with FastAPI + GPT + LangChain + SQL
│   ├── main.py                 # FastAPI entry point
│   ├── requirements.txt        # Python dependencies
│   ├── .env                    # API keys (OpenAI, etc.)
│
│   ├── router/                 # API routes
│   │   └── qna.py              # /ask, /upload, etc.
│
│   ├── services/               # GPT/LangChain/RAG core logic
│   │   ├── sql_agent.ipynb     # SQL agent logic (Jupyter)
│   │   ├── csv_agent.ipynb     # CSV agent logic (Jupyter)
│   │   └── rag_engine.ipynb    # RAG + vector search (Jupyter)
│
│   ├── data/                   # Data files and DBs
│   │   ├── chinook.db
│   │   ├── csv_files/
│   │   └── vectordb/           # ChromaDB / FAISS store
│
│   ├── utils/                  # Utilities and LLM configs
│   │   └── llm_config.py
│
│   └── notebooks/              # Dev and debug notebooks
│       ├── test_sql.ipynb
│       ├── run_rag.ipynb
│       └── playground.ipynb

├── frontend/                   # React + Vite (TypeScript)
│   ├── public/
│   ├── src/
│   │   ├── components/         # ChatBox, FileUpload, etc.
│   │   ├── pages/
│   │   ├── services/           # API service layer
│   │   │   └── api.ts
│   │   └── App.tsx
│   ├── .env                    # VITE_BACKEND_URL
│   ├── vite.config.ts
│   ├── package.json
│   └── tsconfig.json

├── README.md                   # Project documentation
├── .gitignore
└── deployment/                 # Deployment configs (optional)
    ├── render.yaml             # For backend (Python)
    └── vercel.json             # For frontend (React + Vite)
