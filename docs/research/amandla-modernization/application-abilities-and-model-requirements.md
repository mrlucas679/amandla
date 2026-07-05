# AMANDLA Application Abilities And Model Requirements

Date: 2026-07-05
Status: research artifact, not implementation

## Why This File Exists

The model decision cannot be made in the abstract. AMANDLA is not a generic chatbot. It is a desktop communication bridge with several different abilities, and each ability needs a different proof standard.

Current local runtime check:

| Item | Current Evidence | Meaning |
|---|---|---|
| Machine | MSI Thin 15 B13UC, Intel i5-13420H, about 40 GB RAM. | Good enough for small local LLM evaluation. |
| GPU | RTX 3050 Laptop GPU, about 4 GB VRAM. | Excluded by user for this phase; also too small for serious local vision/sign model work. |
| Ollama | `ollama --version` returns `0.30.10`; API returns an empty model list. | Ollama is installed and serving, but no model is currently available. |
| Python | `python.exe` is still the broken Windows Store shim; `py` is unavailable. | Backend tests and Python runtime are still blocked. |

## Ability Map

| Ability | User Value | Current Code Evidence | Model Requirement | Current Confidence |
|---|---|---|---|---|
| Typed hearing text to deaf avatar | Hearing user can type a message and deaf user sees SASL gloss/avatar. | `backend/services/sasl_pipeline.py`, `sasl_transformer/`, `signs_library.js`. | Deterministic SASL map first; optional LLM must preserve known signs and grammar markers. | Medium after tests; not proven at runtime. |
| Hearing speech to deaf avatar | Hearing user speaks and app converts speech to SASL. | `backend/services/whisper_service.py`, WebSocket `speech_upload`. | STT must preserve intent under accent/noise; translation must not drop safety-critical words. | Low until speech fixtures run. |
| Non-English text/speech to SASL | South African language input can route through English before SASL. | `sasl_pipeline._translate_to_english()` uses Ollama. | Language coverage must be measured per language. | Low; current OpenAI/Whisper language list does not cover all SA official languages. |
| Deaf quick signs to hearing speech | Deaf user taps signs/phrases and hearing user gets English speech. | `backend/services/sign_reconstruction.py`, deaf window quick signs, browser TTS. | Sign sequence reconstruction must not invent meaning. | Medium for quick signs after tests; not proven at runtime. |
| Camera sign recognition | Deaf user signs to camera and app recognizes signs. | `harps_recognizer.py`, `mediapipe_bridge.py`, `ollama_service.py`. | Needs real SASL temporal recognition data and signer-disjoint evaluation. | Very low; current HARPS checkpoint labels are generic `SIGN_00` style classes. |
| Avatar sign production | Deaf user receives visual sign output. | `src/windows/deaf/avatar.js`, `avatar_driver.js`, root `signs_library.js`. | Motion data must be deterministic, reviewable, and matched to sign names. | Medium for procedural playback after canvas tests; linguistic quality needs review. |
| Rights analysis | User describes discrimination and gets structured guidance. | `backend/services/claude_service.py` uses Ollama and template fallbacks. | Model must output structured, non-legal-advice guidance with generic errors and privacy controls. | Low until golden rights tests. |
| Rights letter | User creates a complaint/accommodation letter. | `claude_service.py`, rights WebSocket route. | Draft must be editable, structured, and review-required. | Low until golden rights tests. |
| Conversation history | Session messages survive restart. | `backend/services/history_db.py`, SQLite. | No LLM required; privacy and access-control tests matter. | Medium by inspection; runtime unproven. |
| Emergency overlay | Urgent state reaches role windows. | Electron shortcut and WebSocket emergency path. | No LLM required. | Unproven until E2E test. |

## Model Requirements By Ability

### Speech

Speech is not just transcription. In AMANDLA it is the first step in communication, so missing a word like "doctor", "police", "interpreter", "pain", "unsafe", "cannot", or "must" is a product failure.

Required evidence:

- Word error rate by language and accent.
- Intent preservation on urgent phrases.
- Latency from mic stop to first sign.
- Confidence or fallback behavior when audio is unclear.

### English To SASL

This is a constrained transformation, not creative writing.

Required evidence:

- Required sign recall on golden prompts.
- Forbidden sign rate.
- No invented sign names outside `signs_library.js`.
- Modal and aspect marker preservation: `WILL`, `CAN`, `MUST`, `FINISH`.
- Stable fallback for unknown words.

### SASL To English

This should reconstruct a helpful sentence from known signs, not infer hidden details.

Required evidence:

- Sign sequence intent preservation.
- No invented events.
- No overconfident output for incomplete sign sequences.
- Clear fallback for unknown or ambiguous sequences.

### Camera Sign Recognition

This cannot be solved by a generic text LLM prompt over landmarks.

Required evidence:

- Real SASL labels, not generic labels.
- Consent and model card for training data.
- signer-disjoint evaluation.
- Tests for left-handed signing, lighting, camera angle, distance, and occlusion.
- Unknown-sign rejection.

### Rights

Rights workflows are high-impact. The model can help draft and structure, but the app should not pretend to be a lawyer.

Required evidence:

- Structured output schema validation.
- South African disability-rights source grounding where citations are used.
- Generic user-facing errors.
- No raw provider payloads in UI.
- "Review required" UX before export or sending.

## Desired Result Definition

The desirable AI result for AMANDLA is not "uses the biggest model." It is:

1. The app works offline for core typed communication with deterministic fallbacks.
2. Local models improve fluency or transcription only where they pass product tests.
3. Cloud models are opt-in and visibly improve quality enough to justify privacy, latency, and cost.
4. Camera recognition is not claimed as working until real SASL data and temporal recognition tests prove it.
5. Every model output is validated before it can affect the user interface.
6. The Deaf and hard-of-hearing community define success alongside technical metrics.

## Sources

- Local runtime commands run on 2026-07-05 in `C:\Users\Admin\amandla-desktop-codex-research`.
- AMANDLA `CLAUDE.md`.
- `backend/services/sasl_pipeline.py`.
- `backend/services/sign_reconstruction.py`.
- `backend/services/whisper_service.py`.
- `backend/services/harps_recognizer.py`.
- `backend/harps_model/meta.json`.
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition in the Age of LLMs: https://arxiv.org/html/2604.11225v1
- UCT SASL thesis item: https://open.uct.ac.za/items/5c66b556-1f37-4b1c-b12d-cba33a6f5728
- Northeastern Deaf community survey article: https://news.northeastern.edu/2026/03/19/sign-language-technology-skepticism/
