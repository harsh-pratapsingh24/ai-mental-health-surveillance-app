# AegisMind — Architecture Analysis & Improvement Plan

**Date**: 2026-09-08  
**Status**: Analysis Complete — Ready for Implementation Planning

---

## 1. Executive Summary

AegisMind is a well-structured Flask-based mental health monitoring system with a 5-agent pipeline, bilingual companion chatbot, and thoughtful crisis intervention UX. The codebase demonstrates solid clinical AI design principles.

**Top 3 Priorities**:
1. **Database Migration** — Replace in-memory stores with PostgreSQL (blocks production)
2. **Async Processing** — Move Groq LLM calls to Celery/Redis (prevents worker blocking)
3. **Frontend Modularization** — Split 1326-line `app.js` into ES modules

---

## 2. Backend Improvements

| Area | Current State | Recommended Change | Effort | Priority |
|------|---------------|-------------------|--------|----------|
| **Database** | In-memory dicts (`USER_PROFILES`, `CHECK_IN_HISTORY`, `FORUM_POSTS`, `COUNSELOR_QUEUE`, `SEV1_CASES`, `CHAT_SESSIONS`) | PostgreSQL + SQLAlchemy + Alembic migrations | 2-3 days | **Critical** |
| **Async Processing** | Blocking Groq API calls in request thread | Celery + Redis for background LLM calls | 1-2 days | **Critical** |
| **Rate Limiting** | None | Flask-Limiter on `/api/checkin`, `/api/chat`, `/api/forum` | Few hours | High |
| **Security Headers** | None | CSP, HSTS, X-Frame-Options, Referrer-Policy via `flask-talisman` | Few hours | High |
| **Structured Logging** | `print()` statements | JSON logging + Sentry/Logtail integration | Few hours | High |
| **Health Endpoint** | None | `/health` for load balancer probes (DB + Redis checks) | 30 min | High |
| **Input Validation** | Manual checks in routes | Pydantic models for request validation | 1 day | Medium |
| **Testing** | None | Pytest + coverage for agents & routes | 2-3 days | Medium |
| **Configuration** | `os.environ.get()` scattered | Pydantic Settings with `.env` validation | Few hours | Medium |

### Database Schema Mapping (from WEBVIEW_DEPLOYMENT_PLAN.md)

| Current In-Memory Store | SQLAlchemy Model |
|------------------------|------------------|
| `USER_PROFILES` | `UserProfile(token, alias, consent, google_sub, email, created_at)` |
| `CHECK_IN_HISTORY` | `CheckIn(token, text, valence, arousal, voice_score, nlp_json, dpi, delta_dpi, risk_level, timestamp)` |
| `FORUM_POSTS` | `ForumPost(id, alias, text, lang, reactions, flagged, reports, timestamp)` |
| `COUNSELOR_QUEUE` | `CounselorQueue(id, token, alias, dpi, delta_dpi, risk_level, triggers, jitsi_room, reviewed, sev, flagged_at)` |
| `SEV1_CASES` | `Sev1Case(id, token, alias, text_fragment, dpi, delta_dpi, jitsi_room, flagged_at)` |
| `CHAT_SESSIONS` | `ChatSession(token, sender, message, timestamp)` |

**Indexes needed**: `token`, `timestamp`, `risk_level` on all time-series tables.

---

## 3. Frontend Improvements

| Area | Current State | Recommended Change | Effort | Priority |
|------|---------------|-------------------|--------|----------|
| **Code Organization** | Single 1326-line `app.js` | ES modules per feature (chat, checkin, forum, crisis, utils, state, api) | 1-2 days | **Critical** |
| **State Management** | Global `State` object + localStorage | Lightweight store (Zustand) or reactive proxy pattern | 1 day | High |
| **API Layer** | Inline `fetch()` calls everywhere | Centralized API client with interceptors, retries, error handling | Few hours | High |
| **Type Safety** | None | TypeScript migration (gradual, start with API types) | 3-5 days | Medium |
| **Accessibility** | Basic ARIA labels | Full WCAG 2.1 AA audit: focus management, screen readers, contrast ratios | 1-2 days | High |
| **PWA Support** | Meta tags only (`apple-mobile-web-app-capable`) | Service Worker, `manifest.json`, offline fallback page | 1 day | Medium |
| **Testing** | None | Vitest (unit) + Playwright (E2E) | 2 days | Medium |
| **Build System** | Direct static serving | Vite for bundling, HMR, optimized production builds | Few hours | Medium |

### Suggested Module Structure
```
static/js/
├── main.js                 # Entry point, init
├── state/
│   ├── store.js            # Reactive state + persistence
│   └── constants.js        # AFFIRMATIONS, GROUNDING_STEPS
├── api/
│   ├── client.js           # Centralized fetch wrapper
│   └── endpoints.js        # Typed endpoint definitions
├── features/
│   ├── chat/
│   │   ├── chat.js         # Companion chat logic
│   │   └── bubbles.js      # Bubble rendering
│   ├── checkin/
│   │   ├── form.js         # Form handling
│   │   ├── results.js      # Results display
│   │   └── canvas.js       # Gauge & sparkline rendering
│   ├── forum/
│   │   ├── feed.js         # Forum feed rendering
│   │   └── compose.js      # Post composition
│   ├── crisis/
│   │   ├── modal.js        # Crisis modal + breathing pacer
│   │   └── overlay.js      # Crisis lock overlay
│   └── profile/
│       └── profile.js      # Profile & settings
├── ui/
│   ├── modals.js           # Generic modal utilities
│   ├── toasts.js           # Toast notifications
│   └── theme.js            # Theme/language toggles
└── utils/
    ├── dom.js              # $(), $$, escHtml(), formatTime()
    ├── i18n.js             # Bilingual string handling
    └── audio.js            # 432Hz Web Audio synthesizer
```

---

## 4. Clinical / AI Accuracy Improvements

| Component | Current | Suggested Enhancement |
|-----------|---------|----------------------|
| **Crisis Detection** | Regex patterns only | Add transformer-based classifier (DistilBERT fine-tuned on crisis datasets like CLPsych, CrisisLex) |
| **NLP Agent** | Pronoun density + absolutist words | Add: sentiment trajectory (VADER/TextBlob), LIWC-style categories, readability scores (Flesch-Kincaid), emotional arc detection |
| **Trajectory Agent** | Linear regression slope (ΔDPI) | Add: exponential smoothing (Holt-Winters), change-point detection (CUSUM, PELT), seasonal decomposition (STL), anomaly detection (Isolation Forest) |
| **Voice Analysis** | Mock `voice_score` (random) | Integrate `librosa`/`torchaudio` for: pitch (F0), jitter/shimmer, speech rate, pause duration, MFCCs, spectral centroid |
| **Companion LLM** | Groq (qwen/qwen3.8-27b) + rule-based fallback | Add function calling for: grounding exercises, crisis resources, mood logging, check-in scheduling, counselor booking |
| **Risk Thresholds** | Hardcoded (0.70, 0.15, 0.40, 0.05) | Make configurable per user; add clinician calibration UI with ROC curve visualization |

### Crisis Detection Enhancement Detail
```python
# Current: regex-only (lines 135-149 in app.py)
# Proposed: hybrid approach
CRISIS_DETECTION_PIPELINE = [
    ("regex", CRISIS_RE),                    # Fast path - explicit patterns
    ("transformer", DistilBERTClassifier),   # Context-aware - implicit distress
    ("ensemble", LogisticRegression),        # Meta-learner combining signals
]
```

---

## 5. Architecture & Scalability

### Current Architecture (Monolith)
```
┌─────────────────────────────────────────┐
│           Flask App (app.py)            │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│  │Guard │ │ NLP  │ │Trajec│ │Crisis│   │
│  │Agent │ │Agent │ │ Agent│ │Agent │   │
│  └──────┘ └──────┘ └──────┘ └──────┘   │
│         ┌──────────────┐                │
│         │   HITL Agent │                │
│         └──────────────┘                │
│  ┌──────────────────────────────────┐  │
│  │     In-Memory Data Stores        │  │
│  │  (USER_PROFILES, CHECK_INS, ...) │  │
│  └──────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Target Architecture (Modular Monolith → Services)
```
                                    ┌─────────────┐
                                    │  API Gateway │
                                    │  (Kong/      │
                                    │   Traefik)   │
                                    └──────┬──────┘
                                           │
         ┌────────────┬───────────┬────────┼────────┬────────────┐
         ▼            ▼           ▼        ▼        ▼            ▼
    ┌────────┐   ┌────────┐  ┌────────┐ ┌───────┐ ┌───────┐ ┌────────┐
    │ Auth   │   │Checkin │  │ Chat   │ │Forum  │ │Crisis │ │Counselor│
    │ Svc    │   │ Svc    │  │ Svc    │ │ Svc   │ │ Svc   │ │ Svc    │
    └────────┘   └────────┘  └────────┘ └───────┘ └───────┘ └────────┘
         │            │           │        │        │            │
         └────────────┴───────────┴────────┴────────┴────────────┘
                                           │
                                    ┌──────┴──────┐
                                    │ PostgreSQL  │
                                    │ + Redis     │
                                    │ (Celery     │
                                    │  broker)    │
                                    └─────────────┘
```

**Migration Path**:
1. **Phase 1** (Weeks 1-2): Database migration + async tasks within Flask
2. **Phase 2** (Weeks 3-4): Extract agents into internal modules with clean interfaces
3. **Phase 3** (If needed): Deploy as separate services behind gateway

---

## 6. Security & Compliance (Critical for Mental Health)

| Gap | Recommendation | Effort |
|-----|----------------|--------|
| **Data Encryption** | At-rest encryption for all PII (even anonymized tokens); TLS 1.3 enforced; field-level encryption for sensitive columns | Medium |
| **Audit Logging** | Immutable audit trail for: crisis events, counselor queue access, data exports, consent changes | Medium |
| **Data Retention** | Configurable TTL per data type; automatic purge jobs per GDPR/India DPDP Act; user-initiated deletion | Medium |
| **Consent Management** | Granular consent (analytics, crisis sharing, research, marketing); withdrawal flow with data purge | Medium |
| **Penetration Testing** | Annual third-party pentest; OWASP Top 10 coverage; dependency scanning (Dependabot/Snyk) | Ongoing |
| **HIPAA/India DPDP** | BAA with cloud providers; data localization if required; DPIA documentation | High |

### Minimal Security Headers (via `flask-talisman`)
```python
from flask_talisman import Talisman

Talisman(app,
    content_security_policy={
        'default-src': "'self'",
        'script-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        'style-src': ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"],
        'font-src': ["'self'", "https://fonts.gstatic.com"],
        'connect-src': ["'self'", "https://api.groq.com", "wss://*.jit.si"],
        'frame-src': ["https://meet.jit.si"],
        'img-src': ["'self'", "data:"],
    },
    force_https=True,
    strict_transport_security=True,
    session_cookie_secure=True,
    referrer_policy='strict-origin-when-cross-origin'
)
```

---

## 7. Mobile / WebView Specific

The `WEBVIEW_DEPLOYMENT_PLAN.md` is thorough. Key additions for the WebView wrapper:

| Feature | Implementation |
|---------|----------------|
| **Biometric Auth** | Android Keystore / EncryptedSharedPreferences for `aegis_token`; unlock before WebView loads |
| **Push Notifications** | Firebase Cloud Messaging → JS `navigator.serviceWorker` for crisis alerts even when app closed |
| **Offline Queue** | IndexedDB for check-ins + WorkManager background sync when connectivity restored |
| **Native Share Intent** | Crisis resources (helplines) shareable via native Android share sheet |
| **App Shortcuts** | "New Check-In", "Talk to Companion", "Crisis Help" long-press shortcuts |
| **Camera/Mic Permissions** | Runtime permissions for voice recording; `WebChromeClient.onPermissionRequest` |
| **Deep Links** | `intent-filter` for `https://your-domain.com/*` to open in app |

### WebView Detection & Adaptation (add to `app.js`)
```javascript
const isWebView = /Android.*wv/.test(navigator.userAgent);
if (isWebView) {
  document.body.classList.add('webview-mode');
  // Hide bottom dock (native bottom bar handles nav)
  // Expose Android interface: window.AegisAndroid = { saveToken, getToken, biometricAuth, ... }
}
```

### CSS for WebView Mode
```css
/* In mobile.css */
.webview-mode .bottom-dock { display: none; }
.webview-mode .header-login-link { display: none; }
.webview-mode .crisis-fab { bottom: 20px; } /* Adjust for no dock */
```

---

## 8. Implementation Roadmap

### Week 1-2: Foundation (Backend)
- [ ] PostgreSQL + SQLAlchemy models + Alembic migrations
- [ ] Environment-based config (pydantic-settings)
- [ ] Structured logging + Sentry integration
- [ ] Rate limiting + Security headers (`flask-talisman`)
- [ ] `/health` endpoint (DB + Redis connectivity)
- [ ] Pytest suite (agents + routes, target 80% coverage)

### Week 3: Async & Reliability
- [ ] Celery + Redis for Groq API calls
- [ ] Retry policies + dead letter queues
- [ ] Idempotency keys for check-in submission
- [ ] Circuit breaker for external APIs (Groq, Tele-MANAS, Twilio)

### Week 4: Frontend Modernization
- [ ] ES modules + Vite build system
- [ ] Centralized API client with interceptors
- [ ] PWA (manifest.json + Service Worker)
- [ ] Accessibility audit + fixes (WCAG 2.1 AA)
- [ ] TypeScript migration (start with API types)

### Week 5: Clinical Accuracy
- [ ] Crisis classifier (DistilBERT fine-tuned)
- [ ] Voice feature extraction (librosa integration)
- [ ] Configurable risk thresholds + clinician calibration UI
- [ ] LLM function calling for companion (grounding, crisis, booking)

### Week 6: Mobile/WebView
- [ ] Android WebView wrapper (Kotlin, per WEBVIEW_DEPLOYMENT_PLAN.md)
- [ ] Native bridge (token storage, biometric, push, offline queue)
- [ ] Play Store prep (privacy policy, screenshots, listing)

### Ongoing: Security & Compliance
- [ ] Encryption at rest (field-level for sensitive columns)
- [ ] Audit logging framework
- [ ] Data retention policies + purge jobs
- [ ] Schedule pentest

---

## 9. Quick Wins (Do This Week)

| Task | File(s) | Est. Time |
|------|---------|-----------|
| Add Pydantic request validation | `app.py` routes | 2 hrs |
| Add `flask-talisman` security headers | `app.py` | 30 min |
| Add `/health` endpoint | `app.py` | 30 min |
| Extract CSS custom properties to theme files | `static/css/` | 1 hr |
| Split `app.js` into modules | `static/js/` | 4 hrs |
| Complete `.env.example` with all vars | `.env.example` | 15 min |
| Add Dockerfile | root | 30 min |
| Add `requirements-dev.txt` (pytest, black, ruff) | root | 15 min |

---

## 10. Open Questions for Implementation Planning

1. **Timeline**: What's your target for production deployment?
2. **Team**: Solo or team? (Affects modularization priority)
3. **Clinical validation**: Do you have clinician review for risk thresholds?
4. **Data residency**: India-only or global? (Affects cloud provider choice)
5. **Budget**: Render free tier OK, or need AWS/GCP for compliance?
6. **Android priority**: MVP WebView first, or native features (biometric/push) required at launch?
7. **Voice recording**: Browser MediaRecorder API OK, or need native WebView file chooser?
8. **Counselor dashboard**: Separate admin panel or integrated in WebView?

---

## 11. References

- `AGENTS.md` — Multi-agent coordination specification
- `WEBVIEW_DEPLOYMENT_PLAN.md` — Cloud + Android deployment plan
- `app.py` — Main Flask application (798 lines)
- `static/js/app.js` — Frontend logic (1326 lines)
- `static/css/mobile.css` — Design system (1249 lines)
- `requirements.txt` — Python dependencies
- `.env.example` — Environment template