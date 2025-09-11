# QnA - AI-Powered Document Q&A System

A full-stack web application that combines Retrieval-Augmented Generation (RAG) with a conversational AI agent to provide intelligent answers about uploaded documents.

## 🏗️ Architecture

This project consists of two main components:

- **Frontend**: React + TypeScript + Vite application
- **Backend**: Django REST API with AI agent integration

## 🚀 Quick Start

### Prerequisites

- **Python 3.13+** for backend
- **Node.js 18+** for frontend
- **OpenAI API Key** (for AI responses)
- **Tavily API Key** (for web search)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd QnA
```

### 2. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Run migrations
python manage.py migrate

# Start backend server
python manage.py runserver
```

### 3. Frontend Setup

```bash
# Open new terminal, navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access the Application

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin/

## 🔑 Environment Configuration

Create `.env` files in both frontend and backend directories:

### Backend (.env)
```env
OPENAI_API_KEY=your_openai_api_key_here
TAVILY_API_KEY=your_tavily_api_key_here
DJANGO_SECRET_KEY=your_django_secret_key_here
DEBUG=True
```

### Frontend (.env)
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## 🎯 Features

### Core Functionality
- **Document Upload**: Support for PDF and CSV files
- **AI Q&A**: Natural language questions about documents
- **RAG Technology**: Vector embeddings and similarity search
- **Web Search**: Integrated web search capabilities
- **Conversation History**: Maintains chat context
- **User Authentication**: Secure login/registration

### Technical Features
- **Real-time Chat**: WebSocket-based communication
- **File Processing**: Automatic document parsing and indexing
- **Vector Database**: FAISS for efficient similarity search
- **Multi-modal Agent**: Combines document analysis with web search
- **Responsive UI**: Mobile-friendly interface

## 📁 Project Structure

```
QnA/
├── backend/              # Django Backend
│   ├── backend/          # Django Project Settings
│   ├── qna_app/          # Main Django App
│   ├── data_app/         # AI Agent Core
│   ├── theme/            # Templates & Static Files
│   ├── media/            # Uploaded Files
│   ├── data/             # Vector Databases
│   ├── requirements.txt  # Python Dependencies
│   └── README.md         # Backend Documentation
├── frontend/             # React Frontend
│   ├── src/              # React Source Code
│   ├── public/           # Static Assets
│   ├── package.json      # Node Dependencies
│   └── README.md         # Frontend Documentation
├── .env                  # Environment Variables
└── README.md             # This file
```

## 🔧 Development

### Backend Development
```bash
cd backend
source venv/bin/activate
python manage.py runserver
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Database Management
```bash
cd backend
source venv/bin/activate
python manage.py makemigrations
python manage.py migrate
```

## 🚀 Deployment

### Backend Deployment
1. Set `DEBUG=False` in settings
2. Configure production database (PostgreSQL recommended)
3. Set up static file serving
4. Configure environment variables
5. Run `python manage.py collectstatic`

### Frontend Deployment
```bash
cd frontend
npm run build
# Deploy the dist/ folder to your web server
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 API Documentation

### Authentication Endpoints
- `POST /auth/login/` - User login
- `POST /auth/logout/` - User logout
- `POST /auth/register/` - User registration

### File Operations
- `POST /api/upload/` - Upload documents
- `GET /api/files/` - List user files

### Chat/Q&A
- `POST /api/chat/` - Send message to AI
- `GET /api/conversations/` - Get chat history

## 🐛 Troubleshooting

### Common Issues

**Backend Issues:**
- Ensure virtual environment is activated
- Check API keys in `.env` file
- Run `python manage.py migrate` if database errors

**Frontend Issues:**
- Ensure backend is running on port 8000
- Check `VITE_API_BASE_URL` in frontend `.env`
- Clear browser cache if API calls fail

**General Issues:**
- Check firewall settings for port conflicts
- Ensure all dependencies are installed
- Verify Python/Node versions meet requirements

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- OpenAI for GPT models
- Tavily for web search API
- FAISS for vector similarity search
- LangGraph for agent orchestration
