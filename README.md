# Quest2Travel — Enterprise AI Travel Assistant

An AI-powered travel assistant combining conversational AI (Gemini 2.5 Flash) with real travel APIs for flights, trains, buses, hotels, and car rentals.

## Features

- **Conversation Memory** — remembers your origin, destination, class, budget across turns
- **Fuzzy NLU** — understands "Delhii to Mumabi", "Ahemdabad to Banglore"
- **Real APIs** — Amadeus (flights), Booking.com (hotels), RailYatri (trains)
- **Intelligent Fallback** — auto-retries failing APIs, falls back to realistic mock data
- **Dynamic Geocoding** — NO hardcoded coordinates; all resolved via Nominatim/Google
- **Follow-up Queries** — "Only flights" → "Business class" → "Under ₹6000" all work
- **Context Reset** — new route detected → context resets automatically
- **Dark Mode** — full light/dark mode support
- **Session History** — all conversations stored in MongoDB

## Quick Start

```bash
# 1. Start MongoDB
brew services start mongodb-community@7.0  # macOS

# 2. Backend
cd backend && python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add GEMINI_API_KEY at minimum
uvicorn main:app --reload --port 8000

# 3. Frontend (new terminal)
cd frontend && npm install
cp .env.local.example .env.local
npm run dev

# 4. Open http://localhost:3000
```

See [docs/SETUP.md](docs/SETUP.md) for the complete setup guide.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, React, TypeScript, Tailwind CSS |
| State | Zustand + React Query |
| Backend | FastAPI, Python 3.11, AsyncIO |
| AI | Google Gemini 2.5 Flash |
| Database | MongoDB (Motor async driver) |
| NLU | RapidFuzz for fuzzy city matching |
| Geocoding | OpenStreetMap Nominatim (dynamic, no hardcoded coords) |
| HTTP | HTTPX (async) |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/chat | Send message, get AI response + travel results |
| GET | /api/chat/{id}/history | Get conversation history |
| GET | /api/chat/{id}/context | Get current travel context |
| DELETE | /api/chat/{id}/context | Reset travel context |
| GET | /api/sessions | List all sessions |
| DELETE | /api/sessions/{id} | Delete session |
| GET | /api/travel/{id}/searches | Get search history |
| POST | /api/travel/filter | Apply filters to last search |
| GET | /api/health | Health check |
| GET | /api/docs | Swagger UI |
