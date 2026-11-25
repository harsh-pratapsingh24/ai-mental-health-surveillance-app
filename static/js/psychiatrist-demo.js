/* ============================================================
   AegisMind — Clinician Console sample data (only loaded with ?demo=1)
   Mirrors the response shapes of the /api/psychiatrist/* endpoints so the
   screens can be reviewed without a backend. Safe to delete once the real
   data flows; psychiatrist.js only loads this file in demo mode.
   ============================================================ */
"use strict";

(() => {
  const MINUTE = 60 * 1000;
  const DAY = 24 * 60 * MINUTE;
  const now = Date.now();
  const isoAgo = (milliseconds) => new Date(now - milliseconds).toISOString();
  const CRISIS_PATTERN = /want to die|kill myself|end it all|can'?t go on|no reason to live|better off dead/i;

  const SAMPLE_TEXT = {
    low: [
      "Slept okay and had a decent day at college.",
      "Felt calm after a walk. Nothing special to report.",
      "A bit tired but I managed my work fine.",
      "Talked to a friend today and it helped.",
    ],
    moderate: [
      "I always feel behind on everything and nothing I do is enough.",
      "I can't sleep. My mind keeps going over what I did wrong. I feel so alone with this.",
      "Everything feels heavy and I never get a break.",
    ],
    critical: [
      "I feel completely hopeless. Nobody would notice if I disappeared.",
      "I'm exhausted, I am worthless and there is no point in trying anymore.",
    ],
  };

  const riskForDpi = (dpi) => (dpi >= 0.7 ? "critical" : dpi >= 0.4 ? "moderate" : "low");

  // Builds a check-in history from a list of DPI values, oldest first, one per day
  function buildCheckins(dpiSeries, seed, crisisAtEnd = false) {
    return dpiSeries.map((dpi, index) => {
      const isCrisisEntry = crisisAtEnd && index === dpiSeries.length - 1;
      const risk = riskForDpi(dpi);
      const pool = SAMPLE_TEXT[risk];
      const previous = index ? dpiSeries[index - 1] : dpi;
      return {
        id: `demo-checkin-${seed}-${index}`,
        text: isCrisisEntry ? "I can't go on anymore. I just want to end it all." : pool[(index + seed) % pool.length],
        valence: Math.max(1, Math.min(10, Math.round(10 - dpi * 9))),
        arousal: 4 + ((index * 7 + seed) % 5),
        voice_score: Math.max(0.1, 1 - dpi * 0.8),
        nlp: isCrisisEntry ? {} : { fp_density: +(dpi * 0.3).toFixed(3), abs_density: +(dpi * 0.14).toFixed(3), voice_distress: +(dpi * 0.8).toFixed(3) },
        dpi,
        delta_dpi: +((dpi - previous) * 0.6).toFixed(3),
        risk_level: risk,
        created_at: isoAgo((dpiSeries.length - 1 - index) * DAY + (seed % 5) * 37 * MINUTE),
      };
    });
  }

  const patients = [
    { ref: "demo-quiet-willow", alias: "QuietWillow42", seed: 1, checkins: buildCheckins([0.31, 0.34, 0.4, 0.47, 0.55, 0.66, 0.78], 1), lastChatAt: isoAgo(4 * MINUTE) },
    { ref: "demo-steady-river", alias: "SteadyRiver18", seed: 2, checkins: buildCheckins([0.28, 0.36, 0.42, 0.5, 0.61, 1.0], 2, true), lastChatAt: isoAgo(2 * DAY) },
    { ref: "demo-gentle-ember", alias: "GentleEmber77", seed: 3, checkins: buildCheckins([0.22, 0.25, 0.33, 0.41, 0.48, 0.55, 0.6], 3), lastChatAt: null },
    { ref: "demo-warm-harbor", alias: "WarmHarbor31", seed: 4, checkins: buildCheckins([0.45, 0.43, 0.5, 0.52, 0.47], 4), lastChatAt: isoAgo(DAY) },
    { ref: "demo-bright-meadow", alias: "BrightMeadow64", seed: 5, checkins: buildCheckins([0.18, 0.2, 0.17, 0.22, 0.19, 0.16, 0.18], 5), lastChatAt: null },
    { ref: "demo-still-lantern", alias: "StillLantern25", seed: 6, checkins: buildCheckins([0.52, 0.46, 0.4, 0.33, 0.27, 0.22], 6), lastChatAt: isoAgo(3 * DAY) },
    { ref: "demo-soft-compass", alias: "SoftCompass53", seed: 7, checkins: buildCheckins([0.2, 0.24, 0.21, 0.26, 0.23], 7), lastChatAt: isoAgo(5 * DAY) },
    { ref: "demo-hopeful-anchor", alias: "HopefulAnchor90", seed: 8, checkins: buildCheckins([0.62, 0.55, 0.47, 0.38, 0.3, 0.28], 8), lastChatAt: null },
  ];

  const chats = {
    "demo-quiet-willow": [
      { sender: "user", message: "hey, i've been feeling really off for days", created_at: isoAgo(26 * MINUTE) },
      { sender: "companion", message: "I hear you, and I'm glad you reached out. That sounds really heavy. Would it help to tell me what the last few days have been like?", created_at: isoAgo(25 * MINUTE) },
      { sender: "user", message: "nothing i do matters anymore. i'm so tired of everything", created_at: isoAgo(12 * MINUTE) },
      { sender: "companion", message: "It makes sense that you're exhausted. You don't have to carry this alone. Would a short breathing exercise help right now?", created_at: isoAgo(11 * MINUTE) },
      { sender: "user", message: "i want to die, i can't do this anymore", created_at: isoAgo(4 * MINUTE) },
      { sender: "companion", message: "I hear how much pain you are carrying right now, and I want you to know you are not alone. Please call or text 14416 (Tele-MANAS) or 988. There are caring professionals available 24/7.", created_at: isoAgo(4 * MINUTE - 5000) },
    ],
    "demo-steady-river": [
      { sender: "user", message: "can you help me calm down", created_at: isoAgo(2 * DAY + 20 * MINUTE) },
      { sender: "companion", message: "Of course. Let's slow down together. Relax your shoulders and take one slow breath in... and out.", created_at: isoAgo(2 * DAY + 19 * MINUTE) },
    ],
    "demo-warm-harbor": [
      { sender: "user", message: "exams are stressing me out so much", created_at: isoAgo(DAY) },
      { sender: "companion", message: "That sounds like a lot of pressure. What part is weighing on you the most?", created_at: isoAgo(DAY - MINUTE) },
    ],
  };

  const cases = [
    {
      id: "A1B2C3D4", ref: "demo-quiet-willow", sev: "SEV-1", risk_level: "critical", source: "chat", status: "new",
      text_fragment: "i want to die, i can't do this anymore", triggers: ["crisis_phrase_detected"],
      dpi: 1.0, delta_dpi: 0.0, flagged_at: isoAgo(4 * MINUTE), notes: "",
    },
    {
      id: "E5F6A7B8", ref: "demo-steady-river", sev: "SEV-1", risk_level: "critical", source: "checkin", status: "acknowledged",
      text_fragment: "I can't go on anymore. I just want to end it all.", triggers: ["crisis_phrase_detected"],
      dpi: 1.0, delta_dpi: 0.234, flagged_at: isoAgo(38 * MINUTE), notes: "Called the emergency contact. Waiting for a callback.",
    },
    {
      id: "C9D0E1F2", ref: "demo-gentle-ember", sev: "SEV-2", risk_level: "moderate", source: "checkin", status: "new",
      text_fragment: "", triggers: ["pronoun_density", "absolutist_language", "low_valence"],
      dpi: 0.6, delta_dpi: 0.18, flagged_at: isoAgo(2 * 60 * MINUTE), notes: "",
    },
    {
      id: "13579BDF", ref: "demo-warm-harbor", sev: "SEV-2", risk_level: "moderate", source: "checkin", status: "in_contact",
      text_fragment: "", triggers: ["low_valence", "voice_cadence"],
      dpi: 0.47, delta_dpi: -0.03, flagged_at: isoAgo(5 * 60 * MINUTE), notes: "Booked a video session for tomorrow 10 AM.",
    },
    {
      id: "2468ACE0", ref: "demo-hopeful-anchor", sev: "SEV-2", risk_level: "moderate", source: "checkin", status: "resolved",
      text_fragment: "", triggers: ["absolutist_language"],
      dpi: 0.55, delta_dpi: 0.04, flagged_at: isoAgo(4 * DAY), notes: "Follow-up done. Sleep routine improved.", resolved: true,
    },
  ];

  const aliasFor = (ref) => (patients.find((patient) => patient.ref === ref) || {}).alias || "Anonymous";
  const clone = (value) => JSON.parse(JSON.stringify(value));

  function caseForClinician(item) {
    return {
      id: item.id,
      patient_ref: item.ref,
      alias: aliasFor(item.ref),
      sev: item.sev,
      risk_level: item.risk_level,
      dpi: item.dpi,
      delta_dpi: item.delta_dpi,
      triggers: item.triggers,
      text_fragment: item.text_fragment,
      source: item.source,
      status: item.status,
      notes: item.notes,
      reviewed: Boolean(item.resolved),
      flagged_at: item.flagged_at,
      jitsi_room: `AegisMind-Case-${item.id}`,
      jitsi_url: `https://meet.jit.si/AegisMind-Case-${item.id}`,
    };
  }

  const riskRank = { critical: 0, moderate: 1, low: 2 };
  const openCasesFor = (ref) => cases.filter((item) => item.ref === ref && !item.resolved);

  function patientSummary(patient) {
    const checkins = patient.checkins;
    const last = checkins[checkins.length - 1];
    const open = openCasesFor(patient.ref);
    const hasOpenSev1 = open.some((item) => item.sev === "SEV-1");
    const dpiValues = checkins.map((checkin) => checkin.dpi);
    return {
      patient_ref: patient.ref,
      alias: patient.alias,
      risk_level: hasOpenSev1 ? "critical" : last.risk_level,
      dpi: last.dpi,
      delta_dpi: last.delta_dpi,
      avg_dpi: +(dpiValues.reduce((sum, value) => sum + value, 0) / dpiValues.length).toFixed(3),
      sparkline: dpiValues.slice(-7),
      checkin_count: checkins.length,
      last_checkin_at: last.created_at,
      last_chat_at: patient.lastChatAt,
      open_cases: open.length,
      open_sev1: hasOpenSev1,
    };
  }

  function counts() {
    const open = cases.filter((item) => !item.resolved);
    return {
      open_sev1: open.filter((item) => item.sev === "SEV-1").length,
      open_sev2: open.filter((item) => item.sev !== "SEV-1").length,
      unacknowledged: open.filter((item) => item.status === "new").length,
      resolved_today: cases.filter((item) => item.resolved && item.resolvedAt && now - item.resolvedAt < DAY).length,
    };
  }

  const api = {
    session: async () => ({ authenticated: true, development_open_access: false }),
    login: async () => ({ status: "ok" }),
    logout: async () => ({ status: "logged_out" }),

    alerts: async () => {
      const open = cases
        .filter((item) => !item.resolved)
        .sort((a, b) =>
          (a.sev === "SEV-1" ? 0 : 1) - (b.sev === "SEV-1" ? 0 : 1)
          || riskRank[a.risk_level] - riskRank[b.risk_level]
          || new Date(b.flagged_at) - new Date(a.flagged_at));
      return clone({ alerts: open.map(caseForClinician), counts: counts(), server_time: new Date().toISOString() });
    },

    patients: async () => {
      const summaries = patients.map(patientSummary)
        .sort((a, b) => (a.open_sev1 ? 0 : 1) - (b.open_sev1 ? 0 : 1) || riskRank[a.risk_level] - riskRank[b.risk_level] || b.dpi - a.dpi);
      return clone({ patients: summaries });
    },

    patient: async (ref) => {
      const patient = patients.find((item) => item.ref === ref);
      if (!patient) throw new Error("Patient not found");
      const chat = (chats[ref] || []).map((turn) => ({ ...turn, crisis: turn.sender === "user" && CRISIS_PATTERN.test(turn.message) }));
      const patientCases = cases
        .filter((item) => item.ref === ref)
        .sort((a, b) => new Date(b.flagged_at) - new Date(a.flagged_at))
        .map(caseForClinician);
      return clone({
        ...patientSummary(patient),
        first_seen: patient.checkins[0].created_at,
        checkins: patient.checkins,
        chat,
        cases: patientCases,
      });
    },

    updateCase: async (caseId, changes) => {
      const item = cases.find((candidate) => candidate.id === caseId);
      if (!item) throw new Error("Case not found");
      if (changes.status) {
        item.status = changes.status;
        if (changes.status === "resolved") {
          item.resolved = true;
          item.resolvedAt = Date.now();
        }
      }
      if (typeof changes.notes === "string") item.notes = changes.notes.trim();
      return clone(caseForClinician(item));
    },
  };

  // Shows the live-alert experience: a new chatbot emergency arrives while the doctor is on the screen
  function scheduleDemoEmergency() {
    setTimeout(() => {
      const patient = patients.find((item) => item.ref === "demo-soft-compass");
      const message = "i don't want to be here anymore, i want to die";
      chats[patient.ref] = [
        ...(chats[patient.ref] || []),
        { sender: "user", message, created_at: new Date().toISOString() },
        { sender: "companion", message: "I'm really glad you told me. You are not alone. Please call or text 14416 (Tele-MANAS) or 988 right now.", created_at: new Date().toISOString() },
      ];
      patient.lastChatAt = new Date().toISOString();
      cases.push({
        id: "FEEDBEEF", ref: patient.ref, sev: "SEV-1", risk_level: "critical", source: "chat", status: "new",
        text_fragment: message, triggers: ["crisis_phrase_detected"],
        dpi: 1.0, delta_dpi: 0.0, flagged_at: new Date().toISOString(), notes: "",
      });
    }, 25000);
  }

  window.AegisPsychiatristDemo = { api, scheduleDemoEmergency };
})();
