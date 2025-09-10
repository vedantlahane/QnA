├── QnA/
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── qna_app/
│   ├── models.py      # Conversation, UploadedFile
│   ├── views.py       # Handles UI and calls data_app
│   ├── urls.py
│   ├── forms.py
│   └── templates/
|       |--- index.html
│       ├── chat.html
│       └── upload.html
├── data_app/
│   ├── agent_core/
│   │   ├── agent_graph.py  # Builds the main agent graph
│   │   ├── config.py       # Holds the LoadToolsConfig class
│   │   └── tools/          # Separate file for each agent tool
│   │       ├── pdf_rag_tool.py
│   │       ├── sql_tool.py
│   │       ├── csv_rag_tool.py
│   │       └── tavily_search_tool.py
│   └── manager.py           # Top-level module to manage the agent and data
├── configs/
│   └── tools_config.yml     # Configuration for all agent tools
├── media/             # user uploads
├── .env
└── requirements.txt
