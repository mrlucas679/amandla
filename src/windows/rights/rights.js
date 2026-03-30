/**
 * rights.js — JavaScript for the AMANDLA Know Your Rights window.
 *
 * Handles: 3-step wizard (incident form → rights analysis → formal letter),
 * WebSocket connection for API calls, PDF generation, clipboard copy,
 * and offline heuristic fallback.
 */

// ── STATE ─────────────────────────────────────────────────
let analysisData = null
let letterText   = ''

// ── WEBSOCKET CONNECTION ─────────────────────────────────
// Rights window needs a WS connection for the preload API
// methods (analyzeRights, generateLetter) to work.
window.amandla.getSessionId().then(function (id) {
  window.amandla.connect(id || 'demo', 'rights')
}).catch(function () {
  window.amandla.connect('demo', 'rights')
})

// UX-4: Connection status indicator for rights window
const rightsStatusDot  = document.getElementById('rights-status-dot')
const rightsConnText   = document.getElementById('rights-conn-text')
window.amandla.onConnectionChange(function (connected) {
  rightsStatusDot.className = connected ? 'connected' : ''
  rightsConnText.textContent = connected ? 'connected' : 'disconnected'
})

// UX-8: Centralised loading spinner show/hide helper
// Replaces duplicate style.display manipulation for loading-msg and loading-msg-2.

/**
 * Show or hide a loading spinner in a given panel.
 * @param {number} panelNumber - 1 for step 2 spinner, 2 for step 3 spinner.
 * @param {boolean} visible - Whether to show (true) or hide (false) the spinner.
 */
function showLoading(panelNumber, visible) {
  var suffix = panelNumber === 1 ? '' : '-' + panelNumber
  var el = document.getElementById('loading-msg' + suffix)
  if (el) el.style.display = visible ? 'block' : 'none'
}

// ── STEP NAVIGATION ───────────────────────────────────────

/**
 * Navigate to a specific step in the 3-step wizard.
 * @param {number} n - Step number (1, 2, or 3).
 */
function goToStep(n) {
  document.querySelectorAll('.panel').forEach(function (p) { p.classList.remove('active') })
  document.getElementById('panel-' + n).classList.add('active')

  for (let i = 1; i <= 3; i++) {
    const ind = document.getElementById('step-' + i + '-indicator')
    ind.className = 'step' + (i === n ? ' active' : i < n ? ' done' : '')
  }
  document.getElementById('div-1').className = 'step-divider' + (n > 1 ? ' done' : '')
  document.getElementById('div-2').className = 'step-divider' + (n > 2 ? ' done' : '')
}

/**
 * Show an error message in the error banner.
 * @param {string} msg - The error message to display.
 */
function showError(msg) {
  const b = document.getElementById('error-banner')
  b.textContent = msg
  b.style.display = 'block'
}

/** Clear the error banner. */
function clearError() {
  document.getElementById('error-banner').style.display = 'none'
}

// ── STEP 1 → 2: ANALYSE ───────────────────────────────────
document.getElementById('analyse-btn').addEventListener('click', async function () {
  clearError()
  const desc = document.getElementById('incident-desc').value.trim()
  const org  = document.getElementById('org-name').value.trim()
  if (!desc) { showError('Please describe what happened (required).'); return }
  if (!org)  { showError('Please enter the organisation or employer name (required).'); return }

  goToStep(2)
  document.getElementById('analysis-card').style.display = 'none'
  showLoading(1, true)

  try {
    const result = await analyseIncident(desc)
    analysisData = result

    document.getElementById('a-what').textContent     = result.what_happened || desc.substring(0, 120)
    document.getElementById('a-location').textContent = result.location       || getIncidentType()
    const sev = (result.severity || 'serious').toLowerCase()
    const sevEl = document.getElementById('a-severity')
    sevEl.textContent = sev.charAt(0).toUpperCase() + sev.slice(1)
    sevEl.className = 'field-value severity-' + sev

    const lawsEl = document.getElementById('a-laws')
    while (lawsEl.firstChild) lawsEl.removeChild(lawsEl.firstChild)
    const laws = result.laws_likely_violated || defaultLaws()
    laws.forEach(function (law) {
      const tag = document.createElement('span')
      tag.className = 'law-tag'
      tag.textContent = law
      lawsEl.appendChild(tag)
    })

    document.getElementById('analysis-card').style.display = 'block'
  } catch (err) {
    // Fallback: show heuristic analysis
    analysisData = heuristicAnalysis()
    populateAnalysis(analysisData)
    document.getElementById('analysis-card').style.display = 'block'
  } finally {
    showLoading(1, false)
  }
})

/**
 * Populate the analysis card with result data.
 * @param {Object} result - Analysis result with what_happened, location, severity, laws_likely_violated.
 */
function populateAnalysis(result) {
  document.getElementById('a-what').textContent     = result.what_happened || ''
  document.getElementById('a-location').textContent = result.location      || ''
  const sev = (result.severity || 'serious').toLowerCase()
  const sevEl = document.getElementById('a-severity')
  sevEl.textContent = sev.charAt(0).toUpperCase() + sev.slice(1)
  sevEl.className = 'field-value severity-' + sev
  const lawsEl = document.getElementById('a-laws')
  while (lawsEl.firstChild) lawsEl.removeChild(lawsEl.firstChild)
  const laws = result.laws_likely_violated || defaultLaws()
  laws.forEach(function (law) {
    const tag = document.createElement('span')
    tag.className = 'law-tag'
    tag.textContent = law
    lawsEl.appendChild(tag)
  })
}

// ── STEP 2 → 3: GENERATE LETTER ───────────────────────────
document.getElementById('generate-btn').addEventListener('click', async function () {
  clearError()
  goToStep(3)
  document.getElementById('letter-box').style.display = 'none'
  document.getElementById('laws-cited').style.display = 'none'
  showLoading(2, true)

  try {
    const result = await generateLetter()
    letterText = result.letter || result

    const lawsDiv = document.getElementById('laws-cited')
    if (result.laws_cited && result.laws_cited.length > 0) {
      // Clear previous content safely (no innerHTML with markup)
      while (lawsDiv.firstChild) lawsDiv.removeChild(lawsDiv.firstChild)
      // Build "Laws cited" header via DOM API — avoids innerHTML XSS vectors
      const header = document.createElement('div')
      header.style.cssText = 'margin-bottom:8px;font-size:12px;color:#8B6FD4;text-transform:uppercase;letter-spacing:1px;'
      header.textContent = 'Laws cited'
      lawsDiv.appendChild(header)
      result.laws_cited.forEach(function (law) {
        const tag = document.createElement('span')
        tag.className = 'law-tag'
        tag.textContent = law
        lawsDiv.appendChild(tag)
      })
      lawsDiv.style.display = 'block'
    }

    document.getElementById('letter-box').textContent = letterText
    document.getElementById('letter-box').style.display = 'block'
  } catch (err) {
    letterText = buildTemplateLetter()
    document.getElementById('letter-box').textContent = letterText
    document.getElementById('letter-box').style.display = 'block'
  } finally {
    showLoading(2, false)
  }
})

// ── BACK BUTTONS ──────────────────────────────────────────
document.getElementById('back-1-btn').addEventListener('click', function () { goToStep(1) })
document.getElementById('back-2-btn').addEventListener('click', function () { goToStep(2) })

// ── COPY ──────────────────────────────────────────────────
document.getElementById('copy-btn').addEventListener('click', function () {
  navigator.clipboard.writeText(letterText).then(function () {
    const btn = document.getElementById('copy-btn')
    const orig = btn.textContent
    btn.textContent = 'Copied!'
    const COPY_FEEDBACK_MS = 2000
    setTimeout(function () { btn.textContent = orig }, COPY_FEEDBACK_MS)
  }).catch(function () {
    // Fallback: select text in letter box
    const range = document.createRange()
    range.selectNodeContents(document.getElementById('letter-box'))
    window.getSelection().removeAllRanges()
    window.getSelection().addRange(range)
  })
})

// ── PDF DOWNLOAD ──────────────────────────────────────────
document.getElementById('print-btn').addEventListener('click', function () {
  if (window.jspdf && window.jspdf.jsPDF) {
    downloadPDF()
  } else {
    // Fallback to browser print if jsPDF failed to load
    window.print()
  }
})

/** Generate and download a PDF of the complaint letter using jsPDF. */
function downloadPDF() {
  const { jsPDF } = window.jspdf
  const doc = new jsPDF({ unit: 'mm', format: 'a4' })

  // Header bar
  doc.setFillColor(139, 111, 212)  // #8B6FD4
  doc.rect(0, 0, 210, 18, 'F')
  doc.setTextColor(255, 255, 255)
  doc.setFontSize(13)
  doc.setFont('helvetica', 'bold')
  doc.text('AMANDLA — Know Your Rights', 14, 12)

  // Letter body
  doc.setTextColor(20, 20, 20)
  doc.setFont('times', 'normal')
  doc.setFontSize(11)

  const MARGIN_LEFT = 20
  const MAX_WIDTH   = 170   // mm
  const LINE_HEIGHT = 6     // mm
  const PAGE_BOTTOM = 275   // mm — start new page after this
  const lines = doc.splitTextToSize(letterText || '(No letter generated)', MAX_WIDTH)

  let y = 26
  for (let i = 0; i < lines.length; i++) {
    if (y > PAGE_BOTTOM) {
      doc.addPage()
      y = 20
    }
    doc.text(lines[i], MARGIN_LEFT, y)
    y += LINE_HEIGHT
  }

  // Footer
  const pageCount = doc.internal.getNumberOfPages()
  for (let p = 1; p <= pageCount; p++) {
    doc.setPage(p)
    doc.setFontSize(8)
    doc.setTextColor(150, 150, 150)
    doc.text(
      'Generated by AMANDLA — South African Sign Language Communication Bridge  |  Page ' + p + ' of ' + pageCount,
      14, 290
    )
  }

  const org = (document.getElementById('org-name').value || 'complaint').replace(/[^a-z0-9]/gi, '_')
  doc.save('AMANDLA_' + org + '_letter.pdf')
}

// ── API CALLS (via WebSocket preload bridge — no direct HTTP) ──

/**
 * Send the incident description to the backend for rights analysis.
 * @param {string} description - The user's description of the incident.
 * @returns {Promise<Object>} The analysis result.
 */
async function analyseIncident(description) {
  // Uses the preload WebSocket bridge instead of direct fetch
  const result = await window.amandla.analyzeRights(description, getIncidentType())
  return result
}

/**
 * Request a formal complaint letter from the backend.
 * @returns {Promise<Object>} The letter generation result.
 */
async function generateLetter() {
  // Uses the preload WebSocket bridge instead of direct fetch
  const result = await window.amandla.generateLetter({
    description:   document.getElementById('incident-desc').value.trim(),
    user_name:     document.getElementById('your-name').value.trim() || 'The Complainant',
    employer_name: document.getElementById('org-name').value.trim(),
    incident_date: document.getElementById('incident-date').value || todayString(),
    analysis:      analysisData
  })
  return result
}

// ── HEURISTICS (offline fallback) ─────────────────────────

/**
 * Get the human-readable incident type from the dropdown.
 * @returns {string} The selected incident type label.
 */
function getIncidentType() {
  const sel = document.getElementById('incident-type')
  return sel.options[sel.selectedIndex].text
}

/**
 * Return default South African laws based on the selected incident type.
 * @returns {string[]} Array of relevant law citations.
 */
function defaultLaws() {
  const type = document.getElementById('incident-type').value
  if (type === 'workplace' || type === 'other') {
    return ['Employment Equity Act s.6', 'Constitution s.9(3)', 'Labour Relations Act s.191']
  }
  return ['Promotion of Equality Act s.7', 'Constitution s.9(3)']
}

/**
 * Build a heuristic analysis when the backend is unavailable.
 * @returns {Object} A fallback analysis object.
 */
function heuristicAnalysis() {
  const desc = document.getElementById('incident-desc').value.trim()
  const MAX_SUMMARY_LENGTH = 150
  return {
    what_happened: desc.length > MAX_SUMMARY_LENGTH ? desc.substring(0, MAX_SUMMARY_LENGTH) + '…' : desc,
    location: getIncidentType(),
    severity: 'serious',
    laws_likely_violated: defaultLaws()
  }
}

/**
 * Get today's date as an ISO string (YYYY-MM-DD).
 * @returns {string} Today's date.
 */
function todayString() {
  return new Date().toISOString().split('T')[0]
}

/**
 * Build a template complaint letter when the backend is unavailable.
 * Uses form field values and standard South African legal citations.
 * @returns {string} The formatted letter text.
 */
function buildTemplateLetter() {
  const yourName = document.getElementById('your-name').value.trim() || 'The Complainant'
  const orgName  = document.getElementById('org-name').value.trim() || '[Organisation Name]'
  const date     = document.getElementById('incident-date').value || todayString()
  const desc     = document.getElementById('incident-desc').value.trim()
  const year     = new Date().getFullYear()
  const ref      = 'AMANDLA-RIGHTS-' + year + '-' + String(Math.floor(Math.random() * 900) + 100)

  return `${todayString()}

[YOUR ADDRESS]
[CITY, PROVINCE, POSTAL CODE]
[EMAIL ADDRESS]

${orgName}
[ORGANISATION ADDRESS]
[CITY, PROVINCE, POSTAL CODE]

Reference: ${ref}

Dear Sir/Madam,

RE: FORMAL COMPLAINT OF UNFAIR DISCRIMINATION AGAINST A PERSON WITH A DISABILITY

I, ${yourName}, hereby lodge a formal complaint of unfair discrimination in terms of the following legislation:

1. The Employment Equity Act, No. 55 of 1998, Section 6, which prohibits unfair discrimination on the basis of disability.
2. The Promotion of Equality and Prevention of Unfair Discrimination Act, No. 4 of 2000 (PEPUDA), Section 7.
3. The Constitution of the Republic of South Africa, Section 9(3), which guarantees the right to equality and prohibits discrimination on the grounds of disability.

On or about ${date}, the following incident occurred:

${desc}

This conduct constitutes unfair discrimination in terms of the above-mentioned legislation. As a person with a disability, I have a constitutional and statutory right to be treated with dignity and to have equal access to [services/employment/public facilities].

DEMANDS:
1. A written apology acknowledging the discriminatory conduct.
2. Confirmation of steps taken to prevent recurrence.
3. Compliance with all applicable disability rights legislation.

I request your written response within 14 (fourteen) days of receipt of this letter. Should I not receive a satisfactory response within this period, I reserve the right to refer the matter to the Commission for Conciliation, Mediation and Arbitration (CCMA), the South African Human Rights Commission (SAHRC), or the Equality Court.

Yours faithfully,

${yourName}
[SIGNATURE]
[DATE]

---
This letter was generated by AMANDLA — South African Sign Language Communication Bridge
Ref: ${ref}`
}

// ── CLEANUP ON CLOSE ─────────────────────────────────────
// Disconnect cleanly when the rights window is closed so the backend
// session is torn down immediately rather than waiting for the WebSocket timeout.
window.addEventListener('beforeunload', function () {
  window.amandla.disconnect()
})

