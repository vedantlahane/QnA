# QnA Backend

Django-based backend for the AI-Powered Document Q&A System with RAG technology.

## 🚀 Features

- **Django REST API** for frontend communication
- **Document Processing** with PDF and CSV support
- **AI Agent Integration** using LangGraph and OpenAI
- **Vector Database** with FAISS for document embeddings
- **Web Search** integration with Tavily API
- **Authentication** with Django's built-in auth system
- **File Upload** with secure storage

## 🛠️ Tech Stack

- **Django 5.2** - Web framework
- **Python 3.13** - Runtime
- **OpenAI API** - AI language model
- **FAISS** - Vector similarity search
- **LangGraph** - Agent orchestration
- **Tavily API** - Web search
- **SQLite** - Database (development)

## � Installation & Setup

### Prerequisites

- Python 3.13+
- pip (Python package manager)
- Virtual environment (recommended)

### 1. Create Virtual Environment

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Environment Configuration

Create a `.env` file in the backend directory:

```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
DJANGO_SECRET_KEY=your_django_secret_key_here
DEBUG=True
```

### 4. Database Setup

```bash
# Run migrations
python manage.py migrate

# Create superuser (optional)
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

The server will start on `http://localhost:8000`

## 🔧 Available Commands

- `python manage.py runserver` - Start development server
- `python manage.py migrate` - Run database migrations
- `python manage.py makemigrations` - Create new migrations
- `python manage.py createsuperuser` - Create admin user
- `python manage.py collectstatic` - Collect static files for production

## 🌐 API Endpoints

### Authentication
- `POST /auth/login/` - User login
- `POST /auth/logout/` - User logout
- `POST /auth/register/` - User registration

### File Operations
- `POST /api/upload/` - Upload document files
- `GET /api/files/` - List uploaded files

### Chat/Q&A
- `POST /api/chat/` - Send chat message and get AI response
- `GET /api/conversations/` - Get conversation history

### User Management
- `GET /dashboard/` - User dashboard
- `GET /profile/` - User profile

## 📁 Project Structure

```
backend/
├── backend/           # Django project settings
│   ├── __init__.py
│   ├── settings.py    # Django configuration
│   ├── urls.py        # Main URL routing
│   ├── wsgi.py        # WSGI configuration
│   └── asgi.py        # ASGI configuration
├── data_app/          # AI Agent Core
│   ├── __init__.py
│   ├── manager.py     # Agent manager
│   └── agent_core/    # Agent implementation
│       ├── agent_graph.py
│       ├── config.py
│       └── tools/     # Agent tools
├── qna_app/          # Main Django app
│   ├── __init__.py
│   ├── models.py     # Database models
│   ├── views.py      # API views
│   ├── urls.py       # App URLs
│   ├── forms.py      # Forms
│   └── admin.py      # Admin interface
├── theme/            # Templates and static files
│   ├── templates/    # HTML templates
│   ├── static/       # Static assets
│   └── static_src/   # Source assets
├── media/            # Uploaded files
├── data/             # Vector databases and indexes
├── configs/          # Configuration files
├── requirements.txt  # Python dependencies
└── manage.py         # Django management script
```

## 🔑 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for AI responses | Yes |
| `TAVILY_API_KEY` | Tavily API key for web search | Yes |
| `DJANGO_SECRET_KEY` | Django secret key | Yes |
| `DEBUG` | Enable/disable debug mode | No (default: False) |

## 🤝 Development

### Code Style
- Follow PEP 8 Python style guide
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Write tests for new features

### Database
- Use SQLite for development
- PostgreSQL recommended for production
- Run migrations after model changes

### Testing
```bash
# Run tests
python manage.py test

# Run specific app tests
python manage.py test qna_app
```

## 🚀 Deployment

### Production Checklist
- [ ] Set `DEBUG=False` in settings
- [ ] Configure production database
- [ ] Set up static file serving
- [ ] Configure HTTPS
- [ ] Set up proper logging
- [ ] Configure environment variables
- [ ] Run `python manage.py collectstatic`

### Docker (Optional)
```dockerfile
FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 📝 API Documentation

### File Upload
```bash
curl -X POST http://localhost:8000/api/upload/ \
  -H "Content-Type: multipart/form-data" \
  -F "file=@document.pdf"
```

### Chat Query
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main topic of the document?"}'
```

## 🐛 Troubleshooting

### Common Issues

1. **Module not found errors**
   - Ensure virtual environment is activated
   - Reinstall requirements: `pip install -r requirements.txt`

2. **Database errors**
   - Run migrations: `python manage.py migrate`
   - Check database file permissions

3. **API key errors**
   - Verify `.env` file exists and contains correct keys
   - Check API key validity and quotas

4. **Static files not loading**
   - Run: `python manage.py collectstatic`
   - Check `STATIC_ROOT` and `STATIC_URL` settings

## 📄 License

This project is part of the QnA system. See main project license for details.
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
