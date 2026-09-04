Act as a Principal Full-Stack Engineer and Clinical AI Systems Architect.

Your objective is to generate the complete code for a mobile-first, responsive Flask web application named "AegisMind" — an AI-Powered Mental Health Monitoring & Distress Prediction System.

The application must be strictly framed as a mobile viewport application (max-width: 440px on desktop screens, native viewport on mobile devices) featuring a native bottom dock, smooth CSS transitions, Lucide icons (no emojis), and a seamless Dark Mode / Light Mode toggle persisted in localStorage.

### Core Architectural & Feature Requirements:

1. Explicit Informed Consent:
   - Onboarding modal covering anonymized telemetry, zero-knowledge processing, and crisis escalation authorization.

2. Dual-Modal Check-In:
   - 5-point Valence/Arousal interactive mood slider.
   - Reflective text journaling input.
   - Simulated voice note journal with pulsing audio waveform animation, active recording timer, and simulated pitch-variance/cadence scoring.

3. Psycholinguistic & Trajectory Engine (Deterministic Logic):
   - First-person singular pronoun density calculator ("I", "me", "my", "myself") reflecting inward cognitive withdrawal.
   - Absolutist vocabulary scanner ("always", "never", "completely", "nothing", "everyone", "impossible") reflecting cognitive rigidity.
   - Instant regex crisis intercept ("want to die", "kill myself", "end it all", "better off dead", "can't go on").
   - Multi-day moving average distress slope (DPI: 0.00 to 1.00) measuring trajectory velocity (ΔDPI) across a rolling 7-day sparkline.

4. Actionable Risk Matrix & Triage:
   - Low (Green): Psychoeducational grounding.
   - Moderate (Amber): Guided intervention and peer support prompts.
   - Critical (Red): Immediate UI lock and SEV-1 counselor queue routing.

5. Emergency Crisis Escalation ("I Need Help Now"):
   - Omnipresent floating crisis button.
   - Instant overlay modal featuring one-tap emergency dialers (Tele-MANAS: 14416, KIRAN: 1800-599-0019, 988) and an interactive 4-7-8 physiological breathing pacer.

6. Counselor Human-in-the-Loop (HITL) Desk:
   - Switchable portal view for counselors.
   - Review queue displaying flagged user tokens, trajectory velocity, and linguistic triggers.
   - 1-on-1 consultation launcher opening an instant Jitsi Meet room (meet.jit.si/AegisMind-Case-<ID>).

7. Anonymous Peer Support Forum:
   - Anonymous community feed with alias generation, supportive reactions, and a content moderation flag/report modal.

8. Bilingual Engine:
   - Dynamic English / Hindi (हिन्दी) string toggle across the entire application.

Provide the full, production-ready implementation across: `app.py`, `templates/index.html`, `static/css/mobile.css`, and `static/js/app.js` with zero placeholders or omissions.