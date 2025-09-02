QnA/
├── QnA/                      # Core project folder
│   ├── settings.py           # Project settings (DB, API keys)
│   ├── urls.py               # Root URL routing
│   └── wsgi.py
├── qna_app/                  # Main app (Q&A logic)
│   ├── models.py             # Database models
│   ├── views.py              # Q&A processing logic
│   ├── urls.py               # App-specific routes
│   └── templates/
│       └── chat.html         # Chat UI
├── data_app/                 # Data handling app
│   └── management/commands/
│       └── prepare_db.py     # Custom data command
├── .env                      # Environment variables
└── requirements.txt          # Dependencies
