# AMANDLA Evaluation Harness Plan

Status: proposed, not implemented
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

AMANDLA needs an evaluation harness before major rewrites. The app serves real communication needs, so "looks good" is not enough. Translation, signing, latency, security, and accessibility need repeatable checks.

This plan describes the harness to build after the user approves implementation work.

Companion specs:

- `model-evaluation-fixtures-spec.md` defines exact JSON fixture shapes, scoring fields, and privacy labels.
- `first-model-benchmark-runbook.md` defines the first safe local benchmark sequence after Python is restored.

## Evaluation Layers

| Layer | What It Proves | Tooling |
|---|---|---|
| Static checks | Forbidden patterns are absent | `rg`, ESLint later, Python syntax/lint later |
| Unit tests | Pure transformation logic works | pytest, Vitest |
| Contract tests | WebSocket request/response rules hold | pytest/FastAPI test client or real WebSocket client |
| Golden translation tests | English and local-language prompts produce expected SASL signs | JSON fixture runner |
| Model tests | Ollama models return valid constrained outputs | Local model eval runner |
| Cloud/local comparison | Optional cloud providers show measurable gains over local defaults | Fixture-based provider runner |
| Speech language tests | Target languages and accents are measured, not assumed | Recorded consented fixtures |
| Avatar tests | Sign names map to visible/nonblank animation states | Browser canvas checks and pose snapshots |
| Electron E2E | Real windows connect and core workflows complete | Playwright Electron |
| Accessibility tests | Keyboard, focus, names, contrast, and motion are acceptable | axe, Playwright, manual WCAG checklist |
| Performance tests | Startup, latency, frame rate, and memory stay bounded | Node/Playwright timers, backend timing logs |

## Proposed File Layout

```text
tests/
  golden/
    translation_cases.json
    sign_reconstruction_cases.json
    rights_cases.json
    speech_language_cases.json
    provider_comparison_cases.json
  unit/
    test_sign_maps.py
    test_sasl_transformer.py
    test_history_db.py
  contract/
    test_ws_auth.py
    test_ws_message_contract.py
    test_error_shapes.py
  model/
    test_ollama_contract.py
    test_provider_routing_contract.py
    prompts/
      text_to_sasl.md
      signs_to_english.md
      rights_analysis.md
      rights_letter.md
  e2e/
    electron-smoke.spec.ts
    hearing-to-deaf.spec.ts
    deaf-to-hearing.spec.ts
    emergency.spec.ts
    accessibility.spec.ts
tools/
  eval/
    run_eval.ps1
    summarize_results.ts
    check_forbidden_patterns.ps1
    check_avatar_canvas.ts
reports/
  eval/
    latest.json
    latest.md
```

## Golden Translation Suite

Create fixtures that name the communicative intent, not just raw strings.

Example fixture shape:

```json
{
  "id": "basic-greeting-001",
  "input_language": "en",
  "input_text": "Hello, how are you?",
  "expected_required_signs": ["HELLO", "YOU"],
  "expected_forbidden_signs": [],
  "allow_fingerspell": false,
  "notes": "Basic hearing-to-deaf greeting."
}
```

Case groups:

- Greetings and everyday conversation.
- Medical and safety phrases.
- Rights/legal assistance phrases.
- South African place names and multilingual inputs.
- Modal verbs that must not be filler: `will`, `must`, `can`.
- Aspect markers that must survive: `FINISH`, `WILL`.
- Unknown words that should fingerspell.
- Empty, whitespace, oversized, and hostile text inputs.
- South African English, Afrikaans, isiZulu, isiXhosa, Sesotho, Setswana, Sepedi, Xitsonga, Tshivenda, isiNdebele, and siSwati coverage cases where fixtures are available.

Initial pass criteria:

- Required signs are present.
- Forbidden signs are absent.
- No crash on empty or hostile input.
- Unknown words use the chosen fallback consistently.
- Model output never bypasses sanitisation.

## Model Evaluation

Because Ollama currently has no pulled models, no model should be trusted until measured.

Candidate models:

- `amandla` rebuilt from `Modelfile` for compatibility baseline.
- Optional local fallback models such as `qwen3.5:4b`, `qwen3:4b`, `qwen3.5:2b`, or `qwen3:8b`, depending on measured quality and latency.
- Gemma E2B/E4B-class models as lightweight comparisons if local runtime support exists.
- `gpt-oss:20b` only if memory and latency are acceptable on the target machine.
- `llama3.2:3b` or another small local fallback baseline only if needed.

Model output contract:

- Returns strict JSON when requested.
- Uses only known sign names unless explicitly fingerspelling.
- Does not invent backend message types.
- Does not include chain-of-thought or explanatory prose in structured responses.
- Returns a safe fallback when uncertain.

Model roles:

- `english_to_sasl_helper`
- `sasl_to_english_helper`
- `translation_helper`
- `rights_analysis_helper`
- `rights_letter_helper`
- `experimental_landmark_classifier`

Each role needs a separate prompt version and separate score. A model that passes rights-letter generation does not automatically pass SASL translation.

Metrics:

| Metric | Target |
|---|---:|
| Valid JSON rate | 100% |
| Known sign compliance | 98%+ on golden set |
| Required sign recall | 95%+ initial target |
| Forbidden sign rate | 0 critical forbidden signs |
| Median model latency | To be set after hardware baseline |
| Timeout/error rate | 0 on golden set after warmup |

## Speech And Language Evaluation

AMANDLA should not claim support for all South African languages until the speech pipeline is tested with real fixtures or explicitly consented samples.

Required speech cases:

- Clean microphone audio.
- Noisy room audio.
- Short urgent phrases.
- Code-switched phrases.
- Accented South African English.
- Local-language phrases for each target language where consented data exists.

Provider comparison candidates:

- Local faster-whisper.
- OpenAI `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, or `gpt-realtime-whisper`.
- Google Speech-to-Text Chirp 3.
- Azure Speech.

Metrics:

| Metric | Target |
|---|---:|
| Word error rate | Set after baseline per language |
| Intent preservation | 95%+ on urgent/golden phrases |
| Median transcription latency | To be set after hardware baseline |
| Unsafe omission rate | 0 for medical, safety, and rights-critical phrases |

## Future Sign Recognition Evaluation

Camera sign recognition is not production-ready until the project has a real SASL evaluation set.

Data sheet fields for any future sign dataset:

- Sign label and gloss.
- Signer consent status.
- Handedness.
- Camera angle, distance, lighting, and resolution.
- Annotation source and reviewer.
- Train/validation/test split.
- Whether the signer appears in more than one split.
- Known limitations and excluded populations.

Required camera-recognition tests:

- Isolated signs.
- Continuous sign sequences.
- Unseen signer split.
- Left-handed signing.
- Low-light and partial-occlusion cases.
- Unknown-sign rejection.

The existing HARPS checkpoint is not sufficient production evidence because its metadata uses generic class names such as `SIGN_00` rather than validated SASL labels.

## WebSocket Contract Tests

Contract tests should run without the full Electron app first.

Required cases:

- Valid token accepted.
- Invalid token rejected.
- Unknown role rejected.
- Duplicate role behavior is explicit.
- `text` and `speech_text` are handled identically for hearing role.
- Request/response messages include `request_id`.
- Broadcast messages omit `request_id`.
- `assist_phrase` cannot crash on missing variable names.
- `history_request` cannot read another session unless `list_sessions` is intentionally allowed.
- Oversized text and oversized audio are rejected with generic messages.

## Avatar Evaluation

The avatar needs objective checks before visual redesign:

- Sign library loads exactly once in the deaf role.
- Every sign referenced by backend maps exists in `signs_library.js`.
- Every sign can be queued without throwing.
- Canvas is nonblank after avatar initialization.
- Sign playback changes pose values over time.
- Unknown sign names produce a visible fallback or a logged non-fatal warning.
- Reduced-motion mode is respected for UI effects while preserving communication.

Initial performance targets:

| Metric | Target |
|---|---:|
| Avatar frame rate | 30 FPS minimum on test machine |
| Text to first sign | Under 500 ms after backend response is ready |
| WebSocket round trip | Under 200 ms locally |
| Memory after 1 hour idle | Under 500 MB renderer growth target until measured |

## Accessibility Evaluation

Each role window needs:

- Keyboard-only workflow test.
- Visible focus test.
- Accessible names for icon buttons.
- Status region semantics.
- Color contrast audit.
- Error state audit.
- Reduced-motion check.
- Captions/transcripts for speech-derived content.

Recommended gates:

- `axe-core` for automated violations.
- Playwright keyboard path for each primary workflow.
- Manual review against WCAG 2.2 focus visible, focus appearance, contrast, target size, and status message criteria.

## Security And Privacy Evaluation

Static forbidden patterns:

- `load_dotenv()` outside `backend/main.py`.
- `allow_origins=["http://localhost:8000"]`.
- `str(e)` in HTTP responses.
- `require()` in renderer code.
- Direct renderer `fetch("http://localhost` calls.
- New `src/windows/hearing/signs_library.js`.
- New `src/windows/hearing/avatar.js`.
- Hardcoded API keys or secrets.

Runtime checks:

- Bad WebSocket token rejected.
- Renderer has no Node access.
- Preload exposes only named safe methods.
- Errors returned to users are generic.
- Logs can contain diagnostics but not raw secrets or full provider payloads.
- Cloud model calls are disabled unless the selected mode permits them.
- Cloud evaluation uses fixtures or explicitly consented samples.

## Evaluation Report

Every run should produce:

```json
{
  "timestamp": "2026-07-05T00:00:00+02:00",
  "commit": "unknown",
  "branch": "codex/modernization-research",
  "summary": {
    "passed": 0,
    "failed": 0,
    "blocked": 0
  },
    "blocked_reason": "Python unavailable and Ollama has no pulled models"
}
```

The markdown report should include:

- Environment.
- Versions.
- Gates run.
- Gates blocked.
- Failures with file/line evidence.
- Whether the app can be called working.

## Implementation Order

1. Restore Python and create deterministic/static evaluators before any optional local model benchmarking.
2. Create the fixture files from `model-evaluation-fixtures-spec.md`.
3. Add static forbidden-pattern checks.
4. Add JSON fixture validation and baseline deterministic scoring.
5. Run optional local fallback benchmarks using `first-model-benchmark-runbook.md` only after deterministic fixtures and dataset consent validation pass.
6. Add WebSocket auth/contract tests.
7. Add golden SASL/sign-map tests.
8. Add model JSON compliance tests.
9. Add minimal Playwright Electron launch test.
10. Add avatar canvas and pose checks.
11. Add accessibility gates.

Do not use this harness to hide defects. A failing gate is research data and should keep the corresponding defect open.
