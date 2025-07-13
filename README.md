# QnA

QnA/
├── backend/                # FastAPI app with GPT, LangChain, SQL, RAG
│   ├── main.py             # FastAPI entry point
│   ├── requirements.txt    # Python dependencies
│   ├── .env                # API keys (OpenAI, etc.)
│   ├── router/             # API routes
│   │   └── qna.py          # /ask endpoint logic
│   ├── services/           # LangChain / GPT / SQL / RAG logic
│   │   ├── sql_agent.py
│   │   ├── csv_agent.py
│   │   └── rag_engine.py
│   ├── data/               # Data files and dbs
│   │   ├── chinook.db
│   │   ├── csv_files/
│   │   └── vectordb/       # ChromaDB or FAISS
│   ├── utils/              # Helper utilities
│   │   └── llm_config.py
│   └── notebooks/          # Jupyter notebooks for development
│       ├── test_sql.ipynb
│       └── run_gpt.ipynb

├── frontend/               # React + Vite (TypeScript)
│   ├── public/
│   ├── src/
│   │   ├── components/     # ChatBox, FileUpload, etc.
│   │   ├── pages/
│   │   ├── services/       # API calls to backend
│   │   │   └── api.ts
│   │   └── App.tsx
│   ├── .env                # VITE_BACKEND_URL
│   ├── vite.config.ts
│   ├── package.json
│   └── tsconfig.json

├── README.md               # Project documentation
├── .gitignore
└── deployment/             # Optional deploy configs
    ├── render.yaml         # Render deployment for backend
    └── vercel.json         # Vercel config for frontend
