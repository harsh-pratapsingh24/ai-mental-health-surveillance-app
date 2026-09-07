# AegisMind — AI-Powered Mental Health Monitoring & Consoling Companion

A Flask-based multi-agent mental health surveillance system with an empathetic AI companion, crisis intervention, and counselor HITL coordination.

## Features

- **Multi-Agent Pipeline** (per AGENTS.md spec):
  - `guard_agent` — Safety & ingestion guard (consent + crisis regex)
  - `nlp_agent` — Linguistic profiling (pronoun density, absolutist scan)
  - `trajectory_agent` — DPI slope & trajectory velocity over 7-day window
  - `crisis_agent` — SEV-1 crisis intercept & UI lock
  - `hitl_agent` — Counselor HITL queue & Jitsi room management

- **AI Companion Chatbot** with Groq API integration (Llama 3.1)
- **Bilingual Support** — English & Hindi
- **Crisis Intervention** — 4-7-8 breathing pacer, helplines (Tele-MANAS 14416, KIRAN 1800-599-0019, 988)
- **Anonymous Community Forum** with moderation
- **Counselor Dashboard** with Jitsi video consultation links
- **Google OAuth** authentication (kept separate from anonymous wellness data)

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables (copy .env.example to .env and fill in)
cp .env.example .env

# Run development server
python app.py
```

Visit `http://localhost:5000`

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FLASK_SECRET_KEY` | Yes | Random 32+ byte secret for session encryption |
| `GOOGLE_CLIENT_ID` | No | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth client secret |
| `GROQ_API_KEY` | No | Groq API key for Llama 3.1 chatbot (get from https://console.groq.com) |
| `OPENAI_API_KEY` | No | Fallback OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Fallback Anthropic API key |
| `GEMINI_API_KEY` | No | Fallback Google Gemini API key |
| `TELE_MANAS_API_URL` | No | Emergency webhook endpoint |
| `DATABASE_URL` | No | PostgreSQL connection string for production |

## Groq API Setup

1. Get a free API key from [Groq Console](https://console.groq.com)
2. Add to `.env`:
   ```
   GROQ_API_KEY=gsk_your_key_here
   ```
3. The chatbot will automatically use Groq (Llama 3.1 8B) when available, with rule-based fallback

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/register` | POST | Create anonymous session (requires consent) |
| `/api/checkin` | POST | Submit wellness check-in (text + valence + arousal + voice) |
| `/api/chat` | POST | AI Companion chat endpoint |
| `/api/history/<token>` | GET | Retrieve check-in history |
| `/api/forum` | GET/POST | Anonymous community forum |
| `/api/counselor/queue` | GET | HITL review queue |
| `/api/counselor/review/<id>` | POST | Mark case reviewed |
| `/api/counselor/jitsi/<id>` | GET | Get Jitsi consultation link |
| `/api/profile/<token>` | GET | User profile & stats |

## Architecture

```
Check-In → guard_agent → [crisis] → crisis_agent → Emergency Lock
                    ↓ [standard]
               nlp_agent → trajectory_agent → [critical] → crisis_agent
                                                    ↓ [moderate]
                                              hitl_agent → Counselor Queue
```

## Deployment

```bash
# Production with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

For production, set `DATABASE_URL` to PostgreSQL and migrate in-memory stores to persistent models.

## License

Proprietary — AegisMind Clinical AI Systems