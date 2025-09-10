# QnA - AI-Powered Document Q&A System

A sophisticated Django-based web application that combines Retrieval-Augmented Generation (RAG) with a conversational AI agent to provide intelligent answers about uploaded documents.

## 🚀 Features

- **Document Upload & Processing**: Support for PDF and CSV files
- **Intelligent Q&A**: Ask natural language questions about your documents
- **RAG Technology**: Uses vector embeddings and similarity search for accurate answers
- **Multi-Modal Agent**: Combines document analysis with web search capabilities
- **Modern UI**: Clean, responsive interface built with Tailwind CSS
- **Real-time Conversations**: Maintains conversation context and history

## 📁 Project Structure

```
QnA/
├── QnA/                    # Django project settings
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py         # Django settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py
├── qna_app/               # Main Django application
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── forms.py           # File upload and form handling
│   ├── models.py          # Database models (UploadedFile, Conversation)
│   ├── tests.py
│   ├── urls.py            # App URL patterns
│   └── views.py           # UI views and API endpoints
├── data_app/              # AI Agent Core
│   ├── __init__.py
│   ├── manager.py         # Agent manager and tool orchestration
│   └── agent_core/        # Agent implementation
│       ├── __init__.py
│       ├── agent_graph.py # LangGraph agent definition
│       ├── config.py      # Configuration management
│       └── tools/         # Agent tools
│           ├── __init__.py
│           ├── csv_rag_tool.py    # CSV document Q&A
│           ├── pdf_rag_tool.py    # PDF document Q&A
│           ├── sql_tool.py        # SQL database queries
│           └── tavily_search_tool.py # Web search
├── theme/                 # UI Templates and Assets
│   ├── __init__.py
│   ├── apps.py
│   ├── static/            # Compiled static files
│   ├── static_src/        # Source static files
│   │   ├── node_modules/
│   │   └── src/
│   └── templates/         # HTML templates
│       └── base.html      # Base template
├── configs/               # Configuration files
│   └── tools_config.yml   # Agent tool configurations
├── data/                  # Vector database storage
│   ├── faiss_index_1/     # PDF document vectors
│   ├── faiss_index_csv_1/ # CSV document vectors
│   └── faiss_index_4/     # Additional PDF vectors
├── media/                 # User uploads
│   └── uploads/           # Uploaded files
├── logs/                  # Application logs
│   └── django.log
├── test_*.py             # Test scripts
├── manage.py             # Django management script
├── requirements.txt      # Python dependencies
├── .env                  # Environment variables
├── .gitignore
├── Procfile.tailwind     # Tailwind CSS build process
└── README.md
```

## 🛠️ Technology Stack

### Backend
- **Django**: Web framework
- **LangChain**: LLM orchestration
- **LangGraph**: Agent workflow management
- **OpenAI GPT-4**: Primary LLM
- **FAISS**: Vector database for document embeddings
- **Tavily**: Web search API

### Frontend
- **Tailwind CSS**: Utility-first CSS framework
- **DaisyUI**: Component library
- **HTML5**: Semantic markup

### Infrastructure
- **PostgreSQL/SQLite**: Database
- **Redis** (optional): Caching and session storage

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for Tailwind CSS)
- OpenAI API key
- Tavily API key

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd QnA
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js dependencies**
   ```bash
   cd theme/static_src
   npm install
   ```

5. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

6. **Run database migrations**
   ```bash
   cd ..
   python manage.py migrate
   ```

7. **Build static assets**
   ```bash
   python manage.py tailwind build
   ```

8. **Start the development server**
   ```bash
   python manage.py runserver
   ```

9. **Access the application**
   Open http://localhost:8000 in your browser

## 🔧 Configuration

### Environment Variables (.env)
```env
OPEN_AI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
DJANGO_SETTINGS_MODULE=QnA.settings
DEBUG=True
SECRET_KEY=your_secret_key
```

### Agent Configuration (configs/tools_config.yml)
```yaml
primary_agent:
  llm: "gpt-4o-mini"
  temperature: 0.1

pdf_rag:
  embedding_model: "text-embedding-3-small"
  chunk_size: 1000
  chunk_overlap: 200

csv_rag:
  embedding_model: "text-embedding-3-small"
  chunk_size: 500
  chunk_overlap: 50
```

## 📖 Usage

### Uploading Documents
1. Navigate to the upload page
2. Select PDF or CSV files
3. Files are automatically processed and indexed

### Asking Questions
1. Use the chat interface
2. Ask questions in natural language
3. The agent will:
   - Search relevant documents using RAG
   - Provide web search results if needed
   - Maintain conversation context

### Example Queries
- "What are Vedant Lahane's technical skills?"
- "Show me the total earnings from the CSV file"
- "Summarize the main points from the uploaded PDF"
- "What are the latest trends in AI development?"

## 🧪 Testing

### Running Tests
```bash
# Run agent tests
python test_agent.py

# Run comprehensive tests
python test_comprehensive.py

# Run Django tests
python manage.py test
```

### Test Coverage
- ✅ Agent graph construction
- ✅ Tool registration and execution
- ✅ Document processing and indexing
- ✅ RAG functionality
- ✅ Web search integration
- ✅ Conversation memory

## 🔍 API Endpoints

### Document Management
- `POST /upload/` - Upload documents
- `GET /files/` - List uploaded files

### Chat Interface
- `GET /chat/` - Chat interface
- `POST /chat/message/` - Send message to agent

### Authentication
- `/accounts/login/` - User login
- `/accounts/register/` - User registration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT models
- LangChain/LangGraph for agent framework
- FAISS for vector search
- Tailwind CSS for styling
- Django community for the framework

## 📞 Support

For questions or issues:
- Create an issue on GitHub
- Check the documentation
- Review the test files for examples
