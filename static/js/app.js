/**
 * AegisMind — App.js (Simple, Quiet, Empathetic Edition)
 * Principal Engineer: Full-Stack + Clinical AI Systems
 *
 * Modules:
 *  - State management & LocalStorage
 *  - Bilingual string map EN / HI with Clinical Glossary
 *  - Consoling AI Companion Chatbot controller (/api/chat)
 *  - Clinical Glossary & Term Explainer modal
 *  - 5-4-3-2-1 Grounding & 432Hz Audio Synthesizer
 *  - 4-7-8 Breathing Pacer
 *  - DPI Gauge & Sparkline Canvas renderer
 *  - Check-in Submission & Multi-Agent triage
 *  - Anonymous Community Forum & Counselor review
 */

'use strict';

// ────────────────────────────────────────────────────────────────
// 1. BILINGUAL STRING MAP & CLINICAL GLOSSARY
// ────────────────────────────────────────────────────────────────
const STRINGS = {
  en: {
    tagline: 'Mental Wellness Companion',
    nav_home:      'Home',
    nav_chat:      'Companion',
    nav_checkin:   'Check-In',
    nav_forum:     'Community',
    nav_counselor: 'Counselor',
    nav_profile:   'Profile',

    // Home Header & Greeting
    greeting_morning:   'Good morning,',
    greeting_afternoon: 'Good afternoon,',
    greeting_evening:   'Good evening,',
    greeting_night:     'Good night,',
    greeting_sub: 'How is your mind feeling today?',
    daily_capsule: 'Daily Grounding',
    coping_toolkit: 'Calm Toolkit',

    // Toolkit Items
    tool_companion:     'AI Companion',
    tool_companion_sub: 'Talk & console',
    tool_ground:        '5-4-3-2-1 Ground',
    tool_ground_sub:    'Sensory anchor',
    tool_audio:         'Calm Waves',
    tool_audio_sub:     '432Hz tone',
    tool_audio_playing: 'Audio active (Tap to stop)',
    tool_breath:        '4-7-8 Breathing',
    tool_breath_sub:    'Instant calm',

    // Chatbot Companion
    chat_title:       'Aegis Companion',
    chat_welcome:     'Hello friend. I am here to listen, support, and console you without any judgment. How are you feeling right now?',
    chat_placeholder: 'Type your thoughts...',
    chip_overwhelmed: 'I feel overwhelmed',
    chip_calm:        'Help me calm down',
    chip_lonely:      'I feel lonely',
    chip_reassure:    'Tell me something comforting',

    // Glossary & Explainer
    glossary_title: 'Clinical Terms Explained',
    btn_got_it:     'Got It',
    def_dpi:        'DPI (Distress Prediction Index) is a composite number from 0.0 to 1.0 reflecting your current emotional load based on your journal words, mood sliders, and voice clarity. Lower numbers mean higher calm.',
    def_delta:      'Trajectory Velocity (ΔDPI) tracks the direction and speed of emotional change over time. A flat or downward slope shows increasing calm, while a steep rise flags potential fatigue.',
    def_pronoun:    'Pronoun Density measures how often first-person words ("I", "me", "my") appear. Research shows that when we feel overwhelmed, our attention naturally shifts inward.',
    def_absolute:   'Absolutist Words are all-or-nothing terms like "always", "never", or "nothing". In Cognitive Behavioral Therapy (CBT), noticing these helps develop gentle, balanced perspectives.',
    def_valence:    'Valence measures whether an emotion feels heavy or pleasant (1 to 5). Arousal measures your physiological energy level from calm (1) to restless (5).',

    // Grounding
    grounding_badge:    'Sensory Anchor',
    btn_prev:           'Previous',
    btn_next:           'Next',
    btn_finish:         'Finish Grounding',
    grounding_complete: 'Grounding complete! You are present and anchored.',

    // Stats
    stat_checkins: 'Check-Ins',
    stat_dpi:      'Avg DPI',
    stat_streak:   'Streak',
    stat_risk:     'Risk Level',
    insight_low_title:      'You\'re doing well',
    insight_low_text:       'Your distress indicators are calm and steady. Keep up your mindful habits.',
    insight_moderate_title: 'Checking in with you',
    insight_moderate_text:  'We noticed some subtle tension in your recent entries. Take a quiet moment to rest.',
    insight_critical_title: 'We\'re here for you',
    insight_critical_text:  'Your wellbeing is important. Please use our Help button or reach out to a counselor.',
    insight_neutral_title:  'Welcome to AegisMind',
    insight_neutral_text:   'Complete your first check-in to begin tracking your wellness journey.',
    start_checkin: 'Start Daily Check-In',

    // Check-in
    checkin_title:      'Daily Check-In',
    valence_label:      'Emotional Valence',
    valence_low:        'Heavy / Low',
    valence_high:       'Positive / High',
    arousal_label:      'Arousal Level',
    arousal_low:        'Calm',
    arousal_high:       'Restless',
    journal_label:      'Reflective Journal',
    journal_placeholder:'Write down your thoughts and feelings...',
    voice_label:        'Voice Note',
    voice_tap:          'Tap to record a voice note',
    voice_recording:    'Recording...',
    voice_done:         'Recording complete',
    voice_score_label:  'Clarity',
    submit_checkin:     'Submit Check-In',
    submitting:         'Processing...',

    // Results
    result_title:    'Check-In Results',
    dpi_label:       'Distress Prediction Index',
    delta_label:     'Trajectory (ΔDPI)',
    nlp_breakdown:   'Linguistic Analysis',
    pronoun_density: 'Pronoun Density',
    absolutist_scan: 'Absolutist Words',
    valence_dist:    'Valence Distress',
    voice_dist:      'Voice Distress',
    sparkline_label: '7-Day DPI Trajectory',
    risk_low:        'Low Risk',
    risk_moderate:   'Moderate Risk',
    risk_critical:   'Critical Risk',
    new_checkin:     'New Check-In',
    recommendation_low:      'Practice 5-4-3-2-1 sensory grounding: 5 things you see, 4 you can touch, 3 you hear, 2 you smell, 1 you taste.',
    recommendation_moderate: 'Consider resting or talking to our AI Companion. A counselor has also been notified to support you.',
    recommendation_critical: 'Your safety is deeply valued. Please contact a helpline immediately or use the emergency breathing pacer.',

    // Crisis
    crisis_title:      'Support Is Available',
    crisis_subtitle:   'You are not alone. Please reach out to trained support counselors 24/7.',
    helpline_tele:     'Tele-MANAS (India)',
    helpline_kiran:    'KIRAN Helpline',
    helpline_988:      '988 Lifeline (US)',
    breath_start:      'Start 4-7-8 Breathing',
    breath_stop:       'Stop',
    breath_inhale:     'Inhale',
    breath_hold:       'Hold',
    breath_exhale:     'Exhale',
    close_crisis:      'Close',

    // Forum & Counselor
    forum_title:       'Community Support',
    forum_compose:     'Share your thoughts anonymously...',
    forum_post_btn:    'Post',
    forum_empty:       'Be the first to share today.',
    counselor_badge:   'HITL Coordinator',
    queue_title:       'Review Queue',
    btn_consult:       'Consultation',
    btn_reviewed:      'Reviewed',

    // Profile & Settings
    setting_theme:     'Dark Mode',
    setting_lang:      'Language',
    setting_export:    'Export Data',
    setting_reset:     'Reset Session',
    consent_title:     'Informed Consent',
    consent_subtitle:  'AegisMind provides confidential mental health support and distress prediction.',
    consent_anon:      'Anonymized Session',
    consent_anon_text: 'All data is processed under a random anonymous token without personal identity tracking.',
    consent_zk:        'Private Text Processing',
    consent_zk_text:   'Your journals are evaluated locally and in memory. Raw text is never retained beyond your session.',
    consent_crisis:    'Emergency Escalation',
    consent_crisis_text:'If severe distress is detected, emergency helpline options and counselor support are provided.',
    consent_agree:     'I Understand & Agree',

    // Toasts
    toast_checkin_ok:   'Check-in recorded successfully',
    toast_crisis_lock:  'Crisis protocol active — support is here for you',
    toast_post_ok:      'Posted anonymously',
    toast_post_crisis:  'Distress detected. Please reach out via Help button',
    toast_reviewed:     'Case marked as reviewed',
    toast_consent_err:  'Please review consent to continue',
    toast_copied:       'Copied token to clipboard',
  },
  hi: {
    tagline: 'मानसिक स्वास्थ्य साथी',
    nav_home:      'होम',
    nav_chat:      'साथी',
    nav_checkin:   'चेक-इन',
    nav_forum:     'समुदाय',
    nav_counselor: 'परामर्श',
    nav_profile:   'प्रोफ़ाइल',

    greeting_morning:   'सुप्रभात,',
    greeting_afternoon: 'शुभ दोपहर,',
    greeting_evening:   'शुभ संध्या,',
    greeting_night:     'शुभ रात्रि,',
    greeting_sub: 'आज आपका मन कैसा महसूस कर रहा है?',
    daily_capsule: 'दैनिक विचार',
    coping_toolkit: 'शांत टूलकिट',

    tool_companion:     'AI साथी',
    tool_companion_sub: 'बातचीत व सांत्वना',
    tool_ground:        '5-4-3-2-1 इंद्रिय',
    tool_ground_sub:    'ग्राउंडिंग एंकर',
    tool_audio:         'शांत तरंगें',
    tool_audio_sub:     '432Hz ध्वनि',
    tool_audio_playing: 'ध्वनि सक्रिय (रोकने हेतु टैप करें)',
    tool_breath:        '4-7-8 श्वास',
    tool_breath_sub:    'तुरंत शांति',

    chat_title:       'Aegis AI साथी',
    chat_welcome:     'नमस्ते मित्र। मैं यहाँ बिना किसी निर्णय के आपकी बात सुनने और सांत्वना देने के लिए हूँ। आप अभी कैसा महसूस कर रहे हैं?',
    chat_placeholder: 'अपने विचार लिखें...',
    chip_overwhelmed: 'मुझे बहुत तनाव है',
    chip_calm:        'शांत होने में मदद करें',
    chip_lonely:      'अकेलापन लग रहा है',
    chip_reassure:    'कुछ तसल्ली देने वाली बात बताएं',

    glossary_title: 'कठिन शब्दों का सरल अर्थ',
    btn_got_it:     'समझ गया/गई',
    def_dpi:        'DPI (संकट पूर्वानुमान सूचकांक) 0.0 से 1.0 तक का एक समग्र स्कोर है जो आपके जर्नल के शब्दों, मनोदशा और आवाज़ के आधार पर मानसिक तनाव को दर्शाता है। कम अंक मन की शांति दर्शाते हैं।',
    def_delta:      'प्रक्षेपवक्र वेग (ΔDPI) समय के साथ आपकी मनोदशा में आ रहे बदलाव की दिशा और गति को मापता है। स्थिर या नीचे की ओर ढलान मानसिक सुधार का संकेत है।',
    def_pronoun:    'सर्वनाम घनत्व यह मापता है कि आप "मैं", "मुझे", "मेरा" जैसे शब्दों का कितना उपयोग करते हैं। जब कोई तनाव में होता है तो उसका ध्यान स्वाभाविक रूप से अंदर की ओर केंद्रित होता है।',
    def_absolute:   'निरपेक्ष शब्द "हमेशा", "कभी नहीं", "कुछ नहीं" जैसे शब्द होते हैं। संज्ञानात्मक व्यवहार थेरेपी (CBT) में इन्हें पहचानना संतुलित सोच विकसित करने में मदद करता है।',
    def_valence:    'संयोजकता मापती है कि भावना भारी है या सुखद (1 से 5)। उत्तेजना आपके ऊर्जा स्तर को शांत (1) से बेचैन (5) तक मापती है।',

    grounding_badge:    'इंद्रिय एंकर',
    btn_prev:           'पिछला',
    btn_next:           'अगला',
    btn_finish:         'समाप्त करें',
    grounding_complete: 'ग्राउंडिंग पूर्ण! आप वर्तमान में स्थिर हैं।',

    stat_checkins: 'चेक-इन',
    stat_dpi:      'औसत DPI',
    stat_streak:   'लय (दिन)',
    stat_risk:     'जोखिम स्तर',
    insight_low_title:      'आप अच्छा कर रहे हैं',
    insight_low_text:       'आपके मानसिक संकेतक शांत और स्थिर हैं। अपनी अच्छी दिनचर्या बनाए रखें।',
    insight_moderate_title: 'आपकी जाँच कर रहे हैं',
    insight_moderate_text:  'आपकी प्रविष्टियों में थोड़ा तनाव दिखा है। कुछ समय शांति से आराम करें।',
    insight_critical_title: 'हम आपके साथ हैं',
    insight_critical_text:  'आपकी सुरक्षा सबसे महत्वपूर्ण है। कृपया सहायता बटन दबाएं या परामर्शदाता से बात करें।',
    insight_neutral_title:  'AegisMind में आपका स्वागत है',
    insight_neutral_text:   'अपनी स्वास्थ्य यात्रा शुरू करने के लिए पहला चेक-इन पूरा करें।',
    start_checkin: 'दैनिक चेक-इन शुरू करें',

    checkin_title:      'दैनिक चेक-इन',
    valence_label:      'भावनात्मक संयोजकता',
    valence_low:        'भारी / कम',
    valence_high:       'सकारात्मक / उच्च',
    arousal_label:      'उत्तेजना स्तर',
    arousal_low:        'शांत',
    arousal_high:       'बेचैन',
    journal_label:      'चिंतनशील जर्नल',
    journal_placeholder:'अपने विचार और भावनाएं यहाँ लिखें...',
    voice_label:        'वॉयस नोट',
    voice_tap:          'वॉयस नोट रिकॉर्ड करने के लिए टैप करें',
    voice_recording:    'रिकॉर्डिंग चालू है...',
    voice_done:         'रिकॉर्डिंग पूर्ण',
    voice_score_label:  'स्पष्टता',
    submit_checkin:     'चेक-इन सबमिट करें',
    submitting:         'विश्लेषण हो रहा है...',

    result_title:       'चेक-इन परिणाम',
    dpi_label:          'संकट पूर्वानुमान सूचकांक',
    delta_label:        'प्रक्षेपवक्र (ΔDPI)',
    nlp_breakdown:      'भाषाई विश्लेषण',
    pronoun_density:    'सर्वनाम घनत्व',
    absolutist_scan:    'निरपेक्ष शब्द',
    valence_dist:       'संयोजकता संकट',
    voice_dist:         'आवाज़ संकट',
    sparkline_label:    '7-दिन DPI प्रक्षेपवक्र',
    risk_low:           'कम जोखिम',
    risk_moderate:      'मध्यम जोखिम',
    risk_critical:      'गंभीर जोखिम',
    new_checkin:        'नया चेक-इन',
    recommendation_low:      '5-4-3-2-1 तकनीक अपनाएं: 5 चीज़ें देखें, 4 छुएं, 3 सुनें, 2 सूंघें, 1 चखें।',
    recommendation_moderate: 'हमारे AI साथी से बात करें या आराम करें। सहायता के लिए परामर्शदाता को सूचित किया गया है।',
    recommendation_critical: 'आपकी जान अनमोल है। कृपया तुरंत हेल्पलाइन से संपर्क करें या 4-7-8 श्वास व्यायाम करें।',

    crisis_title:      'सहायता उपलब्ध है',
    crisis_subtitle:   'आप अकेले नहीं हैं। प्रशिक्षित परामर्शदाता 24/7 आपकी मदद के लिए उपलब्ध हैं।',
    helpline_tele:     'टेली-मानस (भारत)',
    helpline_kiran:    'किरण हेल्पलाइन',
    helpline_988:      '988 लाइफलाइन (US)',
    breath_start:      '4-7-8 श्वास शुरू करें',
    breath_stop:       'रोकें',
    breath_inhale:     'सांस लें',
    breath_hold:       'रोकें',
    breath_exhale:     'सांस छोड़ें',
    close_crisis:      'बंद करें',

    forum_title:       'समुदाय सहायता',
    forum_compose:     'अपने विचार गुमनाम रूप से साझा करें...',
    forum_post_btn:    'पोस्ट',
    forum_empty:       'आज पहले साझा करने वाले बनें।',
    counselor_badge:   'HITL समन्वयक',
    queue_title:       'समीक्षा कतार',
    btn_consult:       'परामर्श',
    btn_reviewed:      'समीक्षित',

    setting_theme:     'डार्क मोड',
    setting_lang:      'भाषा',
    setting_export:    'डेटा निर्यात',
    setting_reset:     'सत्र रीसेट',
    consent_title:     'सूचित सहमति',
    consent_subtitle:  'AegisMind गोपनीय मानसिक स्वास्थ्य निगरानी और सहायता प्रदान करता है।',
    consent_anon:      'अनामीकृत सत्र',
    consent_anon_text: 'सभी डेटा बिना किसी व्यक्तिगत पहचान के यादृच्छिक टोकन के तहत संसाधित होता है।',
    consent_zk:        'निजी पाठ प्रसंस्करण',
    consent_zk_text:   'आपकी जर्नल प्रविष्टियां सुरक्षित रूप से विश्लेषित होती हैं और कभी बेची नहीं जातीं।',
    consent_crisis:    'आपातकालीन सहायता',
    consent_crisis_text:'गंभीर तनाव में आपातकालीन हेल्पलाइन विकल्प प्रदान किए जाते हैं।',
    consent_agree:     'मैं सहमत हूँ',

    toast_checkin_ok:  'चेक-इन दर्ज किया गया',
    toast_crisis_lock: 'संकट सहायता सक्रिय — हम आपके साथ हैं',
    toast_post_ok:     'गुमनाम रूप से पोस्ट किया गया',
    toast_post_crisis: 'तनाव के संकेत मिले। कृपया सहायता बटन का उपयोग करें',
    toast_reviewed:    'मामला समीक्षित चिह्नित',
    toast_consent_err: 'जारी रखने के लिए सहमति आवश्यक है',
    toast_copied:      'टोकन कॉपी किया गया',
  }
};

// ────────────────────────────────────────────────────────────────
// 2. DAILY AFFIRMATIONS
// ────────────────────────────────────────────────────────────────
const AFFIRMATIONS = [
  { text: "You don't have to control your thoughts. You just have to stop letting them control you.", author: "Dan Millman" },
  { text: "Breathe. You are doing much better than you give yourself credit for.", author: "Mindfulness Practice" },
  { text: "This feeling is temporary. You have survived 100% of your hardest days so far.", author: "Resilience Anchor" },
  { text: "Your present situation is not your final destination. Take it one breath at a time.", author: "CBT Reframing" },
  { text: "Peace comes from within. Give yourself permission to slow down today.", author: "Self-Compassion" },
];
let currentAffirmationIdx = 0;

// ────────────────────────────────────────────────────────────────
// 3. 5-4-3-2-1 SENSORY GROUNDING
// ────────────────────────────────────────────────────────────────
const GROUNDING_STEPS = [
  { num: 5, title: 'Sight', desc: 'Look around and acknowledge 5 things you can see right now (e.g. a color, a pattern, an object).' },
  { num: 4, title: 'Touch', desc: 'Acknowledge 4 things you can physically feel (e.g. the chair beneath you, the fabric of your clothes).' },
  { num: 3, title: 'Hearing', desc: 'Listen carefully and acknowledge 3 distinct sounds around you or in the distance.' },
  { num: 2, title: 'Smell', desc: 'Acknowledge 2 things you can smell, or 2 soothing scents you like (e.g. rain, coffee, lavender).' },
  { num: 1, title: 'Taste', desc: 'Acknowledge 1 thing you can taste, or take a slow, mindful sip of fresh water.' },
];
let currentGroundingIdx = 0;

// ────────────────────────────────────────────────────────────────
// 4. WEB AUDIO 432Hz HARMONIC GENERATOR
// ────────────────────────────────────────────────────────────────
let audioCtx = null;
let isAudioPlaying = false;
let osc1 = null, osc2 = null, gainNode = null;

function toggleCalmSound() {
  if (isAudioPlaying) stopCalmSound();
  else                startCalmSound();
}

function startCalmSound() {
  try {
    const AudioContext = window.AudioContext || window.webkitAudioContext;
    if (!audioCtx) audioCtx = new AudioContext();
    if (audioCtx.state === 'suspended') audioCtx.resume();

    osc1 = audioCtx.createOscillator();
    osc2 = audioCtx.createOscillator();
    gainNode = audioCtx.createGain();

    osc1.type = 'sine';
    osc1.frequency.setValueAtTime(432, audioCtx.currentTime);

    osc2.type = 'sine';
    osc2.frequency.setValueAtTime(436, audioCtx.currentTime); // 4Hz alpha wave beat

    gainNode.gain.setValueAtTime(0.01, audioCtx.currentTime);
    gainNode.gain.exponentialRampToValueAtTime(0.06, audioCtx.currentTime + 1.5);

    osc1.connect(gainNode);
    osc2.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    osc1.start();
    osc2.start();
    isAudioPlaying = true;

    $('calm-sound-title').textContent = 'Calm Audio';
    $('calm-sound-status').textContent = t('tool_audio_playing');
    showToast('432Hz Calm Waves Playing', 'info', 2500);
  } catch {
    showToast('Audio not supported on this browser', 'warning');
  }
}

function stopCalmSound() {
  if (!isAudioPlaying) return;
  try {
    if (gainNode && audioCtx) {
      gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.6);
      setTimeout(() => {
        if (osc1) osc1.stop();
        if (osc2) osc2.stop();
        isAudioPlaying = false;
        $('calm-sound-title').textContent = t('tool_audio');
        $('calm-sound-status').textContent = t('tool_audio_sub');
      }, 600);
    }
  } catch {
    isAudioPlaying = false;
  }
}

// ────────────────────────────────────────────────────────────────
// 5. APP STATE
// ────────────────────────────────────────────────────────────────
const State = {
  lang:         localStorage.getItem('aegis_lang')    || 'en',
  forumLang:    localStorage.getItem('aegis_forum_lang') || 'en',
  theme:        localStorage.getItem('aegis_theme')   || 'dark',
  token:        localStorage.getItem('aegis_token')   || null,
  alias:        localStorage.getItem('aegis_alias')   || null,
  consent:      localStorage.getItem('aegis_consent') === 'true',
  history:      JSON.parse(localStorage.getItem('aegis_history') || '[]'),
  currentPanel: 'home',
  lastResult:   null,
  isRecording:  false,
  recordTimer:  null,
  recordSecs:   0,
  voiceScore:   0.75,
  isBreathing:  false,
  breathPhase:  0,
  breathCount:  4,
  breathTimer:  null,
  isCrisisLock: false,
};

function saveState() {
  localStorage.setItem('aegis_lang',    State.lang);
  localStorage.setItem('aegis_forum_lang', State.forumLang);
  localStorage.setItem('aegis_theme',   State.theme);
  if (State.token)   localStorage.setItem('aegis_token',   State.token);
  if (State.alias)   localStorage.setItem('aegis_alias',   State.alias);
  localStorage.setItem('aegis_consent', State.consent);
  localStorage.setItem('aegis_history', JSON.stringify(State.history.slice(-30)));
}

// ────────────────────────────────────────────────────────────────
// 6. UTILITY HELPERS
// ────────────────────────────────────────────────────────────────
const t  = key => (STRINGS[State.lang] || STRINGS.en)[key] || key;
const $  = id  => document.getElementById(id);
const $$ = sel => document.querySelectorAll(sel);

function formatTime(secs) {
  const m = String(Math.floor(secs / 60)).padStart(2, '0');
  const s = String(secs % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function timeAgo(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)   return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff/60)}m ago`;
  if (diff < 86400)return `${Math.floor(diff/3600)}h ago`;
  return `${Math.floor(diff/86400)}d ago`;
}

function greetingKey() {
  const h = new Date().getHours();
  if (h >= 5  && h < 12) return 'greeting_morning';
  if (h >= 12 && h < 17) return 'greeting_afternoon';
  if (h >= 17 && h < 21) return 'greeting_evening';
  return 'greeting_night';
}

function showToast(text, type = 'info', duration = 3000) {
  const container = $('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = text;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

// ────────────────────────────────────────────────────────────────
// 7. THEME & LANGUAGE
// ────────────────────────────────────────────────────────────────
function applyTheme(theme) {
  State.theme = theme;
  document.documentElement.setAttribute('data-theme', theme);
  const toggle = $('theme-toggle-input');
  if (toggle) toggle.checked = (theme === 'dark');
  saveState();
}

function toggleTheme() {
  applyTheme(State.theme === 'dark' ? 'light' : 'dark');
}

function applyLanguage() {
  $$('[data-i18n]').forEach(el => {
    const val = t(el.dataset.i18n);
    if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA') el.placeholder = val;
    else el.textContent = val;
  });
  $$('[data-i18n-ph]').forEach(el => {
    el.placeholder = t(el.dataset.i18nPh);
  });
  const langBtn = $('lang-btn');
  if (langBtn) langBtn.textContent = State.lang === 'en' ? 'हिन्दी' : 'English';
  const curLang = $('current-lang-display');
  if (curLang) curLang.textContent = State.lang === 'en' ? 'English (EN)' : 'हिन्दी (HI)';
  updateHomeGreeting();
  saveState();
}

function toggleLanguage() {
  State.lang = State.lang === 'en' ? 'hi' : 'en';
  applyLanguage();
  showToast(State.lang === 'hi' ? 'भाषा: हिन्दी' : 'Language: English', 'info', 2000);
}

// ────────────────────────────────────────────────────────────────
// 8. NAVIGATION
// ────────────────────────────────────────────────────────────────
function navigateTo(panelId) {
  $$('.panel').forEach(p => p.classList.remove('active'));
  $$('.dock-item').forEach(d => d.classList.remove('active'));

  const panel = $(`panel-${panelId}`);
  const dockBtn = $(`dock-${panelId}`);
  if (panel)   panel.classList.add('active');
  if (dockBtn) dockBtn.classList.add('active');

  State.currentPanel = panelId;

  if (panelId === 'forum')     loadForum();
  if (panelId === 'counselor') loadCounselorQueue();
  if (panelId === 'home')      updateHome();
  if (panelId === 'profile')   updateProfile();
}

// ────────────────────────────────────────────────────────────────
// 9. CONSENT ONBOARDING
// ────────────────────────────────────────────────────────────────
function showConsentModal() {
  const modal = $('consent-modal');
  if (modal) modal.classList.add('visible');
}

function hideConsentModal() {
  const modal = $('consent-modal');
  if (modal) modal.classList.remove('visible');
}

async function acceptConsent() {
  try {
    const res = await fetch('/api/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ consent: true }),
    });
    const data = await res.json();
    if (data.token) {
      State.token   = data.token;
      State.alias   = data.alias;
      State.consent = true;
      saveState();
    }
  } catch {
    State.token   = Array.from(crypto.getRandomValues(new Uint8Array(8))).map(b => b.toString(16).padStart(2,'0')).join('').toUpperCase();
    State.alias   = generateAlias();
    State.consent = true;
    saveState();
  }
  hideConsentModal();
  showToast('Welcome to AegisMind', 'success');
  updateHome();
  updateProfile();
}

function generateAlias() {
  const adj  = ['Quiet','Gentle','Steady','Calm','Warm','Clear','Soft','Bright','Still','Kind','Serene','Hopeful'];
  const noun = ['Willow','River','Stone','Ember','Harbor','Dawn','Meadow','Lantern','Compass','Anchor','Candle','Shore'];
  return `${adj[Math.floor(Math.random()*adj.length)]}${noun[Math.floor(Math.random()*noun.length)]}${Math.floor(Math.random()*90)+10}`;
}

// ────────────────────────────────────────────────────────────────
// 10. CLINICAL GLOSSARY MODAL
// ────────────────────────────────────────────────────────────────
function openGlossaryModal() {
  $('glossary-modal').classList.add('visible');
  applyLanguage();
}

function closeGlossaryModal() {
  $('glossary-modal').classList.remove('visible');
}

// ────────────────────────────────────────────────────────────────
// 11. CONSOLING CHATBOT COMPANION
// ────────────────────────────────────────────────────────────────
async function sendChatMessage() {
  const input = $('chat-input');
  const msg = input.value.trim();
  if (!msg) return;

  input.value = '';
  appendChatBubble('user', msg);

  // Show typing bubble
  const typingId = 'typing-' + Date.now();
  appendTypingBubble(typingId);

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token: State.token || 'ANON',
        message: msg,
        lang: State.lang
      })
    });
    const data = await res.json();
    removeTypingBubble(typingId);

    if (data.reply) {
      appendChatBubble('companion', data.reply);
      if (data.is_crisis) {
        showCrisisModal();
      }
    }
  } catch {
    removeTypingBubble(typingId);
    appendChatBubble('companion', State.lang === 'hi'
      ? 'मैं आपकी बात समझ रहा हूँ। गहरी सांस लें, आप अकेले नहीं हैं।'
      : 'I hear you. Take a slow deep breath — I am right here with you.');
  }
}

function sendQuickChat(text) {
  const input = $('chat-input');
  if (input) input.value = text;
  sendChatMessage();
}

function appendChatBubble(sender, text) {
  const container = $('chat-messages');
  if (!container) return;

  const wrap = document.createElement('div');
  wrap.className = `chat-bubble-wrap ${sender}`;

  if (sender === 'companion') {
    wrap.innerHTML = `
      <div class="chat-avatar">AI</div>
      <div class="chat-bubble">${escHtml(text)}</div>
    `;
  } else {
    wrap.innerHTML = `
      <div class="chat-bubble">${escHtml(text)}</div>
    `;
  }

  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function appendTypingBubble(id) {
  const container = $('chat-messages');
  if (!container) return;
  const wrap = document.createElement('div');
  wrap.id = id;
  wrap.className = 'chat-bubble-wrap companion';
  wrap.innerHTML = `
    <div class="chat-avatar">AI</div>
    <div class="chat-bubble" style="color:var(--text-muted);"><em>...</em></div>
  `;
  container.appendChild(wrap);
  container.scrollTop = container.scrollHeight;
}

function removeTypingBubble(id) {
  const el = $(id);
  if (el) el.remove();
}

// ────────────────────────────────────────────────────────────────
// 12. DAILY AFFIRMATION
// ────────────────────────────────────────────────────────────────
function nextAffirmation() {
  currentAffirmationIdx = (currentAffirmationIdx + 1) % AFFIRMATIONS.length;
  const aff = AFFIRMATIONS[currentAffirmationIdx];
  const textEl = $('affirmation-text');
  const authEl = $('affirmation-author');
  if (textEl && authEl) {
    textEl.textContent = `"${aff.text}"`;
    authEl.textContent = `— ${aff.author}`;
  }
}

// ────────────────────────────────────────────────────────────────
// 13. 5-4-3-2-1 SENSORY GROUNDING
// ────────────────────────────────────────────────────────────────
function openGroundingModal() {
  currentGroundingIdx = 0;
  updateGroundingView();
  $('grounding-modal').classList.add('visible');
}

function closeGroundingModal() {
  $('grounding-modal').classList.remove('visible');
}

function updateGroundingView() {
  const step = GROUNDING_STEPS[currentGroundingIdx];
  $('grounding-step-num').textContent = step.num;
  $('grounding-step-title').textContent = step.title;
  $('grounding-step-desc').textContent = step.desc;

  $('grounding-prev-btn').style.display = currentGroundingIdx === 0 ? 'none' : 'block';
  $('grounding-next-btn').textContent = currentGroundingIdx === GROUNDING_STEPS.length - 1
    ? t('btn_finish')
    : t('btn_next');
}

function nextGroundingStep() {
  if (currentGroundingIdx < GROUNDING_STEPS.length - 1) {
    currentGroundingIdx++;
    updateGroundingView();
  } else {
    closeGroundingModal();
    showToast(t('grounding_complete'), 'success', 3500);
  }
}

function prevGroundingStep() {
  if (currentGroundingIdx > 0) {
    currentGroundingIdx--;
    updateGroundingView();
  }
}

// ────────────────────────────────────────────────────────────────
// 14. SLIDERS & VOICE NOTE
// ────────────────────────────────────────────────────────────────
function initSliders() {
  $$('.mood-slider').forEach(slider => {
    const valueEl = document.getElementById(slider.dataset.valueEl);
    function update() {
      const pct = ((slider.value - slider.min) / (slider.max - slider.min)) * 100;
      slider.style.setProperty('--pct', `${pct}%`);
      if (valueEl) valueEl.textContent = slider.value;
    }
    slider.addEventListener('input', update);
    update();
  });
}

function toggleRecording() {
  if (State.isRecording) stopRecording();
  else                   startRecording();
}

function startRecording() {
  State.isRecording = true;
  State.recordSecs  = 0;
  $('record-btn').classList.add('recording');
  $('voice-status').textContent = t('voice_recording');
  $$('.wave-bar').forEach(b => b.classList.add('animate'));

  State.recordTimer = setInterval(() => {
    State.recordSecs++;
    $('record-timer').textContent = formatTime(State.recordSecs);
    if (State.recordSecs >= 60) stopRecording();
  }, 1000);
}

function stopRecording() {
  clearInterval(State.recordTimer);
  State.isRecording = false;
  $('record-btn').classList.remove('recording');
  $('voice-status').textContent = t('voice_done');
  $$('.wave-bar').forEach(b => b.classList.remove('animate'));

  State.voiceScore = 0.75 + Math.random() * 0.2;
  $('voice-score').textContent = `${Math.round(State.voiceScore * 100)}%`;
}

// ────────────────────────────────────────────────────────────────
// 15. CHECK-IN SUBMISSION
// ────────────────────────────────────────────────────────────────
async function submitCheckin() {
  if (!State.consent) {
    showToast(t('toast_consent_err'), 'warning');
    showConsentModal();
    return;
  }

  const text    = $('journal-input').value.trim();
  const valence = parseFloat($('valence-slider').value);
  const arousal = parseFloat($('arousal-slider').value);
  const btn     = $('submit-btn');

  btn.disabled = true;
  btn.textContent = t('submitting');

  try {
    const res = await fetch('/api/checkin', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        token:       State.token || 'ANON',
        text,
        valence,
        arousal,
        voice_score: State.voiceScore,
      }),
    });
    const data = await res.json();

    if (data.token && !State.token) {
      State.token = data.token;
      State.alias = data.alias;
      saveState();
    }

    State.history.push({
      timestamp:  data.timestamp || new Date().toISOString(),
      dpi:        data.trajectory?.dpi || 0,
      risk_level: data.trajectory?.risk_level || 'low',
      valence, arousal,
    });
    saveState();

    State.lastResult = data;

    if (data.agent_action?.agent === 'crisis_agent') {
      State.isCrisisLock = true;
      $('crisis-lock-overlay').classList.add('active');
      showCrisisModal();
      showToast(t('toast_crisis_lock'), 'error', 6000);
    } else {
      showCheckinResult(data);
      showToast(t('toast_checkin_ok'), 'success');
    }
  } catch {
    const valDist = (5 - valence) / 4;
    const dpi = Math.min(1, valDist * 0.6 + 0.1);
    const risk = dpi > 0.7 ? 'critical' : dpi > 0.4 ? 'moderate' : 'low';

    State.history.push({ timestamp: new Date().toISOString(), dpi, risk_level: risk, valence, arousal });
    saveState();

    const fallbackData = {
      nlp: { fp_density: 0.05, abs_density: 0.02, valence_distress: valDist, voice_distress: 0.2, nlp_score: dpi },
      trajectory: { dpi, delta_dpi: 0.0, risk_level: risk, sparkline: buildSparkline() },
      agent_action: null,
    };
    State.lastResult = fallbackData;
    showCheckinResult(fallbackData);
  } finally {
    btn.disabled = false;
    btn.textContent = t('submit_checkin');
  }
}

function buildSparkline() {
  return State.history.slice(-7).map(h => h.dpi);
}

function showCheckinResult(data) {
  const traj = data.trajectory || {};
  const nlp  = data.nlp || {};
  const risk = traj.risk_level || 'low';
  const dpi  = traj.dpi  || 0;
  const delta = traj.delta_dpi || 0;

  $('checkin-form').style.display = 'none';
  const result = $('checkin-result');
  result.style.display = 'block';

  drawDPIGauge($('dpi-canvas'), dpi, risk);
  $('dpi-number').textContent = dpi.toFixed(2);
  $('delta-dpi-val').textContent = (delta >= 0 ? '+' : '') + delta.toFixed(3);

  const badgeEl = $('risk-badge');
  badgeEl.className = `risk-badge ${risk}`;
  badgeEl.innerHTML = `<span class="badge-dot"></span>${t(`risk_${risk}`)}`;

  setMetric('metric-pronoun',  nlp.fp_density  || 0, 'pronoun_density');
  setMetric('metric-absolute', nlp.abs_density || 0, 'absolutist_scan');
  setMetric('metric-valence',  nlp.valence_distress || 0, 'valence_dist');
  setMetric('metric-voice',    nlp.voice_distress   || 0, 'voice_dist');

  const sparkData = traj.sparkline || buildSparkline();
  drawSparkline($('sparkline-canvas'), sparkData, risk);

  const recEl = $('recommendation-text');
  recEl.innerHTML = `<div class="insight-title">${t(`insight_${risk}_title`)}</div><p class="insight-text">${t(`recommendation_${risk}`)}</p>`;

  const hitlEl = $('hitl-notice');
  if (data.agent_action?.agent === 'hitl_agent') {
    hitlEl.innerHTML = `<div class="insight-card" style="margin-top:8px;"><div class="insight-title">Counselor Notified</div><p class="insight-text">A counselor is available for consultation room: <strong>${data.agent_action.jitsi_room}</strong></p></div>`;
    hitlEl.style.display = 'block';
  } else {
    hitlEl.style.display = 'none';
  }

  result.scrollIntoView({ behavior: 'smooth', block: 'start' });
  updateHome();
}

function setMetric(id, val, labelKey) {
  const el = $(id);
  if (!el) return;
  const disp = (val * 100).toFixed(1) + '%';
  el.innerHTML = `
    <div class="nlp-metric-value">${disp}</div>
    <div class="nlp-metric-label">${t(labelKey)}</div>
    <div class="progress-bar-wrap"><div class="progress-bar-fill" style="width:${Math.min(val*100, 100)}%"></div></div>
  `;
}

function resetCheckinForm() {
  $('checkin-form').style.display = 'block';
  $('checkin-result').style.display = 'none';
  $('journal-input').value = '';
  $('char-count').textContent = '0';
  $('valence-slider').value = 3;
  $('arousal-slider').value = 3;
  initSliders();
  $('record-timer').textContent = '00:00';
  $('voice-status').textContent = t('voice_tap');
  $('voice-score').textContent = '--';
  State.voiceScore = 0.75;
}

// ────────────────────────────────────────────────────────────────
// 16. CANVAS: GAUGE & SPARKLINE
// ────────────────────────────────────────────────────────────────
function drawDPIGauge(canvas, dpi, risk) {
  if (!canvas) return;
  const size = 72;
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  const cx = size/2, cy = size/2, r = 28;
  const startAngle = Math.PI * 0.75;
  const endAngle   = Math.PI * 2.25;
  const fillAngle  = startAngle + (endAngle - startAngle) * dpi;

  const color = risk === 'critical' ? '#EF4444' : risk === 'moderate' ? '#F59E0B' : '#10B981';
  ctx.clearRect(0, 0, size, size);

  ctx.beginPath();
  ctx.arc(cx, cy, r, startAngle, endAngle);
  ctx.strokeStyle = 'rgba(255,255,255,0.08)';
  ctx.lineWidth = 6;
  ctx.lineCap = 'round';
  ctx.stroke();

  if (dpi > 0) {
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, fillAngle);
    ctx.strokeStyle = color;
    ctx.lineWidth = 6;
    ctx.lineCap = 'round';
    ctx.stroke();
  }
}

function drawSparkline(canvas, data, risk) {
  if (!canvas) return;
  const W = canvas.offsetWidth || 180, H = 32;
  canvas.width = W; canvas.height = H;
  const ctx = canvas.getContext('2d');
  const color = risk === 'critical' ? '#EF4444' : risk === 'moderate' ? '#F59E0B' : '#10B981';

  const valid = data.filter(v => v !== null && v !== undefined);
  if (valid.length < 2) return;

  const max = Math.max(...valid, 0.1);
  const min = Math.min(...valid, 0);
  const range = Math.max(max - min, 0.1);
  const pad = 3;

  const pts = data.map((v, i) => ({
    x: pad + (i / (data.length - 1)) * (W - pad * 2),
    y: v !== null ? H - pad - ((v - min) / range) * (H - pad * 2) : null,
  }));

  ctx.clearRect(0, 0, W, H);
  ctx.beginPath();
  let first = true;
  pts.forEach(p => {
    if (p.y === null) return;
    if (first) { ctx.moveTo(p.x, p.y); first = false; }
    else ctx.lineTo(p.x, p.y);
  });
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.stroke();
}

// ────────────────────────────────────────────────────────────────
// 17. CRISIS & BREATHING PACER
// ────────────────────────────────────────────────────────────────
function showCrisisModal() {
  $('crisis-modal').classList.add('visible');
  applyLanguage();
}

function hideCrisisModal() {
  if (State.isCrisisLock) return;
  $('crisis-modal').classList.remove('visible');
  stopBreathing();
}

const BREATH_PHASES = [
  { key: 'breath_inhale', dur: 4, cls: 'inhale' },
  { key: 'breath_hold',   dur: 7, cls: 'hold' },
  { key: 'breath_exhale', dur: 8, cls: 'exhale' },
];

function startBreathing() {
  if (State.isBreathing) { stopBreathing(); return; }
  State.isBreathing = true;
  State.breathPhase = 0;
  $('breath-start-btn').textContent = t('breath_stop');
  runBreathPhase();
}

function stopBreathing() {
  State.isBreathing = false;
  clearTimeout(State.breathTimer);
  $('breath-start-btn').textContent = t('breath_start');
  const circle = $('breath-circle');
  if (circle) circle.className = 'breath-circle';
  $('breath-instruction').textContent = t('breath_inhale');
  $('breath-count').textContent = '4';
}

function runBreathPhase() {
  if (!State.isBreathing) return;
  const phase = BREATH_PHASES[State.breathPhase];
  const circle = $('breath-circle');
  if (circle) circle.className = `breath-circle ${phase.cls}`;
  $('breath-instruction').textContent = t(phase.key);

  let remaining = phase.dur;
  $('breath-count').textContent = remaining;
  const countdown = setInterval(() => {
    remaining--;
    if (remaining >= 0) $('breath-count').textContent = remaining;
    if (remaining <= 0) clearInterval(countdown);
  }, 1000);

  State.breathTimer = setTimeout(() => {
    State.breathPhase = (State.breathPhase + 1) % 3;
    runBreathPhase();
  }, phase.dur * 1000);
}

// ────────────────────────────────────────────────────────────────
// 18. HOME & PROFILE
// ────────────────────────────────────────────────────────────────
function updateHome() {
  const alias = State.alias || 'Friend';
  $('greeting-name').textContent = alias.replace(/\d+$/, '');
  $('greeting-time-str').textContent = t(greetingKey());
  $('greeting-sub-text').textContent = t('greeting_sub');

  const count = State.history.length;
  const avgDPI = count ? (State.history.reduce((a,h) => a + (h.dpi||0), 0) / count).toFixed(2) : '—';
  const lastRisk = count ? State.history[count - 1].risk_level : 'low';

  $('stat-checkins').textContent = count;
  $('stat-dpi').textContent = avgDPI;
  $('stat-streak').textContent = count > 0 ? 1 : 0;
  $('stat-risk').textContent = t(`risk_${lastRisk}`).split(' ')[0];

  const sparkData = buildSparkline();
  if (sparkData.length >= 2) {
    const homeCanvas = $('home-sparkline');
    if (homeCanvas) drawSparkline(homeCanvas, sparkData, lastRisk);
    $('home-sparkline-section').style.display = 'block';
  }
}

function updateHomeGreeting() {
  if ($('greeting-time-str')) $('greeting-time-str').textContent = t(greetingKey());
  if ($('greeting-sub-text')) $('greeting-sub-text').textContent = t('greeting_sub');
}

function updateProfile() {
  $('profile-alias-display').textContent = State.alias || 'Anonymous';
  $('profile-token-display').textContent = State.token ? State.token.slice(0, 16) : '—';
  $('profile-checkin-count').textContent = State.history.length;
  const avgDPI = State.history.length
    ? (State.history.reduce((a,h) => a + (h.dpi||0), 0) / State.history.length).toFixed(2)
    : '—';
  $('profile-avg-dpi').textContent = avgDPI;
}

function resetSession() {
  if (!confirm('Reset all session data?')) return;
  localStorage.clear();
  location.reload();
}

function exportData() {
  const data = { alias: State.alias, token: State.token, history: State.history, exported_at: new Date().toISOString() };
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `aegismind-data-${Date.now()}.json`;
  a.click();
}

function copyToken() {
  if (!State.token) return;
  navigator.clipboard.writeText(State.token).then(() => showToast(t('toast_copied'), 'info'));
}

// ────────────────────────────────────────────────────────────────
// 19. FORUM & COUNSELOR
// ────────────────────────────────────────────────────────────────
async function loadForum() {
  const container = $('forum-feed');
  try {
    const res = await fetch('/api/forum');
    const data = await res.json();
    const activeLanguage = State.forumLang || 'en';
    renderForum((data.posts || []).filter(post => (post.lang || 'en') === activeLanguage));
    updateForumTabs();
  } catch {
    container.innerHTML = `<p style="font-size:12px;color:var(--text-muted);">${t('forum_empty')}</p>`;
  }
}

function setForumLanguage(lang) {
  if (lang !== 'en' && lang !== 'hi') return;
  State.forumLang = lang;
  saveState();
  updateForumTabs();
  loadForum();
}

function updateForumTabs() {
  ['en', 'hi'].forEach(lang => {
    const tab = $(`community-tab-${lang}`);
    if (!tab) return;
    const active = State.forumLang === lang;
    tab.classList.toggle('active', active);
    tab.setAttribute('aria-selected', String(active));
  });
}

function renderForum(posts) {
  const container = $('forum-feed');
  if (!posts.length) {
    container.innerHTML = `<p style="font-size:12px;color:var(--text-muted);">${t('forum_empty')}</p>`;
    return;
  }
  container.innerHTML = posts.map(p => `
    <div class="forum-post" id="post-${p.id}">
      <div class="post-header">
        <div class="post-avatar">${p.alias.slice(0,2).toUpperCase()}</div>
        <div>
          <div class="post-alias">${escHtml(p.alias)}</div>
          <div class="post-time">${timeAgo(p.timestamp)}</div>
        </div>
      </div>
      <div class="post-text">${escHtml(p.text)}</div>
      <div style="display:flex;gap:6px;">
        <button class="reaction-btn" onclick="reactPost('${p.id}','heart')">❤️ <span id="react-heart-${p.id}">${p.reactions.heart}</span></button>
        <button class="reaction-btn" onclick="reactPost('${p.id}','hug')">🫂 <span id="react-hug-${p.id}">${p.reactions.hug}</span></button>
        <button class="reaction-btn" onclick="reactPost('${p.id}','star')">⭐ <span id="react-star-${p.id}">${p.reactions.star}</span></button>
      </div>
    </div>
  `).join('');
}

async function submitForumPost() {
  const textarea = $('forum-compose');
  const text = textarea.value.trim();
  if (!text) return;

  try {
    const res = await fetch('/api/forum', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, lang: State.forumLang || State.lang }),
    });
    if (res.ok) {
      textarea.value = '';
      $('forum-char-count').textContent = '0';
      showToast(t('toast_post_ok'), 'success');
      loadForum();
    }
  } catch {
    showToast('Failed to post', 'error');
  }
}

async function reactPost(postId, reaction) {
  try {
    const res = await fetch(`/api/forum/${postId}/react`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reaction }),
    });
    const data = await res.json();
    if (data.reactions) {
      const el = $(`react-${reaction}-${postId}`);
      if (el) el.textContent = data.reactions[reaction];
    }
  } catch { /* silent */ }
}

async function loadCounselorQueue() {
  const container = $('counselor-queue');
  try {
    const res = await fetch('/api/counselor/queue');
    const data = await res.json();
    $('queue-total-count').textContent = data.total || 0;
    container.innerHTML = (data.queue || []).map(c => `
      <div class="queue-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <strong style="font-size:13px;">${escHtml(c.alias)}</strong>
          <span class="risk-badge ${c.risk_level}">${c.risk_level}</span>
        </div>
        <div class="queue-stats">
          <div class="queue-stat"><div class="queue-stat-value">${c.dpi.toFixed(2)}</div><div class="queue-stat-label">DPI</div></div>
          <div class="queue-stat"><div class="queue-stat-value">${c.delta_dpi.toFixed(3)}</div><div class="queue-stat-label">ΔDPI</div></div>
          <div class="queue-stat"><div class="queue-stat-value">${c.sev || 'SEV-2'}</div><div class="queue-stat-label">Level</div></div>
        </div>
        <div style="display:flex;gap:6px;">
          <button class="btn btn-outline btn-sm" style="flex:1;" onclick="window.open('https://meet.jit.si/${escHtml(c.jitsi_room)}','_blank')">${t('btn_consult')}</button>
          ${!c.reviewed ? `<button class="btn btn-secondary btn-sm" onclick="markReviewed('${c.id}')">${t('btn_reviewed')}</button>` : ''}
        </div>
      </div>
    `).join('');
  } catch {
    container.innerHTML = `<p style="font-size:12px;color:var(--text-muted);">No cases to display.</p>`;
  }
}

async function markReviewed(caseId) {
  try {
    await fetch(`/api/counselor/review/${caseId}`, { method: 'POST' });
    showToast(t('toast_reviewed'), 'success');
    loadCounselorQueue();
  } catch { /* silent */ }
}

function escHtml(str) {
  return (str || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ────────────────────────────────────────────────────────────────
// 20. INITIALIZATION
// ────────────────────────────────────────────────────────────────
function init() {
  applyTheme(State.theme);
  applyLanguage();

  if (!State.consent) {
    setTimeout(showConsentModal, 400);
  } else if (!State.token) {
    State.token = Array.from(crypto.getRandomValues(new Uint8Array(8))).map(b => b.toString(16).padStart(2,'0')).join('').toUpperCase();
    State.alias = generateAlias();
    saveState();
  }

  initSliders();

  const journal = $('journal-input');
  if (journal) {
    journal.addEventListener('input', () => {
      $('char-count').textContent = journal.value.length;
    });
  }

  const fcompose = $('forum-compose');
  if (fcompose) {
    fcompose.addEventListener('input', () => {
      $('forum-char-count').textContent = fcompose.value.length;
    });
  }

  navigateTo('home');
  updateHome();
  updateProfile();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

// Expose globals for inline handlers
window.navigateTo         = navigateTo;
window.toggleTheme        = toggleTheme;
window.toggleLanguage     = toggleLanguage;
window.showCrisisModal    = showCrisisModal;
window.hideCrisisModal    = hideCrisisModal;
window.acceptConsent      = acceptConsent;
window.openGlossaryModal  = openGlossaryModal;
window.closeGlossaryModal = closeGlossaryModal;
window.sendChatMessage    = sendChatMessage;
window.sendQuickChat      = sendQuickChat;
window.nextAffirmation    = nextAffirmation;
window.openGroundingModal = openGroundingModal;
window.closeGroundingModal= closeGroundingModal;
window.nextGroundingStep  = nextGroundingStep;
window.prevGroundingStep  = prevGroundingStep;
window.toggleCalmSound    = toggleCalmSound;
window.toggleRecording    = toggleRecording;
window.submitCheckin      = submitCheckin;
window.resetCheckinForm   = resetCheckinForm;
window.startBreathing     = startBreathing;
window.submitForumPost    = submitForumPost;
window.setForumLanguage   = setForumLanguage;
window.reactPost          = reactPost;
window.loadCounselorQueue = loadCounselorQueue;
window.markReviewed       = markReviewed;
window.resetSession       = resetSession;
window.exportData         = exportData;
window.copyToken          = copyToken;
