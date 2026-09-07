# AegisMind — Cloud-Hosted WebView Deployment Plan

## Overview
Host the Flask app on a live web server (Render recommended) and build a lightweight Android WebView wrapper app that displays the website.

---

## Phase 1: Backend Production Readiness

### 1.1 Database Migration (Critical)
Replace in-memory stores with PostgreSQL using SQLAlchemy:

| Current In-Memory Store | SQLAlchemy Model |
|------------------------|------------------|
| `USER_PROFILES` | `UserProfile(token, alias, consent, google_sub, email, created_at)` |
| `CHECK_IN_HISTORY` | `CheckIn(token, text, valence, arousal, voice_score, nlp_json, dpi, delta_dpi, risk_level, timestamp)` |
| `FORUM_POSTS` | `ForumPost(id, alias, text, lang, reactions, flagged, reports, timestamp)` |
| `COUNSELOR_QUEUE` | `CounselorQueue(id, token, alias, dpi, delta_dpi, risk_level, triggers, jitsi_room, reviewed, sev, flagged_at)` |
| `SEV1_CASES` | `Sev1Case(id, token, alias, text_fragment, dpi, delta_dpi, jitsi_room, flagged_at)` |
| `CHAT_SESSIONS` | `ChatSession(token, sender, message, timestamp)` |

- Add Alembic for migrations
- Add indexes on `token`, `timestamp`, `risk_level`

### 1.2 Production Configuration
- `FLASK_ENV=production`
- `FLASK_SECRET_KEY` from env (32+ chars)
- Google OAuth: Authorized redirect URI = `https://your-domain.com/auth/google/callback`
- CORS headers for WebView origin
- Security headers: CSP, HSTS, X-Frame-Options (allow WebView origin)

### 1.3 Async/Background Tasks
- Move Groq API calls to Celery + Redis (prevents blocking gunicorn workers)
- Add rate limiting (Flask-Limiter) on `/api/checkin`, `/api/chat`, `/api/forum`

### 1.4 Health Checks & Monitoring
- Add `/health` endpoint for load balancer
- Add Sentry/Logtail for error tracking
- Structured JSON logging

---

## Phase 2: Cloud Hosting (Render Recommended)

### 2.1 Render Blueprint (`render.yaml`)
```yaml
services:
  - type: web
    name: aegismind-web
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
    envVars:
      - key: FLASK_SECRET_KEY
        generateValue: true
      - key: GOOGLE_CLIENT_ID
        sync: false
      - key: GOOGLE_CLIENT_SECRET
        sync: false
      - key: GROQ_API_KEY
        sync: false
      - key: DATABASE_URL
        fromDatabase:
          name: aegismind-db
          property: connectionString
    healthCheckPath: /health

databases:
  - name: aegismind-db
    plan: free
```

### 2.2 Deploy Steps
1. Push to GitHub
2. Connect repo to Render
3. Add PostgreSQL database
4. Set env vars in Render dashboard
5. Update Google Cloud Console OAuth redirect URI

### Alternative: AWS (ECS Fargate + RDS + ALB) — more control, higher complexity

---

## Phase 3: Android WebView Wrapper App

### 3.1 Project Structure
```
AegisMindAndroid/
├── app/
│   ├── src/main/
│   │   ├── java/com/aegismind/webview/
│   │   │   ├── MainActivity.kt
│   │   │   ├── WebViewClient.kt
│   │   │   ├── WebChromeClient.kt
│   │   │   └── JSInterface.kt
│   │   ├── res/
│   │   │   ├── layout/activity_main.xml
│   │   │   ├── values/strings.xml
│   │   │   ├── xml/network_security_config.xml
│   │   │   └── mipmap/ic_launcher*.png
│   │   └── AndroidManifest.xml
│   └── build.gradle.kts
├── build.gradle.kts
└── settings.gradle.kts
```

### 3.2 Key WebView Features

| Feature | Implementation |
|---------|----------------|
| **Full-screen WebView** | `WebView` filling `ConstraintLayout`, `webView.settings.javaScriptEnabled = true` |
| **Navigation handling** | `WebViewClient.shouldOverrideUrlLoading` — keep internal links in WebView, open external in browser |
| **JavaScript ↔ Native bridge** | `@JavascriptInterface` class for: token storage, biometric auth, push notifications, file upload (voice), share intent |
| **Offline support** | Service Worker + `WebView.setCacheMode()`; show custom offline page |
| **Pull-to-refresh** | `SwipeRefreshLayout` wrapping WebView |
| **Back button** | `onBackPressed()` → `webView.goBack()` or exit |
| **Deep links** | `intent-filter` for `https://your-domain.com/*` to open in app |
| **Camera/Mic permissions** | Runtime permissions for voice recording; `WebChromeClient.onPermissionRequest` |
| **File upload** | `WebChromeClient.onShowFileChooser` for voice note recording |
| **Fullscreen video** | `WebChromeClient.onShowCustomView` |
| **SSL errors** | `onReceivedSslError` — reject in prod, allow only for debug |

### 3.3 Critical WebView Settings
```kotlin
webView.settings.apply {
    javaScriptEnabled = true
    domStorageEnabled = true
    databaseEnabled = true
    mixedContentMode = WebSettings.MIXED_CONTENT_NEVER_ALLOW // HTTPS only
    setSupportZoom(true)
    builtInZoomControls = true
    displayZoomControls = false
    userAgentString += " AegisMindApp/1.0"
}
```

### 3.4 Native Features to Add
- **Secure token storage**: Android Keystore / EncryptedSharedPreferences for `aegis_token`
- **Biometric auth**: Unlock app with fingerprint/face (before WebView loads)
- **Push notifications**: Firebase Cloud Messaging → JS `navigator.serviceWorker` for crisis alerts
- **Background sync**: WorkManager for offline check-in queue
- **App shortcuts**: "New Check-In", "Talk to Companion", "Crisis Help"

### 3.5 Build & Release
- Sign with upload key (Play App Signing)
- `bundletool` → `.aab` for Play Store
- Test on API 24+ (Android 7.0+)
- Target SDK 34, Min SDK 24

---

## Phase 4: Web App Adjustments for WebView

### 4.1 PWA Manifest (`static/manifest.json`)
```json
{
  "name": "AegisMind",
  "short_name": "AegisMind",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0B0F0D",
  "theme_color": "#0B0F0D",
  "icons": [...]
}
```

### 4.2 Service Worker (`static/sw.js`) — cache shell + API fallback

### 4.3 Meta tags in `index.html` (already present: `apple-mobile-web-app-capable`, `viewport-fit=cover`)

### 4.4 Detect WebView & adapt
```javascript
// In app.js
const isWebView = /Android.*wv/.test(navigator.userAgent);
if (isWebView) {
  document.body.classList.add('webview-mode');
  // Hide bottom dock (native bottom bar handles nav)
  // Expose Android interface: window.AegisAndroid = { saveToken, getToken, ... }
}
```

### 4.5 CSS for WebView — hide browser chrome elements (bottom dock, header login link)

---

## Phase 5: Testing & Launch Checklist

| Item | Status |
|------|--------|
| Flask app on Render with PostgreSQL | ☐ |
| Google OAuth works on production domain | ☐ |
| Groq API calls async (Celery) | ☐ |
| Health endpoint returns 200 | ☐ |
| WebView loads `https://your-domain.com` | ☐ |
| Voice recording works (mic permission) | ☐ |
| Token persists in EncryptedSharedPreferences | ☐ |
| Biometric unlock works | ☐ |
| Push notifications (FCM) → crisis alerts | ☐ |
| Offline check-in queues & syncs | ☐ |
| Deep links open in app | ☐ |
| Play Store listing (privacy policy, screenshots) | ☐ |
| Internal testing track → production | ☐ |

---

## Clarifying Questions

1. **Hosting preference**: Render (simplest), AWS (ECS/Fargate), or another provider?
2. **Database**: PostgreSQL on Render (free tier) OK, or need managed RDS?
3. **Android target**: Minimum API 24 (Android 7.0) acceptable?
4. **Native features priority**: Which are must-haves for MVP? (Biometric auth? Push notifications? Offline sync?)
5. **Timeline**: Target date for Play Store submission?
6. **Team**: Who builds the Android wrapper — you, or need Kotlin code generated?

---

## Estimated Effort

| Phase | Effort |
|-------|--------|
| Backend prod readiness (DB, async, config) | 2-3 days |
| Render deploy + DNS + OAuth | 0.5 day |
| Android WebView wrapper (core) | 2-3 days |
| Native features (biometric, push, offline) | 3-5 days |
| PWA/Service Worker + WebView adaptations | 1 day |
| Testing + Play Store prep | 1-2 days |
| **Total** | **~10-15 days** |

---

## Next Steps
1. Confirm hosting provider and database choice
2. Prioritize native features for MVP
3. Begin Phase 1: Database migration + SQLAlchemy models
4. Scaffold Android WebView project structure
5. Add PWA manifest and service worker to Flask app