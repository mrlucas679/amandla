---
name: ui-ux-design
description: >
  Design principles, accessibility, and UX best practices for desktop apps, web apps, and the Amandla
  sign language interface. Activate when the user wants to "redesign", "improve the UI", "make it look better",
  "fix the UX", "it feels clunky", "better user experience", "accessibility", "make it more intuitive",
  "design the layout", "color scheme", "typography", "responsive design", or asks how something should
  LOOK or FEEL. Also activate for any new UI component before it's built — design before code.
---

# UI/UX Design Skill

Design is not decoration. Good UX means users accomplish their goals without confusion or frustration.
For Amandla — serving deaf and hearing users, often in stressful real-life communication situations —
the UI must be effortless, clear, and accessible. A confusing UI for a deaf user means a failed communication.

---

## Core Design Principles

### 1. Clarity Over Cleverness
Every element on screen should have an obvious purpose. If you have to explain what a button does,
the design has already failed. Users should NEVER need to read documentation to use the app.

### 2. Feedback for Every Action
Users need to know: Did my action register? Is something happening? Did it work?
- Button clicked → immediate visual response (color change, loading state)
- Message sent → show "sending..." then "delivered"
- Avatar translating → show clear animation, not a frozen screen

### 3. Error States Are Part of the Design
Design the error state FIRST. What does the UI look like when:
- The backend is not running?
- The translation fails?
- The camera isn't working?
- The sign isn't recognized?

Users should never see a blank screen or a cryptic technical error.

### 4. Accessibility Is Not Optional
For Amandla, accessibility is the entire point of the app. But all software should meet WCAG 2.1 AA.

---

## Part 1 — Color and Contrast

### Contrast Ratios (WCAG 2.1 AA)
- Normal text: minimum 4.5:1 contrast ratio against background
- Large text (18px+ bold or 24px+): minimum 3:1
- Interactive elements: 3:1 against adjacent colors

### Amandla Color Recommendations
```css
/* High contrast, accessible palette */
:root {
    /* Dark backgrounds for Amandla's deaf communication context */
    --color-background: #0F1117;
    --color-surface: #1A1D27;
    --color-border: #2D3148;

    /* Text — high contrast */
    --color-text-primary: #F0F2F8;      /* 15.3:1 against background */
    --color-text-secondary: #A0A8C0;    /* 6.2:1 — sufficient for large/secondary */
    --color-text-muted: #626880;        /* Use only for decorative/non-essential text */

    /* Accent */
    --color-accent: #6366F1;            /* Indigo — primary action color */
    --color-accent-hover: #4F46E5;
    --color-success: #22C55E;
    --color-error: #EF4444;
    --color-warning: #F59E0B;

    /* Hearing window vs Deaf window visual distinction */
    --color-hearing-accent: #3B82F6;    /* Blue — hearing side */
    --color-deaf-accent: #8B5CF6;       /* Purple — deaf/signing side */
}
```

### Never Use Color Alone to Convey Meaning
```html
<!-- ❌ Bad — colorblind users can't distinguish -->
<span style="color: red">Error</span>
<span style="color: green">Success</span>

<!-- ✅ Good — icon + color + text -->
<span class="error">❌ Error: Translation failed</span>
<span class="success">✅ Message sent</span>
```

---

## Part 2 — Typography

```css
/* Base font stack — system fonts for performance */
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
    font-size: 16px;         /* Base — never go below 14px for body text */
    line-height: 1.6;        /* Comfortable reading */
    color: var(--color-text-primary);
}

/* Scale */
h1 { font-size: 2rem; font-weight: 700; }
h2 { font-size: 1.5rem; font-weight: 600; }
h3 { font-size: 1.25rem; font-weight: 600; }
body { font-size: 1rem; }
small { font-size: 0.875rem; }  /* Minimum readable size */

/* Never go below 12px for any visible text */
```

---

## Part 3 — Layout and Spacing

### The 8px Grid System
Use multiples of 8 for all spacing. This creates visual rhythm:
```css
:root {
    --space-1: 4px;   /* Tight — icon padding */
    --space-2: 8px;   /* Small — between related elements */
    --space-3: 16px;  /* Medium — section padding */
    --space-4: 24px;  /* Large — between sections */
    --space-5: 32px;  /* XL — major sections */
    --space-6: 48px;  /* XXL — page margins */
}
```

### Amandla's Two-Panel Layout
```css
/* Hearing (left) and Deaf (right) windows side by side */
.app-layout {
    display: grid;
    grid-template-columns: 1fr 1fr;
    height: 100vh;
    gap: 0;
}

.hearing-panel {
    border-right: 2px solid var(--color-border);
    background: var(--color-surface);
}

.deaf-panel {
    background: var(--color-background);
}

/* Avatar takes the top 60% of the deaf panel */
.avatar-container {
    height: 60vh;
    display: flex;
    align-items: center;
    justify-content: center;
}
```

---

## Part 4 — Interactive States

Every interactive element needs 4 states:
```css
.button {
    background: var(--color-accent);
    transition: all 0.15s ease;
}

/* 1. Default */
.button { background: var(--color-accent); }

/* 2. Hover — shows it's clickable */
.button:hover { background: var(--color-accent-hover); transform: translateY(-1px); }

/* 3. Active/pressed — confirms click */
.button:active { transform: translateY(0); }

/* 4. Disabled — clearly not clickable */
.button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none;
}
```

---

## Part 5 — Accessibility for Amandla

### Screen Reader Support
```html
<!-- Always use semantic HTML -->
<button aria-label="Send message to sign language avatar">
    <svg aria-hidden="true">...</svg>
    Send
</button>

<!-- Live regions for dynamic content (avatar status) -->
<div aria-live="polite" aria-atomic="true" class="sr-only">
    <!-- Screen readers announce changes here -->
    <span id="avatar-status"></span>
</div>
```

### Keyboard Navigation
```css
/* Never remove focus outlines without replacing them */
:focus-visible {
    outline: 2px solid var(--color-accent);
    outline-offset: 2px;
}

/* Remove outline only for mouse clicks, not keyboard */
:focus:not(:focus-visible) {
    outline: none;
}
```

### Sign Language Avatar Accessibility
- Provide text captions alongside the avatar animation (already in Amandla with `sasl_text`)
- Avatar should have an "idle/ready" visual state so users know it's waiting
- Animation speed should be adjustable for comprehension
- Provide a text fallback when avatar fails to load

---

## Part 6 — Loading and Error States

```html
<!-- Loading state -->
<div class="avatar-container" aria-busy="true">
    <div class="loading-spinner" aria-label="Avatar is translating..."></div>
</div>

<!-- Error state — clear, actionable -->
<div class="error-state" role="alert">
    <span class="error-icon">⚠️</span>
    <p>Couldn't connect to translation service.</p>
    <button onclick="reconnect()">Try Again</button>
</div>

<!-- Empty state — what to do -->
<div class="empty-state">
    <p>Waiting for a message to translate...</p>
    <p class="hint">Type or speak in the hearing window to begin.</p>
</div>
```

---

## Part 7 — Design Review Checklist

Before any UI is shipped:
- [ ] All text passes contrast ratio test (use https://webaim.org/resources/contrastchecker/)
- [ ] All interactive elements have hover, active, and focus states
- [ ] All error states are designed and implemented
- [ ] Loading states prevent user confusion
- [ ] Keyboard navigation works throughout
- [ ] Screen reader tested (or at least checked with HTML semantics)
- [ ] Works at different window sizes / zoom levels
- [ ] Color is never the ONLY way to convey information

---

## Environment Notes

**In Claude Code (terminal):** Check for common accessibility issues:
```bash
# Check for missing alt text
grep -rn "<img" src/ --include="*.html" | grep -v "alt="
# Check for missing button labels
grep -rn "<button" src/ --include="*.html" | grep -v "aria-label\|>[^<]"
```

**In Claude.ai (browser):** Describe the design before creating CSS.
For any new UI element, start with: "What does the user see? What do they do? What feedback do they get?"
