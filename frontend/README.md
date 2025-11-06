# SmartLife Agent

Plan your life and get the upper hand with SmartLife Agent

## Features

- 🔐 **Authentication**: Secure login and signup system with token-based authentication
- 💬 **Chat Interface**: Clean, modern chat UI for communicating with the backend
- 🧩 **Modular Architecture**: Easy to extend with new features and pages
- ⚡ **Fast & Lightweight**: Built with Vite, React, and TypeScript for optimal performance

## Tech Stack

- **React 18** - UI library
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **React Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS framework

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn
- Python 3.8+ and pip

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env and add:
# - SECRET_KEY (any secure random string)
# - GEMINI_API_KEY (get from https://makersuite.google.com/app/apikey)
```

4. Start the backend server:
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### Frontend Setup

1. Install dependencies:
```bash
npm install
```

2. Create a `.env` file in the root directory (optional):
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

3. Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Building for Production

```bash
npm run build
```

The production build will be in the `dist` directory.

## Project Structure

```
src/
├── components/       # Reusable UI components
│   └── Layout.tsx   # Main layout with navigation
├── contexts/         # React contexts
│   └── AuthContext.tsx  # Authentication state management
├── pages/           # Page components
│   ├── Login.tsx    # Login page
│   ├── Signup.tsx   # Signup page
│   └── Chat.tsx     # Chat interface page
├── services/        # API services
│   └── api.ts       # Backend API client
├── App.tsx          # Main app component with routing
├── main.tsx         # Application entry point
└── index.css        # Global styles
```

## Backend

The backend is a FastAPI application located in the `backend/` directory. See [backend/README.md](backend/README.md) for detailed setup instructions.

### Quick Start

1. Install dependencies: `pip install -r backend/requirements.txt`
2. Set up `.env` file with `SECRET_KEY` and `GEMINI_API_KEY`
3. Run: `uvicorn main:app --reload --port 8000`

## Backend API Endpoints

The backend provides the following API endpoints:

### Authentication
- `POST /api/auth/signup` - Create a new account
  - Request: `{ email: string, password: string, name?: string }`
  - Response: `{ user: { id, email, name? }, token: string }`
- `POST /api/auth/login` - Login with email and password
  - Request: `{ email: string, password: string }`
  - Response: `{ user: { id, email, name? }, token: string }`
- `GET /api/auth/verify` - Verify authentication token
  - Headers: `Authorization: Bearer <token>`
  - Response: `{ id: string, email: string, name?: string }`

### Chat
- `POST /api/chat` - Send a chat message (powered by Google Gemini AI)
  - Headers: `Authorization: Bearer <token>`
  - Request: `{ message: string }`
  - Response: `{ response: string }`
- `GET /api/chat/history` - Get chat history
  - Headers: `Authorization: Bearer <token>`
  - Response: `Array<{ id, message, response, timestamp }>`

## Adding New Features

The application is designed to be easily extensible:

1. **Add a new page**: Create a component in `src/pages/` and add a route in `App.tsx`
2. **Add API endpoints**: Extend `src/services/api.ts` with new API functions
3. **Add new contexts**: Create context files in `src/contexts/` for shared state
4. **Add components**: Place reusable components in `src/components/`

## Development

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
