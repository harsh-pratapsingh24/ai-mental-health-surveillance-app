# AegisMind — AI-Powered Mental Health Surveillance & Consoling Companion

### Smart India Hackathon (SIH) — Complete Presentation Document

> **One-line Pitch:** An AI-driven, privacy-first mental health early-warning system that detects distress from daily check-ins, intercepts crises in real time, and connects users with human counselors — with an empathetic AI companion available 24/7.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Proposed Solution](#2-proposed-solution)
3. [Application Overview](#3-application-overview)
4. [Current Features](#4-current-features)
5. [Technical Approach & Architecture](#5-technical-approach--architecture)
6. [Multi-Agent Pipeline — Detailed](#6-multi-agent-pipeline--detailed)
7. [End-to-End Flow — How the App Works](#7-end-to-end-flow--how-the-app-works)
8. [Tech Stack](#8-tech-stack)
9. [Security, Privacy & Compliance](#9-security-privacy--compliance)
10. [API Reference](#10-api-reference)
11. [Future Improvements](#11-future-improvements)
12. [References Used](#12-references-used)
13. [Team & Acknowledgements](#13-team--acknowledgements)

---

## 1. Problem Statement

Mental health is one of India's largest — and most under-served — public health challenges.

| Statistic | Source |
|---|---|
| ~15% of Indian adults need active mental health interventions (~150 million people) | NIMHANS / National Mental Health Survey 2015–16 |
| India has only **0.3 psychiatrists per 100,000 people** (WHO) | World Health Organization |
| **70–80%** of people with mental disorders receive **no treatment** at all | WHO World Mental Health Report |
| Student stress, anxiety & depression rising sharply post-COVID | ICSSR / ASSOCHAM studies |
| Suicide is the **leading cause of death** for 15–39 year-olds in India | The Lancet Psychiatry, India |

**Key Gaps:**

- **No continuous monitoring** — traditional help-seeking is episodic (only when a crisis hits).
- **Stigma** — people do not walk into clinics; they need anonymous, always-available support.
- **Late detection** — by the time family/teachers notice, the person is often already in SEV-1 crisis.
- **Counselor shortage** — even those willing to seek help face long queues and zero after-hours support.

**What we need:** A non-invasive, early-warning, always-on system that catches the *slope* of decline before it becomes a crisis — and never leaves the person alone when it does.

---

## 2. Proposed Solution

**AegisMind** is a Progressive Web App (PWA) built on a **multi-agent AI pipeline** that:

1. **Ingests** daily wellness check-ins (mood sliders + reflective journal text + voice note clarity) under informed consent.
2. **Profiles** the user's language linguistically (pronoun density, absolutist thinking patterns).
3. **Tracks trajectory** — computes a rolling *Distress Prediction Index (DPI)* and its velocity (ΔDPI) over a 7-day window to detect *accelerating decline*, not just bad days.
4. **Intercepts crises** in real time — locks the UI into SEV-1 crisis mode, shows national helplines (Tele-MANAS 14416, KIRAN 1800-599-0019, 988), and runs an interactive 4-7-8 breathing pacer.
5. **Escalates to humans (HITL)** — moderate-risk cases enter a Counselor Review Queue with isolated Jitsi video consultation links.
6. **Comforts** — an empathetic AI Companion (Groq LLM with deterministic fallback) plus a full Calming Sanctuary (TIPP skills, Thought Defusion, Butterfly Hug tapping, grounding exercises) available in **English and Hindi**.

**What makes it different:**

- It does not just *score* — it detects **velocity of decline** (ΔDPI), catching rapid multi-day deterioration.
- It has a **safety guardrail first** — crisis keywords bypass the entire scoring pipeline and immediately lock the UI.
- **Anonymity by design** — no personal identity is tied to wellness data; Google OAuth identity is kept strictly separate from anonymous check-in tokens.
- **Human-in-the-loop** — AI never acts alone on clinical decisions; it triages to counselors.

---

## 3. Application Overview

**App Name:** AegisMind
**Type:** Progressive Web App (PWA) — installable, offline-capable shell
**Backend:** Python / Flask multi-agent API
**Languages:** English + Hindi (full bilingual UI)
**Themes:** Dark + Light
**Audience:** Students, young professionals, college counseling centers, NGOs

### Main Screens (Panels)

| # | Panel | Purpose |
|---|---|---|
| 1 | **Home** | Greeting, daily affirmation, "Emotional Horizon" weather barometer, quick stats (check-ins, avg DPI, streak, risk level), 7-day DPI sparkline |
| 2 | **AI Companion** | Chatbot with quick-reply chips; empathetic, non-clinical listening |
| 3 | **Daily Check-In** | Valence & Arousal sliders (1–10), reflective journal (≤800 chars), voice note recorder → submits to the multi-agent pipeline |
| 4 | **Calming Sanctuary** | Sit With Me, TIPP (DBT emergency reset), Thought Defusion, Butterfly Hug bilateral tapping, psychoeducation guides |
| 5 | **Community Forum** | Anonymous bilingual peer-support posts with reactions (❤️ 🤗 ⭐) and report-based moderation |
| 6 | **Counselor Desk** | HITL review queue, mark-reviewed action, Jitsi video links |
| 7 | **Profile** | Anonymous alias, token, check-in count, avg DPI, streak |

### Modals & Overlays

- **Informed Consent** onboarding (required before any check-in)
- **Sign In / Token Restore** (16-char anonymous token or alias)
- **Clinical Glossary** (explains DPI, ΔDPI, pronoun density, absolutist words)
- **Crisis Emergency Modal** (helplines + 4-7-8 breathing pacer)
- **5-4-3-2-1 Sensory Grounding** exercise
- **Crisis Lock Overlay** (full-screen SEV-1 lock)

---

## 4. Current Features

### 4.1 Multi-Agent Distress Prediction Pipeline (per AGENTS.md spec)

| Agent | Function |
|---|---|
| `guard_agent` | Consent verification + regex scan of raw text against acute self-harm expressions (English + Hindi/Hinglish patterns) |
| `nlp_agent` | Tokenizes journal → first-person pronoun density, absolutist-word density, valence/arousal/voice inversion → weighted composite `nlp_score` |
| `trajectory_agent` | Weighted rolling DPI over last 7 check-ins + linear-regression slope → ΔDPI → risk level (low / moderate / critical) |
| `crisis_agent` | SEV-1 case creation, UI lock, helpline display, counselor queue priority insert, optional Tele-MANAS webhook |
| `hitl_agent` | Moderate-risk triage into Counselor Queue with trigger labels (pronoun density, absolutist language, low valence, voice cadence) + Jitsi room `AegisMind-Case-<ID>` |

### 4.2 Check-In & Scoring

- **Emotional Valence slider (1–10)** — pleasantness of emotion (1: Deep Distress → 10: Radiant Joy)
- **Arousal & Energy slider (1–10)** — activation level (1: Lethargic → 10: Restless/Agitated)
- **Reflective Journal** — up to 800 characters, linguistic analysis
- **Voice Note recorder** — acoustic clarity score (0–1) with waveform UI
- **Outputs:** DPI gauge, ΔDPI trajectory, 7-day sparkline, 4-metric linguistic breakdown grid, risk badge, personalized insight card

### 4.3 AI Companion Chatbot

- **Groq LLM integration** (primary) with a carefully engineered clinical system prompt:
  - Validate first; no toxic positivity; no unsolicited fixing; gentle boundaries
  - Explicitly *not* a therapist — defers to professional care
  - 2–3 sentence responses with one grounding invitation
- **Crisis intercept inside chat** — helplines injected immediately on self-harm language (English + Hindi)
- **Proactive helpline injection** for high-distress signals (hopeless / worthless / निराश / बोझ …)
- **Deterministic fallback** — rule-based empathetic response matrix (anxiety / loneliness / sadness / gratitude) so the app works with zero API keys
- **Bilingual** — English and natural Hindi/Hinglish

### 4.4 Crisis Intervention (SEV-1)

- Full-screen **Crisis Lock overlay**
- **National helplines:** Tele-MANAS **14416**, KIRAN **1800-599-0019**, US **988**
- **Interactive 4-7-8 breathing pacer** (animated circle with inhale/hold/exhale counts)
- Automatic **SEV-1 case record** + top-priority counselor queue insert
- Optional **Tele-MANAS webhook** dispatch point

### 4.5 Calming Sanctuary (Clinical Toolkit)

| Module | Clinical Basis |
|---|---|
| **Sit With Me** — silent presence mode with breathing orb | Non-demand companionship |
| **TIPP** — Dive Reflex (cold water, 30s), Intense Exercise burst (60s), Paced Breathing | DBT crisis survival skills |
| **Thought Defusion** — type a painful thought, release it into mist | ACT (Acceptance & Commitment Therapy) |
| **Butterfly Hug / Bilateral Tapping** — guided left-right pacer | Bilateral stimulation (EMDR-adjacent) |
| **5-4-3-2-1 Sensory Grounding** — step-by-step modal | Grounding for panic/dissociation |
| **Psychoeducation Guides** — panic physiology, dissociation anchoring | Psychoeducation |

### 4.6 Anonymous Community Forum

- Bilingual (EN/HI) anonymous posts with generated alias
- Reactions: heart, hug, star
- **Report-based moderation:** 3 reports → flagged; ≥5 reports → hidden
- **Crisis regex pre-filter** — posts containing crisis phrases are rejected with a "use I Need Help Now" prompt
- Rate-limited (8 posts / 60s / IP)

### 4.7 Counselor HITL Dashboard

- Queue view (latest 20) with DPI, ΔDPI, risk level, triggers, SEV level
- **Mark as reviewed** workflow
- **Jitsi video consultation link** per case — `https://meet.jit.si/AegisMind-Case-<ID>` (no signup required)
- API-key protected (`X-Counselor-Key`)

### 4.8 Authentication & Session Model

- **Anonymous primary flow:** 16-char token + auto-generated alias (e.g. `QuietWillow42`) — no PII required
- **Session restore** by token or alias
- **Optional Google OAuth** — identity stored *separately* from wellness records (deliberate privacy boundary)
- **Informed consent gate** — check-ins rejected without consent

### 4.9 PWA & UX

- Installable PWA (manifest + service worker), mobile-first 440px app shell
- Dark/Light theme toggle
- Full **English ↔ Hindi** i18n toggle
- Ambient animated background, staggered entrance animations
- Clinical glossary for every metric
- Skip-to-content, ARIA labels, accessible modals

### 4.10 Security & Ops (built-in)

- Flask-Talisman security headers (CSP, HSTS, X-Frame-Options DENY, Referrer-Policy, Permissions-Policy)
- Strict JSON input validation on every endpoint
- 32 KB max request size
- Per-IP per-route **rate limiting** (check-in 10/min, chat 20/min, forum 8/min)
- **Structured JSON logging** with request IDs — deliberately excludes bodies/PHI
- **Immutable audit log** for every auth, check-in, crisis escalation, forum event (HIPAA/DPDP-ready schema)
- `/health` liveness endpoint reporting component status (storage / async worker / LLM) without exposing secrets
- Graceful degradation: app fully functional with **zero** external API keys

---

## 5. Technical Approach & Architecture

### 5.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    CLIENT (PWA - Vanilla JS)                  │
│  Home │ Companion │ Check-In │ Sanctuary │ Forum │ Counselor  │
└───────────────────────────┬──────────────────────────────────┘
                            │ HTTPS / JSON
┌───────────────────────────▼──────────────────────────────────┐
│                 FLASK API (app.py)                            │
│  ┌─────────────┐ ┌──────────────┐ ┌────────────────────────┐  │
│  │ Rate Limiter │ │ Talisman CSP │ │ Input Validation       │  │
│  └─────────────┘ └──────────────┘ └────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐   │
│  │            MULTI-AGENT PIPELINE                        │   │
│  │  guard → nlp → trajectory → {crisis | hitl}            │   │
│  └────────────────────────────────────────────────────────┘   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │ Companion AI │  │ Audit Logger │  │ In-Memory Stores    │   │
│  │ (Groq LLM +  │  │ (immutable)  │  │ (PG-ready schema)   │   │
│  │  fallback)   │  │              │  │                     │   │
│  └──────────────┘  └──────────────┘  └────────────────────┘   │
└───────┬──────────────────┬──────────────────┬────────────────┘
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │  Groq   │      │ Jitsi Meet  │    │ Google OAuth│
   │  LLM    │      │ (video)     │    │ (optional)  │
   └─────────┘      └─────────────┘    └─────────────┘
                          (Future: PostgreSQL / Redis / Celery / Tele-MANAS)
```

### 5.2 Why This Approach

| Design Decision | Rationale |
|---|---|
| **Multi-agent pipeline** (not a monolith) | Each stage has a single responsibility; crisis path is isolated and cannot be skipped or slowed by scoring |
| **Guard-first routing** | Safety must be evaluated *before* any computation — latency of scoring could cost lives |
| **Rule-based NLP (deterministic)** | Transparent, auditable, explainable to clinicians; no black box for risk decisions; works offline |
| **Weighted composite score** | valence 30%, pronoun density 25%, absolutist density 25%, arousal 10%, voice 10% — clinically motivated weighting |
| **Linear regression slope for ΔDPI** | Detects *velocity* of decline — the key early-warning signal a single-day score misses |
| **7-day rolling window** | Matches natural mood variability while still surfacing sustained declines |
| **LLM only in companion chat** | Generative AI used for *empathy*, never for *risk scoring* — risk decisions stay deterministic & auditable |
| **In-memory + migration-ready schema** | Zero-setup demo mode; `models.py` provides full SQLAlchemy schema (UserProfile, CheckIn, ForumPost, CounselorQueue, Sev1Case, ChatSession, AuditLog) for PostgreSQL |
| **Anonymous tokens separate from OAuth** | Wellness data can never be joined to real identity — privacy by architecture |

### 5.3 Scoring Formulas (explainable AI)

**Per-check-in NLP score:**

```
nlp_score = 0.25·fp_density + 0.25·abs_density + 0.30·valence_distress
          + 0.10·arousal_distress + 0.10·voice_distress
```

where:
- `fp_density` = count(I, me, my, myself, mine) / total_words
- `abs_density` = count(always, never, nothing, hopeless, …) / total_words
- `valence_distress` = (10 − valence) / 9
- `arousal_distress` = |arousal − 5.5| / 4.5
- `voice_distress` = 1 − voice_score

**Rolling DPI (weighted, recent check-ins weighted higher):**

```
DPI = Σ(scoreᵢ · weightᵢ) / Σ(weightᵢ),  weight = [1, 2, …, n]
```

**Trajectory velocity (ordinary least squares slope):**

```
ΔDPI = slope of DPI over last 7 check-ins
```

**Risk classification:**

| Condition | Risk Level |
|---|---|
| `DPI ≥ 0.70` OR `ΔDPI ≥ 0.15` | 🔴 **Critical** → `crisis_agent` (SEV-1) |
| `DPI ≥ 0.40` OR `ΔDPI ≥ 0.05` | 🟠 **Moderate** → `hitl_agent` (counselor queue) |
| otherwise | 🟢 **Low** → standard feedback |

**HITL trigger labels:** pronoun density > 0.15 · absolutist density > 0.08 · valence distress > 0.60 · voice distress > 0.60

---

## 6. Multi-Agent Pipeline — Detailed

*(Spec source: `AGENTS.md` — Multi-Agent Coordination Specification)*

```
                    +-----------------------------+
                    |     Incoming Check-In       |
                    |  (Valence + Text + Voice)   |
                    +--------------+--------------+
                                   |
                                   v
                    +-----------------------------+
                    |  Safety & Ingestion Guard   |
                    +--------------+--------------+
                                   |
            +----------------------+----------------------+
            | (Explicit Danger Pattern)                   | (Standard Processing)
            v                                             v
+------------------------------+              +------------------------------+
|    Crisis Intercept Agent    |              |   Linguistic Profiling Agent |
+--------------+---------------+              +--------------+---------------+
               |                                             |
               v                                             v
+------------------------------+              +------------------------------+
|  Emergency Dispatch & Lock   |              |   Trajectory Velocity Agent  |
+------------------------------+              +--------------+---------------+
                                                             |
                                                             v
                                             +------------------------------+
                                             |   HITL Coordinator Agent     |
                                             +------------------------------+
```

### Agent Specifications

#### 1. Safety & Ingestion Guard (`guard_agent`)
- **Execution:** Flask ingress filter on check-in submissions
- **Responsibility:** Verifies client consent status and scans raw strings against acute self-harm expressions
- **Routing:** If flagged → halts standard NLP scoring → immediately diverts to `crisis_agent`
- **Pattern coverage:** English (`want to die`, `kill myself`, `end it all`, `suicide`, `self-harm`…) **+ Hindi/Hinglish** (`marne ki`, `jeena nahi`, `zindagi khatam`)

#### 2. Linguistic Profiling Agent (`nlp_agent`)
- **Execution:** Synchronous NLP evaluation worker
- **Responsibility:** Tokenizes journal inputs → first-person pronoun density → absolutist distortion counts → parses acoustic metadata from voice notes → weighted composite `nlp_score`
- **Psych basis:** First-person singular pronoun use correlates with depression/self-focus (Rude et al., 2010); absolutist language elevated in depression/anxiety/eating disorders (Al-Mosaiwi & Johnstone, 2018)

#### 3. Trajectory Velocity Agent (`trajectory_agent`)
- **Execution:** Rolling state analysis engine
- **Responsibility:** Compares current scores against the user's historical 7-day baseline → calculates weighted DPI and OLS slope (ΔDPI) → flags rapid multi-day declines → updates risk classification

#### 4. Crisis Intercept Agent (`crisis_agent`)
- **Execution:** Real-time event handler for high-severity inputs
- **Responsibility:** Locks user interface into crisis mode → activates 4-7-8 breathing pacer → displays national helplines (Tele-MANAS, KIRAN, 988) → marks active case as **SEV-1** → optional Tele-MANAS webhook

#### 5. HITL Coordinator Agent (`hitl_agent`)
- **Execution:** Counselor triage controller
- **Responsibility:** Populates flagged moderate/critical profiles into the Counselor Review Queue → generates isolated Jitsi video consultation links (`AegisMind-Case-<ID>`) → moderates flagged submissions in the Anonymous Peer Forum

---

## 7. End-to-End Flow — How the App Works

### 7.1 User Journey Flow

```
LANDING (index.html)
   │
   ├─► Informed Consent Modal ──(must accept)──► POST /api/register
   │                                              → token (16-char) + alias
   │
   ├─► [Optional] Google OAuth (identity kept SEPARATE from wellness data)
   │
   ▼
HOME PANEL
   ├─ Daily affirmation
   ├─ Emotional Horizon (weather-style mood status)
   ├─ Quick stats: Check-Ins | Avg DPI | Streak | Risk Level
   ├─ 7-Day DPI sparkline trajectory
   └─ [Start Daily Check-In] ──────────────┐
                                           ▼
                              CHECK-IN PANEL
                                1. Valence slider (1-10)
                                2. Arousal slider (1-10)
                                3. Reflective Journal (≤800 chars)
                                4. Voice Note (clarity score 0-1)
                                [Submit Check-In]
                                           │
                                           ▼
                                   POST /api/checkin
                                           │
                              ┌────────────▼─────────────┐
                              │   1. guard_agent         │
                              │   consent + crisis regex │
                              └────────────┬─────────────┘
                          crisis?          │        standard?
                 ┌─────────────┐           │   ┌──────────────┐
                 │ crisis_agent│           │   │  nlp_agent   │
                 │ SEV-1 LOCK  │           │   │  pronoun/    │
                 └──────┬──────┘           │   │  absolutist/ │
                        │                  │   │  valence/voice│
                        ▼                  │   └──────┬───────┘
              Crisis Modal:                │          │
              • Helplines 14416/988        │          ▼
              • 4-7-8 breathing pacer      │   trajectory_agent
              • UI locked                  │   DPI + ΔDPI + risk
              • SEV-1 to counselor queue   │          │
                                           │    ┌─────┴──────┐
                                           │    ▼            ▼
                                           │ critical     moderate        low
                                           │    │            │             │
                                           │ crisis_agent  hitl_agent    (feedback only)
                                           │ SEV-1 lock   counselor queue
                                           │              + Jitsi room
                                           ▼
                              RESULT DISPLAYED IN UI
                                • DPI gauge (0.00-1.00)
                                • ΔDPI trajectory + sparkline
                                • Risk badge (Low/Moderate/Critical)
                                • 4-metric linguistic breakdown
                                • Personalized insight card
                                • HITL notice (if queued)
```

### 7.2 Parallel Features Available Anytime

| User Action | Flow |
|---|---|
| **Chat with AI Companion** | Type/chip → `POST /api/chat` → crisis regex check → Groq LLM (clinical prompt) → helpline injection if distressed → deterministic fallback if no API → reply rendered |
| **Visit Calming Sanctuary** | Sit With Me / TIPP timer / Defusion release / Butterfly Hug pacer / Guides — all client-side, instant |
| **Post in Forum** | Compose (EN/HI) → crisis regex pre-filter → alias auto-generated → post appears with reactions/report |
| **Counselor reviews case** | Counselor Desk → queue fetch (API-key) → open Jitsi link → mark reviewed |
| **Restore session** | Sign In modal → token or alias → `POST /api/login` → history + streak restored |

### 7.3 A Concrete Example Scenario

> **Day 1–3:** A student checks in normally — DPI ~0.22, risk *low*.
>
> **Day 4:** Journal shows rising absolutist language ("nothing works", "always fail"), valence drops to 3 → DPI 0.48, ΔDPI +0.06 → risk *moderate* → **hitl_agent** queues the case with triggers `absolutist_language`, `low_valence`; counselor sees it with a Jitsi link.
>
> **Day 5:** Journal contains an acute phrase matched by guard regex → **guard_agent diverts immediately** → **crisis_agent** locks UI → helplines (14416 / KIRAN / 988) + 4-7-8 breathing pacer appear → **SEV-1 case** created at top of counselor queue → audit log records `CRISIS_ESCALATED`.

**The system caught a 4-day decline before it became invisible — and responded within the same request cycle.**

---

## 8. Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.x, Flask 3.0.3 |
| **Frontend** | Vanilla HTML/CSS/JS (mobile-first PWA), no framework overhead |
| **PWA** | Web App Manifest + Service Worker (`sw.js`) |
| **AI — Risk scoring** | Deterministic rule-based NLP (regex + lexicon) — explainable |
| **AI — Companion chat** | Groq API (LLM) with deterministic fallback matrix; OpenAI/Anthropic/Gemini key slots present |
| **Video consultation** | Jitsi Meet (open-source, no-signup room links) |
| **Auth** | Anonymous token system + optional Google OAuth (Authlib, OpenID Connect) |
| **Security** | Flask-Talisman (CSP/HSTS), per-IP rate limiter, strict input validation, JSON structured logs |
| **Persistence (current)** | In-memory stores with migration-ready SQLAlchemy schema (`models.py`) |
| **Persistence (ready)** | PostgreSQL via `DATABASE_URL` (Flask-SQLAlchemy + Alembic) |
| **Async (ready)** | Redis + Celery slots for LLM call offloading |
| **Observability (ready)** | Sentry DSN slot, immutable audit log |
| **Deployment** | Docker + docker-compose, Gunicorn, `/health` endpoint |
| **Testing** | `requirements-dev.txt` dev tooling |

**Dependency footprint (core — deliberately minimal):**
```
flask==3.0.3
authlib==1.3.1
python-dotenv==1.0.1
groq==0.13.0
gunicorn==22.0.0
flask-talisman==1.1.0
```

---

## 9. Security, Privacy & Compliance

| Principle | Implementation |
|---|---|
| **Privacy by architecture** | Anonymous 16-char tokens; Google identity stored separately and never joined to wellness records |
| **Consent-first** | Check-ins rejected (403) without informed consent |
| **Data minimization** | Structured logs exclude request bodies/PHI; journal text never logged |
| **Input safety** | Type/range validation on all endpoints; 32 KB body cap; JSON-only API writes |
| **Abuse prevention** | Per-IP per-route rate limits; bounded in-memory limiter |
| **Browser hardening** | CSP (allowlisted origins incl. Groq + Jitsi), HSTS, X-Frame-Options DENY, nosniff, Referrer-Policy, Permissions-Policy (camera/geo/payment/usb disabled) |
| **Counselor data protection** | `X-Counselor-Key` required on all counselor endpoints |
| **Audit trail** | Immutable `AuditLog`: auth login/logout, session creation, check-ins, crisis escalations, forum posts/reports — with IP + timestamp (HIPAA / India DPDP Act ready schema) |
| **Regulatory alignment** | DPDP Act 2023 consent & data-minimisation principles; WHO/Tele-MANAS escalation pathways |

---

## 10. API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | Main PWA |
| `/login` | GET | Google sign-in page |
| `/auth/google` `/callback` `/logout` | GET | OAuth flow |
| `/health` | GET | Component status (no secrets) |
| `/api/register` | POST | Create anonymous session (consent required) |
| `/api/login` | POST | Restore session by token/alias |
| `/api/checkin` | POST | **Core pipeline** — guard → nlp → trajectory → crisis/hitl |
| `/api/chat` | POST | AI Companion (LLM + fallback) |
| `/api/history/<token>` | GET | Last 30 check-in records |
| `/api/profile/<token>` | GET | Profile, avg DPI, streak |
| `/api/forum` | GET/POST | Anonymous forum |
| `/api/forum/<id>/react` | POST | heart / hug / star |
| `/api/forum/<id>/report` | POST | Report (3 → flagged, 5 → hidden) |
| `/api/counselor/queue` | GET | HITL queue (top 20) |
| `/api/counselor/review/<id>` | POST | Mark case reviewed |
| `/api/counselor/jitsi/<id>` | GET | Jitsi video room URL |

**Example check-in response:**
```json
{
  "status": "ok",
  "token": "9B4F1A28C7E0D356",
  "alias": "QuietWillow42",
  "nlp": {
    "fp_density": 0.14, "abs_density": 0.05,
    "valence_distress": 0.44, "nlp_score": 0.2138
  },
  "trajectory": {
    "dpi": 0.31, "delta_dpi": 0.062,
    "risk_level": "moderate", "sparkline": [0.2, 0.22, 0.25, 0.28, 0.31]
  },
  "agent_action": { "action": "HITL_QUEUED", "jitsi_room": "AegisMind-Case-7F2A91C4" }
}
```

---

## 11. Future Improvements

### 11.1 ML-Based Mental Health Score Predictor (High Priority)

**Goal:** Replace/augment the hand-tuned weighted formula with a trained model that learns individual baselines.

| Aspect | Plan |
|---|---|
| **Model** | Gradient Boosted trees (XGBoost/LightGBM) for interpretable tabular risk prediction; sequence model (LSTM/Transformer) on DPI time-series for trajectory forecasting |
| **Features** | All current NLP metrics (fp_density, abs_density, valence/arousal/voice distress), DPI history, ΔDPI slope, check-in frequency/streak, time-of-day, weekday patterns, voice prosody features (jitter, shimmer, speech rate, pause ratio) |
| **Labels** | Counselor-confirmed risk outcomes from HITL queue; validated PHQ-9 / GAD-7 questionnaire correlation |
| **Explainability** | SHAP values displayed to counselors ("absolutist language contributed +0.18 to risk") — keeps clinical trust |
| **Personalization** | Per-user baseline calibration after ~14 check-ins (user's "normal" ≠ population normal) |
| **Why it matters** | Detects subtle multi-signal patterns humans (and fixed weights) miss; adapts to individual writing style |
| **Ethics guardrail** | ML output *advises* routing — SEV-1 keyword guard and human counselor review remain non-negotiable |

**Pipeline:**
```
Features ──► Feature Store ──► ML Scorer ──► Risk probability + SHAP
                              (on-device / server)
                                   │
                     ┌─────────────┴─────────────┐
                     ▼                           ▼
              confidence ≥ threshold       confidence < threshold
                     │                           │
              rule-based DPI (current)    defer to rules + counselor
```

### 11.2 Hardware-Based Heart Rate & SpO₂ Monitoring (High Priority)

**Goal:** Add physiological vitals as a new signal dimension — body state and mind state measured together.

| Aspect | Plan |
|---|---|
| **Sensors** | MAX30102 (PPG: heart rate + SpO₂ pulse oximeter) with ESP32/Arduino; or commercial BLE bands (Mi Band, Samsung, Apple Watch, Garmin) |
| **Connection** | BLE → PWA Web Bluetooth API (no app install needed) **or** ESP32 → Wi-Fi → MQTT/HTTP → Flask API |
| **Metrics** | Resting HR, HRV (heart rate variability — key stress/autonomic marker), SpO₂ %, breathing rate derived from PPG waveform, sleep duration (if wearable) |
| **Clinical basis** | Low HRV ↔ anxiety/autonomic dysregulation (Thayer et al., 2012); HR spikes precede panic episodes; SpO₂/respiratory changes during acute stress |
| **Pipeline integration** | New `vitals_agent`: normalizes vitals → feeds into nlp_score as additional weighted component + new physiological distress flag |
| **Example rule** | DPI ≥ 0.4 **and** HRV drop > 25% vs 7-day baseline → escalate moderate → critical |
| **Use cases** | Night-time panic detection, pre-crisis autonomic spike alerts, grounding-exercise effectiveness feedback (HR slows during 4-7-8 breathing → visible to user) |

**Proposed hardware architecture:**
```
  ┌─────────────────┐        BLE / USB         ┌──────────────────┐
  │ MAX30102 sensor  │ ──── or ───────────────► │  Smartphone/PWA  │
  │ on finger clip   │    BLE wearable band     │  (Web Bluetooth) │
  └─────────────────┘                          └────────┬─────────┘
                                                        │ HTTPS/JSON
  ┌─────────────────┐        Wi-Fi (MQTT)       ┌───────▼─────────┐
  │ ESP32 + MAX30102 │ ───────────────────────► │  Flask API       │
  │ (standalone)     │                          │  vitals_agent    │
  └─────────────────┘                          └───────┬─────────┘
                                                       │
                                              DPI + HRV + SpO₂
                                              fused risk score
```

### 11.3 Other Planned Improvements

| # | Improvement | Description |
|---|---|---|
| 1 | **Voice emotion analysis (real)** | Replace mock clarity score with SER (speech emotion recognition) — prosody, tremor, pitch variance via openSMILE/librosa or a cloud API |
| 2 | **PostgreSQL + Redis persistence** | Migrate in-memory stores to `models.py` schema; Redis-backed rate limiting for horizontal scale |
| 3 | **Celery async workers** | Offload LLM calls from Flask request workers (broker slots already present) |
| 4 | **Tele-MANAS / 112 real integration** | Activate the existing webhook placeholder; Twilio SMS/call fallback for SEV-1 |
| 5 | **Wearable sleep + activity feeds** | Google Fit / Health Connect APIs — sleep loss & inactivity are strong predictors |
| 6 | **Multilingual expansion** | Beyond EN/HI — regional languages (Tamil, Telugu, Bengali, Marathi) for wider India reach |
| 7 | **Federated / on-device NLP** | Run linguistic scoring on-device so raw journal text never leaves the phone (maximum privacy) |
| 8 | **Native Android/iShell WebView app** | `WEBVIEW_DEPLOYMENT_PLAN.md` already outlines Android WebView packaging for Play Store distribution |
| 9 | **College counseling dashboard** | Aggregate, fully anonymized cohort-level stress trends for institutions (exam season spikes) |
| 10 | **PHQ-9 / GAD-7 validation study** | Correlate DPI with validated clinical questionnaires to establish clinical validity |
| 11 | **Gamified adherence** | Streaks, weekly insight reports, gentle check-in reminders (notifications) |
| 12 | **Parental/guardian mode (minors)** | With strict consent — flag risk to a designated guardian only at SEV-1 |

---

## 12. References Used

### Clinical & Psycholinguistic Foundations

1. **Rude, S., et al. (2010).** "Language use of depressed and depression-vulnerable college students." *Self and Identity* — first-person singular pronouns as a marker of depression and self-focus.
2. **Al-Mosaiwi, M. & Johnstone, T. (2018).** "Absolutist Words: A New Set of Markers of Mental Distress in Natural Language." *PLOS ONE* — absolutist language elevated in depression, anxiety, and eating disorders.
3. **Thayer, J.F., Åhs, F., et al. (2012).** "A meta-analysis of heart rate variability and its implications for translational research." *Biological Psychology* — low HRV as a transdiagnostic marker of emotional dysregulation.
4. **Linehan, M.M. (2015).** *DBT Skills Training Manual* (3rd ed.) — TIPP crisis survival skills (Temperature, Intense exercise, Paced breathing, Paired muscle relaxation).
5. **Hayes, S.C., Strosahl, K.D. & Wilson, K.G. (2012).** *Acceptance and Commitment Therapy* (2nd ed.) — cognitive defusion techniques.
6. **Grounding 5-4-3-2-1 technique** — widely used sensory grounding for panic/anxiety (clinical practice standard).

### Public Health & Policy

7. **National Mental Health Survey of India, 2015–16 (NIMHANS)** — prevalence of mental morbidity in India.
8. **WHO (2022).** *World Mental Health Report: Transforming Mental Health for All.*
9. **Tele-MANAS, Ministry of Health & Family Welfare, Government of India** — national tele-mental health programme; helpline **14416**.
10. **KIRAN Mental Health Helpline, Govt. of India** — 1800-599-0019 (toll-free, 24/7, 13 languages).
11. **988 Suicide & Crisis Lifeline** (USA) — international reference crisis service.
12. **Digital Personal Data Protection Act (DPDP), India, 2023** — consent, data minimisation, purpose limitation.
13. **The Lancet Psychiatry (2020/2023)** — suicide mortality patterns in India by age group.

### Technical References

14. **Flask Documentation** — https://flask.palletsprojects.com/
15. **Groq API / LPU inference** — https://console.groq.com (LLM companion chat)
16. **Jitsi Meet — open-source video conferencing** — https://meet.jit.si (no-signup consultation rooms)
17. **Authlib — OAuth/OpenID Connect for Flask** (Google sign-in)
18. **Flask-Talisman — HTTP security headers** (CSP, HSTS)
19. **MAX30102 Pulse Oximeter & Heart Rate Sensor Datasheet** (Adafruit/Maxim Integrated) — proposed vitals hardware
20. **Web Bluetooth API (W3C)** — browser-native BLE device integration
21. **Progressive Web Apps — Google web.dev guidance** — manifest + service worker offline shell
22. **XGBoost / LightGBM + SHAP** — interpretable ML for tabular risk prediction
23. **openSMILE / librosa** — audio feature extraction for voice prosody analysis
24. **India's National Mental Health Programme (NMHP)** — context for Tele-MANAS scale-up

### Internal Specification Documents

25. **`AGENTS.md`** — Multi-Agent Coordination Specification (guard / nlp / trajectory / crisis / hitl agents)
26. **`ARCHITECTURE_ANALYSIS.md`**, **`WEBVIEW_DEPLOYMENT_PLAN.md`** — internal architecture & deployment planning docs

---

## 13. Team & Acknowledgements

| Field | Detail |
|---|---|
| **Project Name** | AegisMind — AI-Powered Mental Health Surveillance & Consoling Companion |
| **Problem Statement** | *(Fill your SIH problem statement ID & title)* |
| **Team ID / Name** | *(Fill here)* |
| **Team Members** | *(Fill here)* |
| **Mentor** | *(Fill here)* |
| **Category** | Software (Smart India Hackathon) |
| **Domain** | Healthcare / Mental Wellness / AI |

---

## Appendix — Quick Demo Script (for the judges' round)

1. **Open app** → Consent modal → accept → show anonymous token generation.
2. **Home** → show Emotional Horizon, quick stats, glossary (`?` button).
3. **Check-In** → set valence 3, arousal 8, type a stressed journal entry, record voice → submit.
4. **Show results** → DPI gauge, ΔDPI, linguistic breakdown, insight card.
5. **Trigger moderate risk** → counselor queue entry appears with Jitsi link → open Jitsi room live.
6. **Trigger crisis** (type a flagged phrase) → **UI locks**, helplines + 4-7-8 breathing pacer appear → SEV-1 case.
7. **AI Companion** → send "I feel overwhelmed" → empathetic LLM response (+ helpline injection if distressed).
8. **Sanctuary** → run TIPP timer / release a thought into mist / butterfly hug pacer.
9. **Forum** → post anonymously → react → show report moderation.
10. **Toggle Hindi** → entire UI switches to हिन्दी.
11. **Future slide** → ML predictor plan + MAX30102/ESP32 vitals hardware diagram.
