# SmartResume AI - Intelligent Resume Analysis Platform

[![Deploy to Fly.io](https://img.shields.io/badge/Deploy-Fly.io-blueviolet)](https://fly.io)
[![Python](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![React](https://img.shields.io/badge/React-18+-61dafb)](https://reactjs.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688)](https://fastapi.tiangolo.com)

## Overview

SmartResume AI is a comprehensive, AI-powered resume analysis platform that transforms raw resume documents into structured data and provides personalized career guidance. The platform leverages advanced machine learning models to extract entities, analyze compatibility with job descriptions, and generate actionable feedback for career development.

## 🚀 Features

### Core Functionality

- **Document Processing**: Extract text from PDF, DOCX, and TXT files with OCR fallback
- **Entity Extraction**: Advanced NLP models identify skills, experience, and qualifications
- **Semantic Analysis**: Calculate compatibility scores between resumes and job descriptions
- **AI Feedback**: Generate personalized career coaching recommendations using Google Gemini
- **Secure Storage**: Store analysis results with user authentication and data protection

### Technical Capabilities

- **Multi-format Support**: PDF, DOCX, TXT document processing
- **OCR Integration**: Tesseract OCR for image-based text extraction
- **ML Pipeline**: PyTorch, Transformers, and TensorFlow for advanced analysis
- **Real-time Processing**: Asynchronous document processing with progress tracking
- **RESTful API**: Comprehensive API with OpenAPI documentation

## 🏗️ Architecture

### Backend (FastAPI + Python)

- **Framework**: FastAPI with async/await support
- **ML Stack**: PyTorch, Transformers, Sentence-Transformers, SpaCy
- **Database**: Supabase (PostgreSQL) with async drivers
- **Authentication**: JWT-based authentication via Supabase Auth
- **Document Processing**: PDFPlumber, python-docx, Tesseract OCR
- **AI Integration**: Google Gemini API for advanced analysis

### Frontend (React + TypeScript)

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite for fast development and optimized builds
- **UI Components**: shadcn/ui with Tailwind CSS
- **State Management**: React Query for server state management
- **Authentication**: Supabase Auth integration
- **File Upload**: Drag-and-drop interface with progress tracking

## 🛠️ Technology Stack

### Backend Dependencies

```
FastAPI 0.104.1          # Modern web framework
uvicorn[standard] 0.24.0 # ASGI server
pydantic 2.5.0           # Data validation
supabase 2.3.0           # Database and auth
torch 2.1.0+cpu          # Machine learning
transformers 4.35.0      # NLP models
tensorflow-cpu 2.15.0    # Deep learning
sentence-transformers    # Semantic embeddings
spacy 3.7.2             # NLP processing
google-generativeai     # Gemini AI integration
```

### Frontend Dependencies

```
React 18+               # UI framework
TypeScript 5+           # Type safety
Vite 5+                # Build tool
Tailwind CSS 3.4+      # Styling
shadcn/ui              # UI components
React Query            # Server state
Supabase JS            # Backend integration
```

## 📦 Installation & Development

### Prerequisites

- **Python 3.11+** with pip
- **Node.js 20+** with npm
- **Docker** (for containerized deployment)

### Local Development Setup

1. **Clone the repository**

```bash
git clone <repository-url>
cd smartresume-ai
```

2. **Backend Setup**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Frontend Setup**

```bash
cd frontend
npm install
```

4. **Environment Configuration**

```bash
# Backend (.env)
DATABASE_URL=your_supabase_connection_string
GOOGLE_API_KEY=your_gemini_api_key
JWT_SECRET=your_jwt_secret
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_supabase_service_key

# Frontend (.env)
VITE_SUPABASE_URL=your_supabase_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_URL=http://localhost:8000
```

5. **Start Development Servers**

```bash
# Backend (Terminal 1)
cd backend && uvicorn app.main:app --reload --port 8000

# Frontend (Terminal 2)
cd frontend && npm run dev
```

## 🚀 Deployment

### Fly.io Deployment (Recommended)

The application is configured for single-container deployment on Fly.io, combining both frontend and backend services.

1. **Install Fly.io CLI**

```bash
# macOS
brew install flyctl

# Windows
iwr https://fly.io/install.ps1 -useb | iex

# Linux
curl -L https://fly.io/install.sh | sh
```

2. **Login and Deploy**

```bash
fly auth login
fly deploy
```

3. **Set Environment Variables**

```bash
fly secrets set DATABASE_URL="your_connection_string"
fly secrets set GOOGLE_API_KEY="your_api_key"
fly secrets set JWT_SECRET="your_jwt_secret"
fly secrets set SUPABASE_URL="your_supabase_url"
fly secrets set SUPABASE_SERVICE_KEY="your_service_key"
```

### Docker Deployment

```bash
# Build the container
docker build -t smartresume-ai .

# Run locally
docker run -p 8000:8000 -p 3000:3000 smartresume-ai
```

## 📊 Performance & Scalability

- **Response Times**: 95% of requests complete within 30 seconds
- **File Processing**: Supports files up to 10MB
- **Concurrent Users**: Optimized for high-concurrency workloads
- **Rate Limiting**: Configurable rate limits per user/endpoint
- **Caching**: Intelligent model caching for improved performance

## 🔒 Security Features

- **Authentication**: JWT-based authentication with Supabase
- **Authorization**: Role-based access control
- **Data Protection**: Encrypted data storage and transmission
- **Input Validation**: Comprehensive input sanitization
- **Rate Limiting**: Protection against abuse and DoS attacks
- **CORS Configuration**: Secure cross-origin resource sharing

## 📚 API Documentation

The API is fully documented with OpenAPI/Swagger. Access the interactive documentation at:

- **Swagger UI**: `https://your-domain.com/docs`
- **ReDoc**: `https://your-domain.com/redoc`

### Key Endpoints

- `POST /api/v1/upload` - Upload and process resume documents
- `POST /api/v1/analyze` - Analyze resume against job description
- `GET /api/v1/history` - Retrieve analysis history
- `GET /api/v1/health` - System health check

## 🧪 Testing

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# Integration tests
npm run test:e2e
```

## 📈 Monitoring & Observability

- **Health Checks**: Comprehensive system health monitoring
- **Logging**: Structured logging with request tracing
- **Metrics**: Performance and usage metrics collection
- **Error Tracking**: Detailed error reporting and analysis

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

For support, please contact [support@smartresume-ai.com](mailto:support@smartresume-ai.com) or open an issue in the GitHub repository.

---

**SmartResume AI** - Empowering careers through intelligent resume analysis.
