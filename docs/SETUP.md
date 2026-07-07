# Quest2Travel — Complete Setup & Run Guide

## Table of Contents
1. Prerequisites
2. Project Structure
3. MongoDB Setup
4. Backend Setup
5. Frontend Setup
6. API Key Setup
7. Running the Project
8. Testing Guide
9. Troubleshooting

---

## 1. Prerequisites

Install the following before starting:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org |
| Node.js | 18+ | https://nodejs.org |
| MongoDB Community | 7.0+ | https://mongodb.com/try/download/community |
| MongoDB Compass | Latest | https://mongodb.com/try/download/compass |
| Git | Any | https://git-scm.com |

---

## 2. Project Structure

```
quest2travel/
├── backend/
│   ├── main.py                   # FastAPI app entry point
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/
│   │   └── settings.py           # All config via environment variables
│   ├── database/
│   │   └── connection.py         # MongoDB connection + indexes
│   ├── models/
│   │   └── travel.py             # Pydantic models for all data types
│   ├── memory/
│   │   └── conversation.py       # Conversation context manager
│   ├── agents/
│   │   └── gemini_agent.py       # Gemini 2.5 Flash AI integration
│   ├── services/
│   │   ├── chat.py               # Chat orchestration service
│   │   ├── travel_search.py      # Travel search + filtering
│   │   └── geocoding.py          # Dynamic location resolution
│   ├── api_clients/
│   │   ├── flights.py            # Amadeus flights client
│   │   └── travel.py             # Hotels, trains, buses, cars clients
│   ├── routers/
│   │   ├── chat.py               # /api/chat endpoints
│   │   └── sessions.py           # /api/sessions + /api/travel endpoints
│   └── utils/
│       ├── nlu.py                # Fuzzy NLU + city resolution
│       └── fallback.py           # Retry decorator + mock data generators
│
└── frontend/
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    └── src/
        ├── app/
        │   ├── page.tsx          # Main chat UI page
        │   ├── layout.tsx        # Root layout
        │   ├── providers.tsx     # React Query + toast
        │   └── globals.css
        ├── components/
        │   ├── chat/
        │   │   ├── ChatMessage.tsx
        │   │   └── ChatInput.tsx
        │   ├── travel/
        │   │   ├── ResultCards.tsx  # All travel result cards
        │   │   ├── flights/
        │   │   ├── hotels/
        │   │   ├── trains/
        │   │   ├── buses/
        │   │   └── cars/
        │   ├── layout/
        │   │   └── Sidebar.tsx
        │   └── ui/
        │       └── MockDisclaimer.tsx
        ├── hooks/
        │   └── useChat.ts
        ├── store/
        │   └── chat.ts           # Zustand state
        ├── lib/
        │   ├── api.ts            # Axios API client
        │   └── utils.ts
        └── types/
            └── index.ts          # All TypeScript types
```

---

## 3. MongoDB Setup

### Install MongoDB Community Server

**macOS (Homebrew):**
```bash
brew tap mongodb/brew
brew install mongodb-community@7.0
brew services start mongodb-community@7.0
```

**Windows:**
1. Download installer from https://mongodb.com/try/download/community
2. Run installer (choose "Complete" setup)
3. MongoDB runs as a Windows Service automatically

**Ubuntu/Debian:**
```bash
curl -fsSL https://pgp.mongodb.com/server-7.0.asc | sudo gpg -o /usr/share/keyrings/mongodb-server-7.0.gpg --dearmor
echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-7.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/7.0 multiverse" | sudo tee /etc/apt/sources.list.d/mongodb-org-7.0.list
sudo apt-get update && sudo apt-get install -y mongodb-org
sudo systemctl start mongod && sudo systemctl enable mongod
```

### Verify MongoDB is running
```bash
mongosh --eval "db.runCommand({ connectionStatus: 1 })"
# Should print: ok: 1
```

### MongoDB Compass Setup
1. Download and install MongoDB Compass from https://mongodb.com/try/download/compass
2. Open Compass
3. Connection string: `mongodb://localhost:27017`
4. Click "Connect"
5. The `quest2travel` database and collections are auto-created when you first run the backend

---

## 4. Backend Setup

```bash
# Navigate to backend
cd quest2travel/backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys (see section 6)
```

---

## 5. Frontend Setup

```bash
# Navigate to frontend
cd quest2travel/frontend

# Install Node.js dependencies
npm install

# Set up environment variables
cp .env.local.example .env.local
# Edit .env.local if your backend runs on a different port
```

---

## 6. API Key Setup

Edit `backend/.env` and fill in the keys you have:

### Required (Core Functionality)
```env
GEMINI_API_KEY=your_key_here
```
Get from: https://aistudio.google.com/app/apikey (Free tier available)

### Optional (Live Travel Data — fallback to mock if not set)

**Amadeus (Flights):**
1. Go to https://developers.amadeus.com
2. Create account → New App
3. Use TEST environment (free, no credit card)
```env
AMADEUS_CLIENT_ID=your_client_id
AMADEUS_CLIENT_SECRET=your_secret
```

**Booking.com Hotels via RapidAPI:**
1. Go to https://rapidapi.com/apidojo/api/booking
2. Subscribe (free tier available)
```env
BOOKING_API_KEY=your_rapidapi_key
```

**Trains (RailYatri via RapidAPI):**
1. Go to https://rapidapi.com/search/trains
2. Subscribe to a trains API
```env
RAILYATRI_API_KEY=your_key
```

> **Note:** If API keys are not set, the system automatically returns realistic mock data with a disclaimer. The app is fully functional without any API keys — just with sample data.

---

## 7. Running the Project

### Terminal 1 — Start Backend
```bash
cd quest2travel/backend
source venv/bin/activate  # Windows: venv\Scripts\activate
uvicorn main:app --reload --port 8000
```

Expected output:
```
INFO:     Started server process [...]
INFO:     Waiting for application startup.
INFO:     Connected to MongoDB: quest2travel
INFO:     Database indexes created
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Terminal 2 — Start Frontend
```bash
cd quest2travel/frontend
npm run dev
```

Expected output:
```
▲ Next.js 14.2.3
- Local:        http://localhost:3000
- Ready in 2.1s
```

### Open in Browser
- **App:** http://localhost:3000
- **API Docs:** http://localhost:8000/api/docs
- **Health Check:** http://localhost:8000/api/health

---

## 8. Testing Guide

### Test 1: Basic Greeting
```
User: Hello
Expected: Friendly greeting from Gemini AI
```

### Test 2: Fuzzy City Matching
```
User: Delhii to Mumabi flights
Expected: Resolves to "Delhi to Mumbai" and searches flights
```

### Test 3: Conversation Memory (Follow-up Queries)
```
Step 1: "Delhi to Mumbai"
         → Shows all travel options

Step 2: "Only flights"
         → Filters to flights only

Step 3: "Business class"
         → Filters to business class flights

Step 4: "Under ₹20000"
         → Filters business class flights under ₹20,000

Step 5: "5-star hotel"
         → Remembers destination=Mumbai, searches 5-star hotels
```

### Test 4: Context Reset
```
Step 1: "Delhi to Mumbai flights"
         → Delhi→Mumbai context set

Step 2: "Mumbai to Goa"
         → Context RESETS, new search for Mumbai→Goa
```

### Test 5: API Docs Testing
Visit http://localhost:8000/api/docs and test:
- POST /api/chat with `{"message": "Delhi to Goa flights"}`
- GET /api/sessions — see all sessions
- GET /api/chat/{session_id}/context — see current travel context

### Test 6: MongoDB Compass Verification
1. Open Compass → Connect to `mongodb://localhost:27017`
2. Navigate to `quest2travel` database
3. Check `sessions` — should have a document with `travel_context`
4. Check `messages` — should have all user + assistant messages
5. Check `travel_searches` — should have search result documents

---

## 9. Troubleshooting

### MongoDB connection refused
```bash
# Check if MongoDB is running
mongosh --eval "db.runCommand({ connectionStatus: 1 })"

# Start MongoDB
# macOS: brew services start mongodb-community@7.0
# Linux: sudo systemctl start mongod
# Windows: net start MongoDB
```

### ModuleNotFoundError (Python)
```bash
# Ensure virtual environment is activated
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend cannot reach backend (CORS error)
```bash
# Verify backend is running on port 8000
curl http://localhost:8000/api/health

# Verify NEXT_PUBLIC_API_URL in frontend/.env.local
# Should be: NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Gemini API errors
- Verify `GEMINI_API_KEY` in `backend/.env`
- Check quota: https://aistudio.google.com/app/apikey
- The system falls back to static responses if Gemini fails

### Mock data showing instead of live data
- This is expected when API keys are not configured
- Add API keys to `backend/.env` and restart the backend
- Mock data shows "Sample data" badge on result cards

### RapidFuzz not found
```bash
pip install rapidfuzz --break-system-packages
# or inside venv:
pip install rapidfuzz
```

---

## Architecture Notes

### Why mock data never crashes the app
Every API client uses the `@with_fallback` decorator (`backend/utils/fallback.py`).
It retries 3 times with exponential backoff, then calls the mock provider.
The `is_mock: true` flag propagates to the frontend which shows the amber disclaimer.

### How conversation memory works
`backend/memory/conversation.py` parses every user message with the NLU utilities
and merges new information into `TravelContext` stored in MongoDB.
A new route (e.g., "Mumbai to Goa" after "Delhi to Mumbai") triggers a full reset.
Everything else (class, budget, hotel stars, dates) is additive.

### Dynamic location resolution
`backend/services/geocoding.py` calls Nominatim (free, no key) for every city name.
Results are cached in MongoDB's `cached_results` collection with a 24-hour TTL.
NO coordinates are hardcoded anywhere in the codebase.
# Check the current status
git status

# Stage all changes
git add .

# Commit the changes
git commit -m "Describe your changes"

# Push to the current branch
git push -u origin main