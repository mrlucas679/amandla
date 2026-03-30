/**
 * AMANDLA — Mode Controller
 * ==========================
 * TWO MODES:
 *   "sign"   → avatar + sign interpreter runs normally
 *   "assist" → avatar hidden, AAC-style phrase-completion UI shown
 */

const ModeController = (() => {

  let _mode = 'sign'; // 'sign' | 'assist'
  let _listeners = [];

  // Match existing HTML IDs in deaf/index.html
  const AVATAR_CONTAINER_ID  = 'avatar-panel';
  const ASSIST_CONTAINER_ID  = 'assistContainer';
  const TOGGLE_BTN_ID        = 'modeToggleBtn';

  function _show(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = '';
  }

  function _hide(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = 'none';
  }

  function _updateToggleButton() {
    const btn = document.getElementById(TOGGLE_BTN_ID);
    if (!btn) return;
    btn.textContent = _mode === 'sign'
      ? 'Assist Mode'
      : 'Sign Mode';
    btn.setAttribute('aria-pressed', _mode === 'assist');
  }

  function _enterSignMode() {
    _show(AVATAR_CONTAINER_ID);
    _hide(ASSIST_CONTAINER_ID);
    AssistEngine.stop();
    _updateToggleButton();
    _emit('sign');
  }

  function _enterAssistMode() {
    _hide(AVATAR_CONTAINER_ID);
    _show(ASSIST_CONTAINER_ID);
    AssistEngine.start();
    _updateToggleButton();
    _emit('assist');
  }

  function _emit(newMode) {
    _listeners.forEach(fn => { try { fn(newMode); } catch(e) {} });
  }

  return {
    toggle() {
      _mode = _mode === 'sign' ? 'assist' : 'sign';
      _mode === 'sign' ? _enterSignMode() : _enterAssistMode();
    },

    setMode(m) {
      if (m !== 'sign' && m !== 'assist') return;
      _mode = m;
      _mode === 'sign' ? _enterSignMode() : _enterAssistMode();
    },

    isSign()   { return _mode === 'sign'; },
    isAssist() { return _mode === 'assist'; },
    getMode()  { return _mode; },

    onChange(fn) { _listeners.push(fn); },

    init() {
      _enterSignMode();
    },
  };

})();


// ═══════════════════════════════════════════════════════════════════
// ASSIST ENGINE
// ═══════════════════════════════════════════════════════════════════

const AssistEngine = (() => {

  const PHRASE_BANK = [
    // Needs
    "I need help",
    "I need water",
    "I need medicine",
    "I need to sit down",
    "I need to go to the bathroom",
    "I need a moment",
    "I need you to call someone",
    "I need to go to the hospital",

    // Feelings
    "I am feeling unwell",
    "I am feeling dizzy",
    "I am feeling anxious",
    "I am feeling pain",
    "I am feeling tired",
    "I am okay",
    "I am confused",
    "I am scared",

    // Requests
    "Please wait",
    "Please slow down",
    "Please repeat that",
    "Please write it down",
    "Please call a doctor",
    "Please call my family",
    "Please help me",

    // Responses
    "Yes, I understand",
    "No, I do not understand",
    "Can you help me",
    "Can you speak slower",
    "Can you write that down",
    "Can you call someone for me",

    // Location / Direction
    "I want to go home",
    "I want to go to the clinic",
    "I want to go outside",
    "I want to sit here",

    // Emergency
    "This is an emergency",
    "Call an ambulance",
    "I cannot breathe properly",
    "I have chest pain",

    // South African contextual
    "I need to see the doctor",
    "I need my medication",
    "I am Deaf",
    "I use sign language",
    "Please be patient with me",
    "Thank you for your help",
  ];

  let _inputEl       = null;
  let _suggestionsEl = null;
  let _outputEl      = null;
  let _currentInput  = '';
  let _history       = [];

  function _getSuggestions(text) {
    if (!text || !text.trim()) return PHRASE_BANK.slice(0, 6);

    const query = text.toLowerCase().trim();

    const scored = PHRASE_BANK.map(phrase => {
      const p = phrase.toLowerCase();
      let score = 0;

      if (p.startsWith(query))             score = 100;
      else if (p.includes(' ' + query))    score = 80;
      else if (p.includes(query))          score = 60;
      else {
        const words = query.split(/\s+/);
        const allMatch = words.every(w => p.includes(w));
        if (allMatch) score = 40;
      }

      return { phrase, score };
    });

    return scored
      .filter(s => s.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 6)
      .map(s => s.phrase);
  }

  function _renderSuggestions(suggestions) {
    if (!_suggestionsEl) return;
    _suggestionsEl.innerHTML = '';

    if (suggestions.length === 0) {
      _suggestionsEl.innerHTML = '<p style="color:var(--color-text-tertiary);font-size:13px;margin:8px 0">No matches — keep typing or pick from common phrases above</p>';
      return;
    }

    suggestions.forEach(phrase => {
      const btn = document.createElement('button');
      btn.textContent = phrase;
      btn.style.cssText = [
        'display:block', 'width:100%', 'text-align:left',
        'padding:10px 14px', 'margin-bottom:6px',
        'background:var(--color-background-secondary)',
        'border:1px solid var(--color-border-tertiary)',
        'border-radius:8px', 'cursor:pointer',
        'font-size:14px', 'color:var(--color-text-primary)',
        'transition:background 0.15s',
      ].join(';');

      btn.onmouseenter = () => btn.style.background = 'var(--color-background-tertiary)';
      btn.onmouseleave = () => btn.style.background = 'var(--color-background-secondary)';

      btn.onclick = () => _confirmPhrase(phrase);
      _suggestionsEl.appendChild(btn);
    });
  }

  function _confirmPhrase(phrase) {
    _history.push(phrase);
    _renderHistory();

    _currentInput = '';
    if (_inputEl) _inputEl.value = '';
    _renderSuggestions(_getSuggestions(''));

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('amandla:assistPhrase', {
        detail: { phrase }
      }));
    }
  }

  function _renderHistory() {
    if (!_outputEl) return;
    _outputEl.innerHTML = '';
    _history.slice(-5).reverse().forEach(phrase => {
      const div = document.createElement('div');
      div.textContent = phrase;
      div.style.cssText = [
        'padding:8px 12px', 'margin-bottom:4px',
        'background:var(--color-background-info)',
        'border-left:3px solid var(--color-border-info)',
        'border-radius:0 6px 6px 0',
        'font-size:14px', 'color:var(--color-text-primary)',
      ].join(';');
      _outputEl.appendChild(div);
    });
  }

  function _onKeyDown(e) {
    if (e.key === 'Enter') {
      const suggestions = _getSuggestions(_currentInput);
      if (suggestions.length > 0) _confirmPhrase(suggestions[0]);
    } else if (e.key === 'Escape') {
      _currentInput = '';
      if (_inputEl) _inputEl.value = '';
      _renderSuggestions(_getSuggestions(''));
    }
  }

  function _onInput(e) {
    _currentInput = e.target.value;
    _renderSuggestions(_getSuggestions(_currentInput));
  }

  let _recognition = null;

  function _startSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return;

    _recognition = new SpeechRecognition();
    _recognition.continuous      = true;
    _recognition.interimResults  = true;
    _recognition.lang            = 'en-ZA';

    _recognition.onresult = (event) => {
      let interim = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        if (event.results[i].isFinal) {
          _currentInput += event.results[i][0].transcript;
        } else {
          interim = event.results[i][0].transcript;
        }
      }
      const display = _currentInput + interim;
      if (_inputEl) _inputEl.value = display;
      _renderSuggestions(_getSuggestions(display));
    };

    _recognition.onerror = (event) => {
      // 'no-speech' is non-fatal — restart recognition so the user can try again
      if (event.error === 'no-speech') {
        console.warn('[AssistEngine] No speech detected — restarting recognition');
        try { _recognition.start(); } catch(e) { /* already started */ }
        return;
      }
      // All other errors (network, not-allowed, aborted, etc.) are fatal for this attempt
      console.error('[AssistEngine] Speech recognition error:', event.error);
      _stopSpeechRecognition();
    };
    _recognition.start();
  }

  function _stopSpeechRecognition() {
    if (_recognition) { try { _recognition.stop(); } catch(e) {} }
    _recognition = null;
  }

  function _buildUI() {
    const container = document.getElementById('assistContainer');
    if (!container || container.dataset.built) return;
    container.dataset.built = 'true';

    container.style.cssText = 'padding:16px;max-width:600px;margin:0 auto;font-family:var(--font-sans,sans-serif);overflow-y:auto;height:100%';

    const label = document.createElement('p');
    label.textContent = 'Start typing or speak — tap a suggestion to send it';
    label.style.cssText = 'font-size:13px;color:var(--color-text-secondary);margin:0 0 10px';
    container.appendChild(label);

    _inputEl = document.createElement('input');
    _inputEl.type        = 'text';
    _inputEl.placeholder = 'Type here… e.g. "I need"';
    _inputEl.style.cssText = [
      'width:100%', 'box-sizing:border-box',
      'padding:12px 14px', 'font-size:16px',
      'border:1.5px solid var(--color-border-secondary)',
      'border-radius:10px', 'margin-bottom:12px',
      'background:var(--color-background-primary)',
      'color:var(--color-text-primary)',
      'outline:none',
    ].join(';');
    _inputEl.addEventListener('input', _onInput);
    _inputEl.addEventListener('keydown', _onKeyDown);
    container.appendChild(_inputEl);

    const hasSpeech = !!(window.SpeechRecognition || window.webkitSpeechRecognition);
    if (hasSpeech) {
      const micBtn = document.createElement('button');
      micBtn.textContent = 'Hold to Speak';
      micBtn.style.cssText = [
        'padding:10px 18px', 'margin-bottom:14px',
        'background:var(--color-background-success)',
        'color:var(--color-text-success)',
        'border:1px solid var(--color-border-success)',
        'border-radius:8px', 'cursor:pointer', 'font-size:14px',
      ].join(';');
      micBtn.onmousedown  = () => _startSpeechRecognition();
      micBtn.onmouseup    = () => _stopSpeechRecognition();
      micBtn.ontouchstart = () => _startSpeechRecognition();
      micBtn.ontouchend   = () => _stopSpeechRecognition();
      container.appendChild(micBtn);
    }

    _suggestionsEl = document.createElement('div');
    _suggestionsEl.style.cssText = 'margin-bottom:16px';
    container.appendChild(_suggestionsEl);

    const histLabel = document.createElement('p');
    histLabel.textContent = 'Recently sent';
    histLabel.style.cssText = 'font-size:12px;color:var(--color-text-tertiary);margin:0 0 6px;text-transform:uppercase;letter-spacing:0.05em';
    container.appendChild(histLabel);

    _outputEl = document.createElement('div');
    container.appendChild(_outputEl);

    _renderSuggestions(_getSuggestions(''));
  }

  return {
    start() {
      _buildUI();
      _renderSuggestions(_getSuggestions(_currentInput));
      if (_inputEl) _inputEl.focus();
    },

    stop() {
      _stopSpeechRecognition();
    },

    feed(text) {
      _currentInput = text;
      if (_inputEl) _inputEl.value = text;
      _renderSuggestions(_getSuggestions(text));
    },

    addPhrases(phrases) {
      phrases.forEach(p => { if (!PHRASE_BANK.includes(p)) PHRASE_BANK.push(p); });
    },
  };

})();


// ═══════════════════════════════════════════════════════════════════
// AUTO-INIT
// ═══════════════════════════════════════════════════════════════════
if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ModeController.init());
  } else {
    ModeController.init();
  }
}


// ═══════════════════════════════════════════════════════════════════
// EXPORTS — renderer runs with nodeIntegration: false, so only
// window globals are reachable (no Node-style exports).
// ═══════════════════════════════════════════════════════════════════
if (typeof window !== 'undefined') {
  window.ModeController = ModeController;
  window.AssistEngine   = window.AssistEngine || AssistEngine;
}
