/* ============================================================
   AegisMind — Clinician Console
   Emergency alerts, patient list and patient history for psychiatrists.

   Talks only to the Flask /api/psychiatrist/* endpoints, so switching the
   backend from local SQLite to Supabase later needs no change here.
   Open /psychiatrist?demo=1 to explore the screens with sample data.
   ============================================================ */
"use strict";

(() => {
  const API_BASE_URL = window.AEGIS_API_BASE_URL || "";
  const ALERT_POLL_MS = 10000;
  const PATIENT_POLL_MS = 30000;
  const isDemo = new URLSearchParams(window.location.search).has("demo");

  const MAIN_PANELS = ["alerts", "patients", "insights", "account"];
  const RISK_COLORS = { low: "#818CF8", moderate: "#F59E0B", critical: "#F43F5E" };
  const RISK_LABELS = { low: "Low risk", moderate: "Moderate", critical: "Critical" };
  const SOURCE_LABELS = { chat: "Chatbot", checkin: "Check-in", trajectory: "Trend" };
  const STATUS_LABELS = { new: "New", acknowledged: "Acknowledged", in_contact: "In contact", resolved: "Resolved" };
  const TRIGGER_LABELS = {
    crisis_phrase_detected: "Crisis phrase",
    pronoun_density: "High self-focus",
    absolutist_language: "Absolutist language",
    low_valence: "Low mood",
    voice_cadence: "Voice strain",
  };

  // ────────────────────────────────────────────────────────────
  // State
  // ────────────────────────────────────────────────────────────
  const state = {
    authenticated: false,
    accessMode: "signed_in", // signed_in | development | demo
    panel: "alerts",
    dockPanel: "alerts",
    returnPanel: "alerts",
    alerts: [],
    counts: {},
    patients: [],
    patient: null,
    openPatientRef: null,
    alertFilter: "all",
    patientFilter: "all",
    patientSearch: "",
    detailTab: "timeline",
    seenAlertIds: null,
    lastUpdatedAt: null,
    isLive: false,
    started: false,
    soundOn: true,
    notifyOn: false,
    theme: "dark",
    loginMode: "account",
    signInMethods: { account: true, access_code: false, registration: false },
    clinicianEmail: "",
  };

  const $ = (id) => document.getElementById(id);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const store = {
    get: (key, fallback) => localStorage.getItem(`aegis_psy_${key}`) ?? fallback,
    set: (key, value) => localStorage.setItem(`aegis_psy_${key}`, value),
  };

  // ────────────────────────────────────────────────────────────
  // Small helpers
  // ────────────────────────────────────────────────────────────
  function escHtml(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function timeAgo(iso) {
    if (!iso) return "never";
    const seconds = (Date.now() - new Date(iso).getTime()) / 1000;
    if (Number.isNaN(seconds)) return "unknown";
    if (seconds < 45) return "just now";
    if (seconds < 3600) return `${Math.round(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.round(seconds / 3600)}h ago`;
    return `${Math.round(seconds / 86400)}d ago`;
  }

  function formatDateTime(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleString([], { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
  }

  function initials(alias) {
    const capitals = String(alias || "?").match(/[A-Z]/g);
    return (capitals ? capitals.slice(0, 2).join("") : String(alias || "?").slice(0, 2)).toUpperCase();
  }

  const plural = (count, word) => `${count} ${word}${count === 1 ? "" : "s"}`;
  const fixed = (value, digits = 2) => (typeof value === "number" ? value.toFixed(digits) : "—");
  // Mood and energy are whole numbers on the 1-10 slider; show a decimal only when there is one
  const scoreText = (value) => (typeof value !== "number" ? "—" : Number.isInteger(value) ? String(value) : value.toFixed(1));
  const percent = (value) => `${Math.round(value * 100)}%`;

  function toast(text, type = "info", duration = 3500) {
    const container = $("toast-container");
    const element = document.createElement("div");
    element.className = `toast ${type}`;
    element.textContent = text;
    container.appendChild(element);
    setTimeout(() => element.remove(), duration);
  }

  function riskBadge(risk, label) {
    const level = RISK_COLORS[risk] ? risk : "low";
    return `<span class="risk-badge ${level}"><span class="badge-dot"></span>${escHtml(label ?? RISK_LABELS[level])}</span>`;
  }

  function emptyState(title, text) {
    return `<div class="psy-empty"><strong>${escHtml(title)}</strong>${escHtml(text)}</div>`;
  }

  function trendArrow(delta) {
    if (typeof delta !== "number") return "";
    if (delta >= 0.05) return `<span class="psy-trend up" title="Distress rising">▲</span>`;
    if (delta <= -0.05) return `<span class="psy-trend down" title="Distress easing">▼</span>`;
    return `<span class="psy-trend" title="Stable">•</span>`;
  }

  // ────────────────────────────────────────────────────────────
  // API layer (live backend, or sample data with ?demo=1)
  // ────────────────────────────────────────────────────────────
  class AuthRequiredError extends Error {}

  async function liveRequest(path, options = {}) {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 15000);
    try {
      const response = await fetch(`${API_BASE_URL}${path}`, {
        credentials: "same-origin",
        ...options,
        headers: { Accept: "application/json", ...(options.body ? { "Content-Type": "application/json" } : {}) },
        signal: controller.signal,
      });
      const payload = await response.json().catch(() => ({}));
      if (response.status === 401 && path !== "/api/psychiatrist/login") throw new AuthRequiredError();
      if (!response.ok) throw new Error(payload.message || payload.error || "Request failed");
      return payload;
    } catch (error) {
      if (error.name === "AbortError") throw new Error("The request timed out.");
      throw error;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  const liveApi = {
    session: () => liveRequest("/api/psychiatrist/session"),
    // credentials is { email, password } or { access_code }
    login: (credentials) => liveRequest("/api/psychiatrist/login", { method: "POST", body: JSON.stringify(credentials) }),
    // details is { email, password, setup_code }
    register: (details) => liveRequest("/api/psychiatrist/register", { method: "POST", body: JSON.stringify(details) }),
    logout: () => liveRequest("/api/psychiatrist/logout", { method: "POST" }),
    alerts: () => liveRequest("/api/psychiatrist/alerts"),
    patients: () => liveRequest("/api/psychiatrist/patients"),
    patient: (ref) => liveRequest(`/api/psychiatrist/patients/${encodeURIComponent(ref)}`),
    updateCase: (caseId, changes) =>
      liveRequest(`/api/psychiatrist/cases/${encodeURIComponent(caseId)}`, { method: "POST", body: JSON.stringify(changes) }),
  };
  let api = liveApi;

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const element = document.createElement("script");
      element.src = src;
      element.onload = resolve;
      element.onerror = () => reject(new Error(`Could not load ${src}`));
      document.head.appendChild(element);
    });
  }

  function handleError(error, fallbackMessage) {
    if (error instanceof AuthRequiredError) {
      showLogin();
      return;
    }
    toast(error.message || fallbackMessage, "error");
  }

  // ────────────────────────────────────────────────────────────
  // Theme, sound and notification settings
  // ────────────────────────────────────────────────────────────
  function applyTheme(theme) {
    state.theme = theme;
    document.documentElement.setAttribute("data-theme", theme);
    $("toggle-theme").checked = theme === "dark";
    store.set("theme", theme);
  }

  function applySound(isOn) {
    state.soundOn = isOn;
    $("toggle-sound").checked = isOn;
    $("btn-sound").setAttribute("aria-pressed", String(isOn));
    $("icon-sound-on").style.display = isOn ? "" : "none";
    $("icon-sound-off").style.display = isOn ? "none" : "";
    store.set("sound", String(isOn));
  }

  async function applyNotify(isOn) {
    if (isOn) {
      if (!("Notification" in window)) {
        toast("This device does not support system notifications.", "warning");
        isOn = false;
      } else if (Notification.permission !== "granted") {
        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          toast("Notifications are blocked. Allow them in the browser settings.", "warning");
          isOn = false;
        }
      }
    }
    state.notifyOn = isOn;
    $("toggle-notify").checked = isOn;
    store.set("notify", String(isOn));
  }

  // ────────────────────────────────────────────────────────────
  // Emergency notifications: toast, sound, vibration, system notification
  // ────────────────────────────────────────────────────────────
  let audioContext = null;

  function unlockAudio() {
    if (!audioContext) {
      const AudioContextClass = window.AudioContext || window.webkitAudioContext;
      if (AudioContextClass) audioContext = new AudioContextClass();
    }
    if (audioContext && audioContext.state === "suspended") audioContext.resume();
  }

  function playAlertTone(isUrgent) {
    unlockAudio();
    if (!audioContext) return;
    const pitches = isUrgent ? [880, 660, 880] : [660];
    pitches.forEach((frequency, index) => {
      const startAt = audioContext.currentTime + index * 0.22;
      const oscillator = audioContext.createOscillator();
      const gain = audioContext.createGain();
      oscillator.type = "sine";
      oscillator.frequency.value = frequency;
      gain.gain.setValueAtTime(0.0001, startAt);
      gain.gain.exponentialRampToValueAtTime(0.25, startAt + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, startAt + 0.18);
      oscillator.connect(gain).connect(audioContext.destination);
      oscillator.start(startAt);
      oscillator.stop(startAt + 0.2);
    });
  }

  function showSystemNotification(title, body, tag) {
    if (!state.notifyOn || !("Notification" in window) || Notification.permission !== "granted") return;
    try {
      new Notification(title, { body, tag });
    } catch {
      /* some mobile browsers only allow notifications from a service worker */
    }
  }

  function notifyEmergency(alert) {
    const isSev1 = alert.sev === "SEV-1";
    const title = isSev1 ? `SEV-1 emergency · ${alert.alias}` : `New case · ${alert.alias}`;
    const detail = alert.text_fragment || (alert.triggers || []).map((t) => TRIGGER_LABELS[t] || t).join(", ");
    toast(title, isSev1 ? "error" : "warning", 6000);
    if (state.soundOn) playAlertTone(isSev1);
    if (isSev1 && navigator.vibrate) navigator.vibrate([250, 120, 250]);
    showSystemNotification(title, `${SOURCE_LABELS[alert.source] || "Check-in"}: ${detail}`, alert.id);
  }

  function announceNewEmergencies(alerts) {
    const currentIds = new Set(alerts.map((alert) => alert.id));
    // First load: remember what is already open so the doctor is not pinged for old cases
    if (state.seenAlertIds === null) {
      state.seenAlertIds = currentIds;
      return;
    }
    const freshAlerts = alerts.filter((alert) => !state.seenAlertIds.has(alert.id));
    state.seenAlertIds = currentIds;
    freshAlerts.forEach(notifyEmergency);
  }

  // ────────────────────────────────────────────────────────────
  // Charts (canvas)
  // ────────────────────────────────────────────────────────────
  function prepareCanvas(canvas, fallbackWidth, fallbackHeight) {
    const ratio = window.devicePixelRatio || 1;
    const width = canvas.clientWidth || fallbackWidth;
    const height = canvas.clientHeight || fallbackHeight;
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    const context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);
    return { context, width, height };
  }

  // DPI is always 0 to 1, so every sparkline uses the same scale and patients compare fairly
  function drawSparkline(canvas, values, risk) {
    if (!canvas) return;
    const { context, width, height } = prepareCanvas(canvas, 72, 28);
    const padding = 3;
    const points = values.map((value, index) => ({
      x: padding + (values.length === 1 ? 0.5 : index / (values.length - 1)) * (width - padding * 2),
      y: height - padding - Math.max(0, Math.min(1, value)) * (height - padding * 2),
    }));
    if (!points.length) return;
    context.strokeStyle = RISK_COLORS[risk] || RISK_COLORS.low;
    context.fillStyle = context.strokeStyle;
    context.lineWidth = 2;
    context.lineJoin = "round";
    context.beginPath();
    points.forEach((point, index) => (index === 0 ? context.moveTo(point.x, point.y) : context.lineTo(point.x, point.y)));
    context.stroke();
    const last = points[points.length - 1];
    context.beginPath();
    context.arc(last.x, last.y, 2.6, 0, Math.PI * 2);
    context.fill();
  }

  function drawGauge(canvas, dpi, risk) {
    if (!canvas) return;
    const { context, width, height } = prepareCanvas(canvas, 72, 72);
    const centerX = width / 2;
    const centerY = height / 2;
    const radius = 28;
    const startAngle = Math.PI * 0.75;
    const endAngle = Math.PI * 2.25;
    context.lineWidth = 6;
    context.lineCap = "round";
    context.beginPath();
    context.arc(centerX, centerY, radius, startAngle, endAngle);
    context.strokeStyle = "rgba(255,255,255,0.1)";
    context.stroke();
    if (typeof dpi === "number" && dpi > 0) {
      context.beginPath();
      context.arc(centerX, centerY, radius, startAngle, startAngle + (endAngle - startAngle) * Math.min(dpi, 1));
      context.strokeStyle = RISK_COLORS[risk] || RISK_COLORS.low;
      context.stroke();
    }
  }

  function drawTrendChart(canvas, checkins) {
    if (!canvas) return;
    const { context, width, height } = prepareCanvas(canvas, 380, 150);
    const mutedColor = getComputedStyle(document.documentElement).getPropertyValue("--text-muted").trim() || "#6D6782";
    const padding = { top: 10, right: 10, bottom: 20, left: 10 };
    const plotWidth = width - padding.left - padding.right;
    const plotHeight = height - padding.top - padding.bottom;
    const yFor = (dpi) => padding.top + (1 - Math.max(0, Math.min(1, dpi))) * plotHeight;

    // Step 1: dashed lines where moderate (0.40) and critical (0.70) risk begin
    [[0.4, RISK_COLORS.moderate], [0.7, RISK_COLORS.critical]].forEach(([level, color]) => {
      context.setLineDash([4, 4]);
      context.strokeStyle = color;
      context.globalAlpha = 0.45;
      context.lineWidth = 1;
      context.beginPath();
      context.moveTo(padding.left, yFor(level));
      context.lineTo(width - padding.right, yFor(level));
      context.stroke();
    });
    context.setLineDash([]);
    context.globalAlpha = 1;

    // Step 2: the DPI line across check-ins
    const points = checkins
      .filter((checkin) => typeof checkin.dpi === "number")
      .map((checkin, index, all) => ({
        x: padding.left + (all.length === 1 ? 0.5 : index / (all.length - 1)) * plotWidth,
        y: yFor(checkin.dpi),
        risk: checkin.risk_level,
      }));
    if (!points.length) return;
    const gradient = context.createLinearGradient(0, 0, width, 0);
    gradient.addColorStop(0, "#8B5CF6");
    gradient.addColorStop(1, "#C084FC");
    context.strokeStyle = gradient;
    context.lineWidth = 2.2;
    context.lineJoin = "round";
    context.beginPath();
    points.forEach((point, index) => (index === 0 ? context.moveTo(point.x, point.y) : context.lineTo(point.x, point.y)));
    context.stroke();

    // Step 3: a dot per check-in, coloured by risk, with a bigger dot on the latest
    points.forEach((point, index) => {
      context.fillStyle = RISK_COLORS[point.risk] || RISK_COLORS.low;
      context.beginPath();
      context.arc(point.x, point.y, index === points.length - 1 ? 4.5 : 2.8, 0, Math.PI * 2);
      context.fill();
    });

    // Step 4: first and last dates under the chart
    context.fillStyle = mutedColor;
    context.font = "600 10px Manrope, sans-serif";
    context.textAlign = "left";
    context.fillText(formatDateTime(checkins[0].created_at).split(",")[0], padding.left, height - 5);
    context.textAlign = "right";
    context.fillText(formatDateTime(checkins[checkins.length - 1].created_at).split(",")[0], width - padding.right, height - 5);
  }

  function drawSparklinesIn(root) {
    $$("canvas[data-spark]", root).forEach((canvas) => {
      const values = canvas.dataset.spark.split(",").filter(Boolean).map(Number);
      drawSparkline(canvas, values, canvas.dataset.risk);
    });
  }

  // ────────────────────────────────────────────────────────────
  // Cards
  // ────────────────────────────────────────────────────────────
  function caseActionButtons(item, isDetailView) {
    const buttons = [];
    if (!isDetailView) {
      buttons.push(`<button class="btn btn-secondary btn-sm" type="button" data-action="open-patient" data-ref="${escHtml(item.patient_ref)}">Open patient</button>`);
    }
    if (item.status !== "resolved") {
      buttons.push(`<button class="btn btn-outline btn-sm" type="button" data-action="video" data-url="${escHtml(item.jitsi_url)}">Join video</button>`);
    }
    if (item.status === "new") {
      const buttonClass = item.sev === "SEV-1" ? "btn-primary" : "btn-outline";
      buttons.push(`<button class="btn ${buttonClass} btn-sm" type="button" data-action="set-status" data-case="${escHtml(item.id)}" data-status="acknowledged">Acknowledge</button>`);
    } else if (item.status === "acknowledged") {
      buttons.push(`<button class="btn btn-outline btn-sm" type="button" data-action="set-status" data-case="${escHtml(item.id)}" data-status="in_contact">Mark in contact</button>`);
    }
    if (item.status !== "resolved") {
      buttons.push(`<button class="btn btn-secondary btn-sm" type="button" data-action="resolve" data-case="${escHtml(item.id)}" data-alias="${escHtml(item.alias)}">Resolve</button>`);
    }
    return buttons.join("");
  }

  function caseCardHtml(item, isDetailView = false) {
    const isSev1 = item.sev === "SEV-1";
    const triggerTags = (item.triggers || [])
      .map((trigger) => `<span class="psy-tag">${escHtml(TRIGGER_LABELS[trigger] || trigger)}</span>`)
      .join("");
    const quote = item.text_fragment ? `<blockquote class="psy-quote">“${escHtml(item.text_fragment)}”</blockquote>` : "";
    const notes = isDetailView
      ? `<div class="psy-case-notes">
           <textarea id="note-${escHtml(item.id)}" class="journal-textarea" maxlength="2000" placeholder="Private clinician note…">${escHtml(item.notes)}</textarea>
           <button class="btn btn-secondary btn-sm mt-2" type="button" data-action="save-note" data-case="${escHtml(item.id)}">Save note</button>
         </div>`
      : "";
    const header = isDetailView
      ? `<div class="psy-alert-who"><strong>${escHtml(item.id)}</strong><span class="post-time">${escHtml(formatDateTime(item.flagged_at))} · ${escHtml(timeAgo(item.flagged_at))}</span></div>`
      : `<div class="post-avatar">${escHtml(initials(item.alias))}</div>
         <div class="psy-alert-who"><strong>${escHtml(item.alias)}</strong><span class="post-time">${escHtml(timeAgo(item.flagged_at))} · via ${escHtml(SOURCE_LABELS[item.source] || "Check-in")}</span></div>`;

    return `
      <article class="queue-card psy-alert ${isSev1 ? "sev1" : "sev2"}">
        <div class="psy-alert-head">
          ${header}
          ${riskBadge(isSev1 ? "critical" : item.risk_level, item.sev)}
        </div>
        ${quote}
        <div class="psy-tags">
          <span class="psy-tag source-${escHtml(item.source)}">${escHtml(SOURCE_LABELS[item.source] || "Check-in")}</span>
          <span class="psy-tag status-${escHtml(item.status)}">${escHtml(STATUS_LABELS[item.status] || item.status)}</span>
          ${triggerTags}
        </div>
        <div class="queue-stats">
          <div class="queue-stat"><div class="queue-stat-value">${fixed(item.dpi)}</div><div class="queue-stat-label">DPI</div></div>
          <div class="queue-stat"><div class="queue-stat-value">${fixed(item.delta_dpi, 3)}</div><div class="queue-stat-label">ΔDPI</div></div>
          <div class="queue-stat"><div class="queue-stat-value">${escHtml(item.sev)}</div><div class="queue-stat-label">Level</div></div>
        </div>
        ${notes}
        <div class="psy-actions">${caseActionButtons(item, isDetailView)}</div>
      </article>`;
  }

  function patientRowHtml(patient) {
    const lastSeen = patient.last_checkin_at ? `Check-in ${timeAgo(patient.last_checkin_at)}` : "No check-ins yet";
    const openPill = patient.open_cases ? `<span class="psy-open-pill">${patient.open_cases} open</span>` : "";
    return `
      <article class="queue-card psy-patient" role="button" tabindex="0" data-action="open-patient" data-ref="${escHtml(patient.patient_ref)}">
        <div class="post-avatar">${escHtml(initials(patient.alias))}</div>
        <div class="psy-patient-main">
          <div class="psy-patient-top"><strong>${escHtml(patient.alias)}</strong>${riskBadge(patient.risk_level)}</div>
          <div class="psy-patient-meta"><span>${escHtml(lastSeen)}</span><span>${plural(patient.checkin_count, "check-in")}</span>${openPill}</div>
        </div>
        <div class="psy-patient-side">
          <canvas data-spark="${escHtml((patient.sparkline || []).join(","))}" data-risk="${escHtml(patient.risk_level)}" width="72" height="28"></canvas>
          <span class="psy-patient-dpi">DPI ${fixed(patient.dpi)} ${trendArrow(patient.delta_dpi)}</span>
        </div>
      </article>`;
  }

  // ────────────────────────────────────────────────────────────
  // Panel: Alerts
  // ────────────────────────────────────────────────────────────
  function filteredAlerts() {
    return state.alerts.filter((alert) => {
      switch (state.alertFilter) {
        case "sev1": return alert.sev === "SEV-1";
        case "sev2": return alert.sev !== "SEV-1";
        case "chat": return alert.source === "chat";
        case "checkin": return alert.source !== "chat";
        case "new": return alert.status === "new";
        default: return true;
      }
    });
  }

  function renderAlerts() {
    const { open_sev1: openSev1 = 0, open_sev2: openSev2 = 0, unacknowledged = 0 } = state.counts;
    const hero = $("alerts-hero");
    hero.classList.toggle("is-critical", openSev1 > 0);
    hero.innerHTML = openSev1 > 0
      ? `<div class="psy-hero-number">${openSev1}</div>
         <div>
           <div class="psy-hero-title">${openSev1 === 1 ? "Emergency needs" : "Emergencies need"} you now</div>
           <div class="psy-hero-sub">${unacknowledged} unacknowledged · ${plural(openSev2, "moderate case")} open</div>
         </div>`
      : `<div class="psy-hero-number">0</div>
         <div>
           <div class="psy-hero-title">No open emergencies</div>
           <div class="psy-hero-sub">${plural(openSev2, "moderate case")} open. You will be alerted the moment a patient needs you.</div>
         </div>`;

    const alerts = filteredAlerts();
    $("alerts-list").innerHTML = alerts.length
      ? alerts.map((alert) => caseCardHtml(alert)).join("")
      : emptyState(
          state.alerts.length ? "Nothing matches this filter" : "All clear",
          state.alerts.length ? "Try another filter to see the other open cases." : "New emergencies from check-ins and the chatbot appear here instantly.",
        );
  }

  function renderAlertBadge() {
    const { open_sev1: openSev1 = 0 } = state.counts;
    const badge = $("dock-alert-badge");
    badge.hidden = state.alerts.length === 0;
    badge.textContent = state.alerts.length > 99 ? "99+" : String(state.alerts.length);
    document.title = openSev1 > 0 ? `(${openSev1}) Emergency — AegisMind Clinician` : "AegisMind Clinician";
  }

  async function refreshAlerts() {
    if (!state.authenticated) return;
    try {
      const data = await api.alerts();
      state.alerts = data.alerts || [];
      state.counts = data.counts || {};
      announceNewEmergencies(state.alerts);
      state.lastUpdatedAt = Date.now();
      state.isLive = true;
      renderLivePill();
      renderAlertBadge();
      if (state.panel === "alerts") renderAlerts();
      if (state.panel === "insights") renderInsights();
    } catch (error) {
      if (error instanceof AuthRequiredError) return showLogin();
      state.isLive = false;
      renderLivePill();
    }
  }

  // ────────────────────────────────────────────────────────────
  // Panel: Patients
  // ────────────────────────────────────────────────────────────
  function filteredPatients() {
    const search = state.patientSearch.trim().toLowerCase();
    return state.patients.filter((patient) => {
      if (search && !patient.alias.toLowerCase().includes(search)) return false;
      if (state.patientFilter === "open") return patient.open_cases > 0;
      if (state.patientFilter === "all") return true;
      return patient.risk_level === state.patientFilter;
    });
  }

  function renderPatients() {
    const patients = filteredPatients();
    $("patients-total").textContent = String(state.patients.length);
    $("patients-list").innerHTML = patients.length
      ? patients.map(patientRowHtml).join("")
      : emptyState(
          state.patients.length ? "No patients match" : "No patients yet",
          state.patients.length ? "Try a different search or filter." : "Patients appear here after their first check-in or chat.",
        );
    drawSparklinesIn($("patients-list"));
  }

  async function refreshPatients() {
    if (!state.authenticated) return;
    try {
      const data = await api.patients();
      state.patients = data.patients || [];
      if (state.panel === "patients") renderPatients();
      if (state.panel === "insights") renderInsights();
    } catch (error) {
      if (error instanceof AuthRequiredError) showLogin();
    }
  }

  // ────────────────────────────────────────────────────────────
  // Panel: Insights
  // ────────────────────────────────────────────────────────────
  function renderInsights() {
    const counts = state.counts;
    const tiles = [
      { label: "Open SEV-1", value: counts.open_sev1 ?? 0, tone: "psy-tile-critical" },
      { label: "Open SEV-2", value: counts.open_sev2 ?? 0, tone: "psy-tile-moderate" },
      { label: "Patients monitored", value: state.patients.length, tone: "" },
      { label: "Resolved today", value: counts.resolved_today ?? 0, tone: "" },
    ];
    $("insight-tiles").innerHTML = tiles
      .map((tile) => `<div class="stat-tile ${tile.tone}"><div class="stat-tile-top"><span class="stat-tile-label">${tile.label}</span></div><div class="stat-tile-value">${tile.value}</div></div>`)
      .join("");

    const byRisk = { low: 0, moderate: 0, critical: 0 };
    state.patients.forEach((patient) => { byRisk[patient.risk_level] = (byRisk[patient.risk_level] || 0) + 1; });
    const total = state.patients.length || 1;
    $("risk-dist-bar").innerHTML = ["critical", "moderate", "low"]
      .map((risk) => `<span class="${risk}" style="width:${(byRisk[risk] / total) * 100}%"></span>`)
      .join("");
    $("risk-dist-legend").innerHTML = ["critical", "moderate", "low"]
      .map((risk) => `<span><i style="background:${RISK_COLORS[risk]}"></i>${RISK_LABELS[risk]} ${byRisk[risk]}</span>`)
      .join("");

    const needAttention = state.patients.filter((patient) => patient.risk_level !== "low").slice(0, 3);
    $("attention-list").innerHTML = needAttention.length
      ? needAttention.map(patientRowHtml).join("")
      : emptyState("Everyone is stable", "No patient is currently at moderate or critical risk.");
    drawSparklinesIn($("attention-list"));
  }

  // ────────────────────────────────────────────────────────────
  // Panel: Account
  // ────────────────────────────────────────────────────────────
  function renderAccount() {
    const modeText = {
      demo: "Demo data · not connected to patients",
      development: "Local development access · no access code set",
      signed_in: state.clinicianEmail ? `Signed in as ${state.clinicianEmail}` : "Signed in with clinician access code",
    };
    $("account-mode").textContent = modeText[state.accessMode];
    $("row-signout").style.display = state.accessMode === "signed_in" ? "" : "none";
  }

  // ────────────────────────────────────────────────────────────
  // Panel: Patient detail
  // ────────────────────────────────────────────────────────────
  async function openPatient(ref) {
    state.returnPanel = state.panel === "patient" ? state.returnPanel : state.panel;
    state.openPatientRef = ref;
    state.patient = null;
    state.detailTab = "timeline";
    $("back-label").textContent = `Back to ${state.returnPanel}`;
    $("patient-hero").innerHTML = emptyState("Loading patient…", "");
    $("patient-tab-body").innerHTML = "";
    // Android back button / swipe-back returns to the list instead of leaving the app
    history.pushState({ patient: ref }, "");
    navigateTo("patient");
    await loadPatientDetail(ref);
  }

  async function loadPatientDetail(ref) {
    try {
      const patient = await api.patient(ref);
      if (state.openPatientRef !== ref) return;
      state.patient = patient;
      renderPatient();
    } catch (error) {
      if (error instanceof AuthRequiredError) return showLogin();
      toast(error.message || "Could not load that patient.", "error");
      navigateTo(state.returnPanel);
    }
  }

  function renderPatientHero(patient) {
    return `
      <div class="card">
        <div class="pd-hero-top">
          <div class="profile-avatar-ring">${escHtml(initials(patient.alias))}</div>
          <div class="pd-hero-name"><strong>${escHtml(patient.alias)}</strong><span>ref ${escHtml(patient.patient_ref.slice(0, 8))}</span></div>
          ${riskBadge(patient.risk_level)}
        </div>
        <div class="dpi-display">
          <div class="dpi-gauge">
            <canvas id="pd-gauge" width="72" height="72"></canvas>
            <div class="dpi-value"><span class="dpi-number">${fixed(patient.dpi)}</span><span class="dpi-label">DPI</span></div>
          </div>
          <div class="dpi-meta">
            <div class="dpi-meta-title"><span>Trajectory (ΔDPI)</span></div>
            <div class="dpi-meta-delta">${typeof patient.delta_dpi === "number" ? (patient.delta_dpi >= 0 ? "+" : "") + patient.delta_dpi.toFixed(3) : "—"} ${trendArrow(patient.delta_dpi)}</div>
            <canvas id="pd-spark" data-spark="${escHtml((patient.sparkline || []).join(","))}" data-risk="${escHtml(patient.risk_level)}" height="32"></canvas>
          </div>
        </div>
        <div class="pd-stats">
          <div class="queue-stat"><div class="queue-stat-value">${patient.checkin_count}</div><div class="queue-stat-label">Check-ins</div></div>
          <div class="queue-stat"><div class="queue-stat-value">${fixed(patient.avg_dpi)}</div><div class="queue-stat-label">Avg DPI</div></div>
          <div class="queue-stat"><div class="queue-stat-value">${patient.open_cases}</div><div class="queue-stat-label">Open cases</div></div>
        </div>
      </div>`;
  }

  function checkinTags(checkin) {
    const nlp = checkin.nlp || {};
    const tags = [
      { label: `Mood ${scoreText(checkin.valence)}/10`, hot: checkin.valence <= 3 },
      { label: `Energy ${scoreText(checkin.arousal)}/10`, hot: checkin.arousal >= 9 || checkin.arousal <= 2 },
    ];
    // Same thresholds the hitl_agent uses to raise a case, so highlights match what flagged the patient
    if (typeof nlp.fp_density === "number") tags.push({ label: `Self-focus ${percent(nlp.fp_density)}`, hot: nlp.fp_density > 0.15 });
    if (typeof nlp.abs_density === "number") tags.push({ label: `Absolutist ${percent(nlp.abs_density)}`, hot: nlp.abs_density > 0.08 });
    if (typeof nlp.voice_distress === "number") tags.push({ label: `Voice strain ${percent(nlp.voice_distress)}`, hot: nlp.voice_distress > 0.6 });
    if (!Object.keys(nlp).length && checkin.risk_level === "critical") tags.unshift({ label: "Crisis phrase detected", hot: true });
    return tags.map((tag) => `<span class="psy-tag ${tag.hot ? "status-new" : ""}">${escHtml(tag.label)}</span>`).join("");
  }

  function renderTimelineTab(patient) {
    if (!patient.checkins.length) return emptyState("No check-ins yet", "Check-ins will appear here with their linguistic markers.");
    const chart = `
      <div class="card">
        <div class="card-title"><span>DPI over time</span><span class="post-time">last ${plural(patient.checkins.length, "check-in")}</span></div>
        <canvas id="pd-trend" class="pd-trend-canvas"></canvas>
        <div class="pd-chart-legend">
          <span><i style="background:${RISK_COLORS.moderate}"></i>0.40 moderate</span>
          <span><i style="background:${RISK_COLORS.critical}"></i>0.70 critical</span>
        </div>
      </div>`;
    const entries = [...patient.checkins].reverse().map((checkin) => `
      <article class="queue-card pd-checkin">
        <div class="pd-checkin-head">
          ${riskBadge(checkin.risk_level)}
          <span class="post-time">${escHtml(formatDateTime(checkin.created_at))}</span>
          <span class="pd-checkin-dpi">DPI ${fixed(checkin.dpi)}</span>
        </div>
        <p class="pd-checkin-text">${escHtml(checkin.text)}</p>
        <div class="psy-tags">${checkinTags(checkin)}</div>
      </article>`).join("");
    return `${chart}<div class="section-heading">Check-ins · newest first</div>${entries}`;
  }

  function renderChatTab(patient) {
    if (!patient.chat.length) return emptyState("No chat messages", "This patient has not talked to the companion yet.");
    const bubbles = patient.chat.map((turn) => {
      const isPatient = turn.sender === "user";
      const flag = turn.crisis ? `<div class="psy-crisis-flag">Crisis phrase</div>` : "";
      return `
        <div class="chat-bubble-wrap ${isPatient ? "user" : "companion"} ${turn.crisis ? "is-crisis" : ""}">
          <div class="chat-avatar">${isPatient ? escHtml(initials(patient.alias)) : "AI"}</div>
          <div>
            <div class="chat-bubble">${escHtml(turn.message)}</div>
            <div class="psy-chat-time">${escHtml(formatDateTime(turn.created_at))}</div>
            ${flag}
          </div>
        </div>`;
    }).join("");
    return `<div class="psy-chat">${bubbles}</div>`;
  }

  function renderCasesTab(patient) {
    if (!patient.cases.length) return emptyState("No cases", "No case has been raised for this patient.");
    return patient.cases.map((item) => caseCardHtml(item, true)).join("");
  }

  function renderPatientTab() {
    const patient = state.patient;
    if (!patient) return;
    const renderers = { timeline: renderTimelineTab, chat: renderChatTab, cases: renderCasesTab };
    $("patient-tab-body").innerHTML = renderers[state.detailTab](patient);
    $$(".pd-tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === state.detailTab));
    if (state.detailTab === "timeline") drawTrendChart($("pd-trend"), patient.checkins);
  }

  function renderPatient() {
    const patient = state.patient;
    if (!patient) return;
    $("patient-hero").innerHTML = renderPatientHero(patient);
    drawGauge($("pd-gauge"), patient.dpi, patient.risk_level);
    drawSparklinesIn($("patient-hero"));
    renderPatientTab();
  }

  function switchDetailTab(tab) {
    state.detailTab = tab;
    renderPatientTab();
    // Chat reads newest-last, so land on the latest message. The whole page scrolls, not an inner box.
    requestAnimationFrame(() => window.scrollTo(0, tab === "chat" ? document.documentElement.scrollHeight : 0));
  }

  // ────────────────────────────────────────────────────────────
  // Case actions
  // ────────────────────────────────────────────────────────────
  function confirmDialog(title, text, confirmLabel) {
    return new Promise((resolve) => {
      const modal = $("confirm-modal");
      $("confirm-title").textContent = title;
      $("confirm-text").textContent = text;
      $("confirm-ok").textContent = confirmLabel;
      const finish = (result) => {
        modal.classList.remove("visible");
        $("confirm-ok").onclick = null;
        $("confirm-cancel").onclick = null;
        resolve(result);
      };
      $("confirm-ok").onclick = () => finish(true);
      $("confirm-cancel").onclick = () => finish(false);
      modal.classList.add("visible");
    });
  }

  async function changeCaseStatus(caseId, status, successMessage) {
    try {
      await api.updateCase(caseId, { status });
      toast(successMessage, "success");
      await refreshAlerts();
      if (state.panel === "patient" && state.openPatientRef) await loadPatientDetail(state.openPatientRef);
      else refreshPatients();
    } catch (error) {
      handleError(error, "Could not update that case.");
    }
  }

  async function saveCaseNote(caseId) {
    const field = $(`note-${caseId}`);
    if (!field) return;
    try {
      await api.updateCase(caseId, { notes: field.value });
      const savedCase = state.patient && state.patient.cases.find((item) => item.id === caseId);
      if (savedCase) savedCase.notes = field.value.trim();
      toast("Note saved", "success", 2000);
    } catch (error) {
      handleError(error, "Could not save the note.");
    }
  }

  async function handleAction(target) {
    const { action } = target.dataset;
    if (action === "open-patient") return openPatient(target.dataset.ref);
    if (action === "video") return window.open(target.dataset.url, "_blank", "noopener");
    if (action === "save-note") return saveCaseNote(target.dataset.case);
    if (action === "set-status") {
      const message = target.dataset.status === "acknowledged" ? "Case acknowledged" : "Marked as in contact";
      return changeCaseStatus(target.dataset.case, target.dataset.status, message);
    }
    if (action === "resolve") {
      const confirmed = await confirmDialog(
        "Resolve this case?",
        `${target.dataset.alias} will leave the open queue. Their history stays in the record.`,
        "Resolve",
      );
      if (confirmed) changeCaseStatus(target.dataset.case, "resolved", "Case resolved");
    }
  }

  // ────────────────────────────────────────────────────────────
  // Navigation
  // ────────────────────────────────────────────────────────────
  function renderPanel(panelId) {
    if (panelId === "alerts") renderAlerts();
    if (panelId === "patients") { renderPatients(); refreshPatients(); }
    if (panelId === "insights") { renderInsights(); refreshPatients(); }
    if (panelId === "account") renderAccount();
    if (panelId === "patient") renderPatient();
  }

  function navigateTo(panelId) {
    $$(".panel").forEach((panel) => panel.classList.remove("active"));
    $$(".dock-item").forEach((dock) => dock.classList.remove("active"));
    $(`panel-${panelId}`).classList.add("active");
    if (MAIN_PANELS.includes(panelId)) state.dockPanel = panelId;
    // The patient screen keeps the tab it was opened from highlighted in the dock
    $(`dock-${state.dockPanel}`).classList.add("active");
    state.panel = panelId;
    window.scrollTo(0, 0);
    renderPanel(panelId);
  }

  // ────────────────────────────────────────────────────────────
  // Live status pill
  // ────────────────────────────────────────────────────────────
  function renderLivePill() {
    const pill = $("live-pill");
    pill.classList.toggle("is-live", state.isLive);
    pill.classList.toggle("is-offline", !state.isLive && state.lastUpdatedAt !== null);
    if (state.lastUpdatedAt === null) {
      $("live-text").textContent = "Connecting";
    } else if (!state.isLive) {
      $("live-text").textContent = "Offline";
    } else {
      const seconds = Math.round((Date.now() - state.lastUpdatedAt) / 1000);
      $("live-text").textContent = seconds < 60 ? `Live · ${seconds}s` : `Live · ${Math.floor(seconds / 60)}m`;
    }
  }

  // ────────────────────────────────────────────────────────────
  // Sign-in
  // ────────────────────────────────────────────────────────────
  // Shows either the email + password fields or the access-code field
  // mode is "account" (email + password), "register" (create a clinician account) or "code" (shared access code)
  function applyLoginMode(mode) {
    state.loginMode = mode;
    const methods = state.signInMethods;
    $("login-account-fields").hidden = mode === "code";
    $("login-setup-fields").hidden = mode !== "register";
    $("login-code-fields").hidden = mode !== "code";
    $("login-title").textContent = mode === "register" ? "Create Clinician Account" : "Clinician Sign-In";
    $("login-subtitle").textContent = {
      account: "Patient histories are confidential. Sign in with your clinician account to continue.",
      register: "Use the email your administrator approved, choose a password, and enter the setup code you were given.",
      code: "Local testing only. Enter the clinician access code to continue.",
    }[mode];
    $("login-submit").textContent = mode === "register" ? "Create account" : "Sign In";
    $("clinician-password").autocomplete = mode === "register" ? "new-password" : "current-password";

    $("login-register-toggle").hidden = !methods.registration || mode === "code";
    $("login-register-toggle").textContent = mode === "register" ? "Already have an account? Sign in" : "New psychiatrist? Create your account";
    $("login-switch-method").hidden = !(methods.account && methods.access_code) || mode === "register";
    $("login-switch-method").textContent = mode === "code" ? "Use email and password instead" : "Use access code instead (local testing)";

    $("login-error").textContent = "";
    setTimeout(() => $(mode === "code" ? "access-code" : "clinician-email").focus(), 60);
  }

  function showLogin() {
    state.authenticated = false;
    $("login-gate").classList.add("visible");
    applyLoginMode(state.signInMethods.account || !state.signInMethods.access_code ? "account" : "code");
  }

  async function handleLoginSubmit(event) {
    event.preventDefault();
    const submit = $("login-submit");
    $("login-error").textContent = "";

    // Step 1: collect what the clinician typed for the chosen method
    const mode = state.loginMode;
    const email = $("clinician-email").value.trim();
    const password = $("clinician-password").value;
    const setupCode = $("setup-code").value.trim();
    const credentials = mode === "code" ? { access_code: $("access-code").value.trim() } : { email, password };
    const missingSomething = !Object.values(credentials).every((value) => value) || (mode === "register" && !setupCode);
    if (missingSomething) {
      $("login-error").textContent = {
        account: "Enter your email and password.",
        register: "Enter your email, a password and the setup code.",
        code: "Enter the access code.",
      }[mode];
      return;
    }
    if (mode === "register" && password.length < 8) {
      $("login-error").textContent = "Use a password of at least 8 characters.";
      return;
    }

    // Step 2: create the account first when registering, then sign in and open the dashboard
    submit.disabled = true;
    try {
      if (mode === "register") await api.register({ email, password, setup_code: setupCode });
      const result = await api.login(credentials);
      state.clinicianEmail = result.clinician_email || "";
      $("clinician-password").value = "";
      $("setup-code").value = "";
      $("access-code").value = "";
      $("login-gate").classList.remove("visible");
      renderAccount();
      startApp();
    } catch (error) {
      $("login-error").textContent = error.message || "Could not sign in.";
    } finally {
      submit.disabled = false;
    }
  }

  async function handleSignOut() {
    try { await api.logout(); } catch { /* signing out locally is enough */ }
    window.location.reload();
  }

  // ────────────────────────────────────────────────────────────
  // Start-up
  // ────────────────────────────────────────────────────────────
  function startApp() {
    state.authenticated = true;
    refreshAlerts();
    refreshPatients();
    renderPanel(state.panel);
    if (state.started) return;
    state.started = true;
    setInterval(refreshAlerts, ALERT_POLL_MS);
    setInterval(refreshPatients, PATIENT_POLL_MS);
    setInterval(renderLivePill, 1000);
  }

  function wireEvents() {
    // Bottom dock
    $$(".dock-item").forEach((dock) => dock.addEventListener("click", () => navigateTo(dock.dataset.panel)));

    // Every button or row that carries data-action
    document.addEventListener("click", (event) => {
      const target = event.target.closest("[data-action]");
      if (target) handleAction(target);
    });
    document.addEventListener("keydown", (event) => {
      const target = event.target;
      if ((event.key === "Enter" || event.key === " ") && target.matches && target.matches('[data-action="open-patient"][role="button"]')) {
        event.preventDefault();
        handleAction(target);
      }
    });

    // Filters and search
    $("alert-filters").addEventListener("click", (event) => {
      const chip = event.target.closest("[data-filter]");
      if (!chip) return;
      state.alertFilter = chip.dataset.filter;
      $$("#alert-filters .chat-chip").forEach((item) => item.classList.toggle("active", item === chip));
      renderAlerts();
    });
    $("patient-filters").addEventListener("click", (event) => {
      const chip = event.target.closest("[data-filter]");
      if (!chip) return;
      state.patientFilter = chip.dataset.filter;
      $$("#patient-filters .chat-chip").forEach((item) => item.classList.toggle("active", item === chip));
      renderPatients();
    });
    $("patient-search").addEventListener("input", (event) => {
      state.patientSearch = event.target.value;
      renderPatients();
    });

    // Patient detail
    $$(".pd-tab").forEach((tab) => tab.addEventListener("click", () => switchDetailTab(tab.dataset.tab)));
    $("btn-back").addEventListener("click", () => history.back());
    window.addEventListener("popstate", () => {
      if (state.panel === "patient") navigateTo(state.returnPanel);
    });

    // Header and account settings
    $("btn-theme").addEventListener("click", () => applyTheme(state.theme === "dark" ? "light" : "dark"));
    $("toggle-theme").addEventListener("change", (event) => applyTheme(event.target.checked ? "dark" : "light"));
    $("row-theme").addEventListener("click", () => applyTheme(state.theme === "dark" ? "light" : "dark"));
    $("btn-sound").addEventListener("click", () => applySound(!state.soundOn));
    $("toggle-sound").addEventListener("change", (event) => applySound(event.target.checked));
    $("row-sound").addEventListener("click", () => applySound(!state.soundOn));
    $("toggle-notify").addEventListener("change", (event) => applyNotify(event.target.checked));
    $("row-notify").addEventListener("click", () => applyNotify(!state.notifyOn));
    $("row-test-alert").addEventListener("click", () => notifyEmergency({
      id: "test-alert", alias: "Test Patient", sev: "SEV-1", source: "chat", text_fragment: "This is only a test alert.", triggers: [],
    }));
    $("row-signout").addEventListener("click", handleSignOut);
    $("login-form").addEventListener("submit", handleLoginSubmit);
    $("login-switch-method").addEventListener("click", () => applyLoginMode(state.loginMode === "account" ? "code" : "account"));
    $("login-register-toggle").addEventListener("click", () => applyLoginMode(state.loginMode === "register" ? "account" : "register"));

    // Browsers only allow sound after a tap, so unlock audio on the first one
    document.addEventListener("pointerdown", unlockAudio, { once: true });
    // Catch up straight away when the doctor returns to this tab
    document.addEventListener("visibilitychange", () => { if (!document.hidden) refreshAlerts(); });
  }

  async function boot() {
    applyTheme(store.get("theme", "dark"));
    applySound(store.get("sound", "true") === "true");
    state.notifyOn = store.get("notify", "false") === "true" && "Notification" in window && Notification.permission === "granted";
    $("toggle-notify").checked = state.notifyOn;
    wireEvents();

    // Sample data mode: no backend needed
    if (isDemo) {
      try {
        await loadScript("/static/js/psychiatrist-demo.js");
      } catch (error) {
        toast(error.message, "error");
        return;
      }
      api = window.AegisPsychiatristDemo.api;
      state.accessMode = "demo";
      $("demo-banner").hidden = false;
      startApp();
      window.AegisPsychiatristDemo.scheduleDemoEmergency();
      return;
    }

    // Real mode: ask the server whether this browser may see patient data
    try {
      const session = await api.session();
      state.accessMode = session.development_open_access ? "development" : "signed_in";
      state.clinicianEmail = session.clinician_email || "";
      state.signInMethods = session.sign_in_methods || state.signInMethods;
      if (!session.authenticated) return showLogin();
      startApp();
    } catch {
      toast("Cannot reach the server. Retrying…", "warning");
      state.authenticated = true;
      startApp();
    }
  }

  boot();
})();
