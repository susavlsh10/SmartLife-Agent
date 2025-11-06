# SmartLife Agent Backend

FastAPI backend for the SmartLife Agent application with authentication and Gemini AI chat integration.

## Features

- 🔐 JWT-based authentication (signup, login, token verification)
- 💬 Chat interface with Google Gemini AI integration
- 📝 SQLite database with SQLAlchemy ORM for user and chat history storage
- 🔒 Password hashing with bcrypt
- 🌐 CORS enabled for frontend communication

## Prerequisites

- Python 3.8+
- pip or poetry

## Setup

1. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Set up environment variables:**
   - Copy `.env.example` to `.env`
   - Add your `SECRET_KEY` (any secure random string)
   - Add your `GEMINI_API_KEY` from [Google AI Studio](https://makersuite.google.com/app/apikey)

```bash
cp .env.example .env
# Edit .env and add your keys
```

3. **Run the server:**
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Authentication

- `POST /api/auth/signup` - Create a new account
  - Body: `{ "email": "user@example.com", "password": "password123", "name": "Optional Name" }`
  - Returns: `{ "user": {...}, "token": "jwt_token" }`

- `POST /api/auth/login` - Login
  - Body: `{ "email": "user@example.com", "password": "password123" }`
  - Returns: `{ "user": {...}, "token": "jwt_token" }`

- `GET /api/auth/verify` - Verify token
  - Headers: `Authorization: Bearer <token>`
  - Returns: `{ "id": "...", "email": "...", "name": "..." }`

### Chat

- `POST /api/chat` - Send a chat message
  - Headers: `Authorization: Bearer <token>`
  - Body: `{ "message": "Hello!" }`
  - Returns: `{ "response": "AI response..." }`

- `GET /api/chat/history` - Get chat history
  - Headers: `Authorization: Bearer <token>`
  - Returns: `[{ "id": "...", "message": "...", "response": "...", "timestamp": "..." }]`

## Database

The application uses SQLite with SQLAlchemy ORM for database management. The database file (`smartlife.db`) is created automatically on first run.

### Models

- **User**: Stores user accounts (id, email, password_hash, name, created_at)
- **ChatHistory**: Stores chat messages (id, user_id, message, response, timestamp)

SQLAlchemy provides:
- Type-safe database operations
- Automatic relationship management
- Easy migrations and schema changes
- Better code organization

## Getting a Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add it to your `.env` file

## Development

Run with auto-reload:
```bash
uvicorn main:app --reload --port 8000
```

Run in production:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Project Structure

```
backend/
├── main.py              # FastAPI app entry point
├── app/
│   ├── __init__.py
│   ├── database.py      # SQLAlchemy database connection and session management
│   ├── db_models.py     # SQLAlchemy ORM models (User, ChatHistory)
│   ├── models.py        # Pydantic models for API requests/responses
│   ├── auth.py          # Authentication utilities
│   ├── gemini_client.py # Gemini AI client
│   └── routers/
│       ├── __init__.py
│       ├── auth.py      # Authentication routes
│       └── chat.py      # Chat routes
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md
```

