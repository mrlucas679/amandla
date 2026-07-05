# AMANDLA MASTER PLAN

**Status: the single source of truth. Every other planning document is history.**
Date: 2026-07-05
Owner: mrlucas679. Executor: engineering (human + AI agents).
Supersedes: `PROJECT_PLAN.md`, `INVESTIGATION_AND_PLAN.md`, `PRODUCTION_READINESS.md`,
`AMANDLA_FINAL_BLUEPRINT.md`, `AMANDLA_MISSING_PIECES.md`, everything in `archive/`,
and the strategy content of `docs/research/amandla-modernization/` (kept as reference only).

---

## 0. The Core Diagnosis

Rule one: understand the core thing you are fixing before you fix anything.

AMANDLA did not fail at the hackathon because of any single bug. It failed because of
**three root causes**, and every visible bug traces back to one of them:

1. **It promised the impossible part and neglected the possible part.**
   Real-time camera SASL recognition does not exist anywhere on Earth at production
   quality — UCT's best result is BLEU-4 1.35 from 5 hours of studio data, and their own
   thesis says it is far from practical. We demoed the impossible half (camera → sign
   recognition via an LLM guessing from landmarks) and under-invested in the possible
   half (reliable hearing→deaf communication with a trustworthy avatar). Judges saw the
   impossible half fail.

2. **There was never a definition of "working."**
   No golden test cases, no latency budget, no contract for the WebSocket protocol, no
   way to tell a model hallucination from an application bug. When you cannot measure
   working, every demo is a coin flip.

3. **A small LLM sat in the hot path of a safety-relevant system.**
   The live translation pipeline consults the LLM *first* and rules *second*
   (`backend/services/sasl_pipeline.py`, tier 1 = Ollama, tier 2 = rules — the exact
   inversion of our own stated strategy). A hallucinating 3B model in the critical path
   of a clinic conversation is not a bug; it is an architecture decision that guarantees
   bugs.

Everything in this plan flows from fixing those three things:
**rescope to the reliable core, define working with tests, and remove untrusted
inference from the hot path.**

---

## 1. What the Product Actually Is

AMANDLA v1.0 is **not** a sign-language translation AI. It is an
**assistive communication workstation** for a hearing person and a Deaf person who are
in the same room and do not share a language — a clinic counter, a Home Affairs desk, a
school office, a pharmacy. SASL became South Africa's 12th official language in 2023;
government services now carry a legal obligation they cannot staff with interpreters.
That is the market, and it does not need AI magic — it needs reliability.

### The v1.0 communication loop (all of it buildable today)

| Direction | Path | Trust level |
|---|---|---|
| Hearing → Deaf | Speech (Whisper) or typed text → deterministic SASL gloss → avatar + gloss text | Deterministic, testable |
| Deaf → Hearing | Quick-sign buttons, assist phrases, typed text → English text + TTS | Deterministic, testable |
| Confirmation | Speaker sees their own transcript; Deaf user sees gloss; either can flag "that's wrong" | Human-in-the-loop |

### Explicitly OUT of v1.0

- Camera sign recognition (research track only — Section 7).
- Any claim of supporting all 11 spoken languages (each language earns its claim through
  fixtures, one at a time; v1.0 claims English + measured Afrikaans/isiZulu STT only
  after fixtures pass).
- LLM-generated translations shown to users without deterministic validation.
- Mobile apps, web deployment, multi-device sessions. (Planned, not now.)

### The long game (what makes this a company, not a tool)

Every consented interaction becomes SASL training data. The dataset — not the model,
not the app — is the moat. No one on Earth has a large, diverse, real-world,
consent-based SASL corpus. Section 7 is the plan to build it. The app is the collection
instrument; the product funds the dataset; the dataset eventually delivers the model
that makes the impossible half possible.

---

## 2. Decisions (all made — none open)

The failed project drowned in open questions. These are closed. Reopen one only with
evidence that it is wrong, written into this file.

| # | Question | Decision | Why |
|---|---|---|---|
| D1 | Split screen or separate windows? | **One window, one shared screen, "Counter Mode":** hearing pane and Deaf pane side by side, Deaf pane can flip 180° for across-the-counter tablets. Kill the current three-BrowserWindow model. | Watch how it's really used: one device on a counter between two people. Two windows on one machine served the demo, not the users. |
| D2 | Rights workflow placement | A **separate workspace** reachable from the main screen, not a third window. | It's a documentation task, not a live conversation. |
| D3 | Frontend stack | **React 19 + TypeScript + Vite in Electron**, migrated only after Phase 1 gates pass. Keep FastAPI backend. No Tauri, no Next.js, no rewrite of the backend. | Accepts the research ADR. The current imperative JS is untestable; but a UI rewrite before the protocol is contracted just repaints the failure. |
| D4 | Live translation order | **Rules first. LLM last, constrained, optional.** Reorder `sasl_pipeline.py`: phrase map → rule transformer → (only if coverage < threshold AND Ollama present) schema-constrained LLM whose output is validated against the known-sign list before use. | Root cause #3. A deterministic system that says "I don't know this word — fingerspelling it" beats a fluent hallucination every time, especially in a clinic. |
| D5 | Local LLM role | Optional enhancer only. App is **fully functional with Ollama absent**. Missing-Ollama is a designed state, not an error. | The demo died when dependencies weren't running. The product must not. |
| D6 | Cloud AI role | Three modes: `LOCAL_ONLY` (default), `QUALITY_CLOUD` (explicit user toggle, for rights letters + hard STT), `RESEARCH_EVAL` (dev only). Cloud calls happen in backend only, schema-validated, logged with provider/model/latency. Frontier cloud models are the **engineering assistants** (architecture, debugging, annotation tooling) — never the production translator. | Matches the multi-model principle: strong reasoning models where accuracy matters, small/cheap models for routine tasks, specialized models (STT, vision, animation) for their domains. One model doing everything was the hackathon mistake. |
| D7 | Speech-to-text | Local faster-whisper is the default. Cloud STT (Google Chirp 3 / OpenAI / Azure — evaluated on SA-language fixtures, not marketing pages) available in QUALITY_CLOUD. Every supported language ships with a fixture file proving WER and urgent-phrase preservation. | "Supports isiZulu" is a claim we earn per language. |
| D8 | Camera recognition | Research track, separate module, feature-flagged off in product builds. The HARPS checkpoint (generic `SIGN_00` labels, perfect metrics = toy data) is quarantined to `research/` with a model card saying exactly that. | Root cause #1. It returns to the product only through the Section 7 gates. |
| D9 | WebSocket auth | **Subprotocol auth** (`Sec-WebSocket-Protocol: amandla-<secret>`), not `?token=` query strings. One PR changes preload + handler + docs + tests together. | Tokens in URLs end up in logs. The research was right; the codebase drifted the wrong way. |
| D10 | HTTP security | Kill `allow_origins=["*"]`. Mutating HTTP routes require the session secret header; CORS restricted to the app origin. Generic error messages everywhere (`detail=str(e)` in `sasl_transformer/routes.py:83` dies in Phase 0). | Any browser tab can currently POST audio to localhost:8000. That's not an invariant, it's a footgun that was documented as an invariant. |
| D11 | Branches | **`main` is the only long-lived branch.** `claude/festive-cannon` (merged) — delete. `codex/modernization-research` — this file absorbs its decisions; branch archived (tag `research-2026-07`, then delete). `dev` — reconcile its uncommitted work within Phase 0, then delete. All work via short-lived PR branches into `main`, CI-gated. | Three parallel realities produced three parallel failures. |
| D12 | Repo cleanup | Execute in Phase 0: delete `archive/` (12 stale docs), `amandla_sasl_transformer2/`, duplicate Ghaziasgar PDF, tracked SQLite sidecars (`data/*.db*` → gitignore). Move `ASL-Sensor-Dataglove-Dataset/` (281 MB of ASL *glove sensor* CSVs — wrong language, wrong modality) out of the repo to external storage. `SASL DOCUMEENTS/` → `docs/research/sasl-sources/` (spelling fixed). | Noise made every audit slower and every AI agent dumber. Tune it down permanently. |
| D13 | Evaluation metric for progress | **Fixtures passing, latency percentiles, Deaf-reviewer scores, crash-free sessions.** Never document count. | The research loop charted its own markdown output as progress. Banned. |
| D14 | Avatar | Keep the Three.js engine + keyframe pipeline (merged 2026-07-05: `signWithFrames`, TransitionEngine keyframe playback, converter/recorder/merge tools). Priority is **data through that pipeline**, not engine rework: record real signers for the 130-sign library, Deaf reviewer scores each sign. | The engine was never the problem; synthetic hand-authored poses were. The pipeline to fix that now exists — use it. |
| D15 | Language of record | SASL is a language, not signed English. The gloss layer (SOV, time-first, NMMs) stays the intermediate representation, and a SASL linguist reviews the grammar rules — the transformer's rules were written by developers, not signers. | Linguistic correctness is a product feature we've never validated with a native signer. |
| D16 | Team reality | Solo founder + AI engineering agents. First two spends: **(1) a Deaf consultant (design partner + sign reviewer, monthly retainer), (2) a SASL interpreter part-time for the fixture/gloss review.** No other hires until pilot. | An SASL product with zero Deaf people in the loop is how we got a sign library no signer ever verified. |
| D17 | Pilot target | One site, one scenario: a school for the Deaf front office OR one clinic reception (whichever partnership lands first via DeafSA/SLED/NID — Section 8). Scripted evaluation dialogue, measured. | A product is proven at a counter, not a demo table. |

---

## 3. Information Still Missing (and the decision made in its absence)

Asked and answered honestly — these are the things this plan *cannot* derive from code
or research, with the default I've decided until the information exists:

| Missing information | How to get it | Decision meanwhile |
|---|---|---|
| How a real counter conversation actually flows (turn-taking, interruptions, pointing at the screen) | One observation day at a Deaf school/clinic with the Deaf consultant. Cheapest, highest-value research this project can do. | Counter Mode designed for strict turn-taking with a visible "your turn" cue; revise after observation. |
| Whether our 130 signs are correct SASL | Deaf consultant reviews each sign video against the avatar (the validator tool exists). | All signs carry confidence scores; below-threshold signs fall back to fingerspelling. |
| Dataset licensing for pretraining corpora | Verify each license before download (Section 7 table). | No corpus enters training until license verified. **`SignVerse-2M` (mentioned in prior AI research) could not be verified as a real dataset — treat as unconfirmed until a URL and license exist. This is exactly the hallucination class we are defending against; we apply the same standard to our own plans.** |
| POPIA legal review for biometric collection | One consult with a SA privacy attorney before the first consent screen ships; university ethics board via UCT/Wits partnership. | No real-person data collection until Section 7 governance gates pass. Synthetic fixtures only. |
| Founder's weekly hours + budget envelope | Owner states it when known. | Phases are sequenced solo-friendly: one phase at a time, each independently valuable if the project pauses. |

---

## 4. Target Architecture

```
┌────────────────────────── One Electron window ──────────────────────────┐
│  Counter Mode: [ Hearing pane | Deaf pane (flippable) ]  [Rights ws]    │
│  React 19 + TS + Vite renderer                                          │
│  └── typed preload bridge only (no fetch, no require, zod-validated)    │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │ WebSocket (subprotocol auth, typed contract)
┌──────────────────────────────┴───────────────────────────────────────────┐
│ FastAPI backend (local)                                                  │
│  TaskRouter — every request declares task + mode (LOCAL_ONLY default)    │
│   ├─ Translation: phrase map → SASL rules → [optional constrained LLM]   │
│   │               → known-sign validation → coverage score → gloss       │
│   ├─ Speech: faster-whisper │ cloud STT (QUALITY_CLOUD only)             │
│   ├─ Rights: templates │ cloud drafting (QUALITY_CLOUD, review-required) │
│   ├─ Recognition: DISABLED in product; research flag only                │
│   └─ EvalLogger: provider, model, latency, validation, fallback reason   │
│  History (SQLite) · Rate limits · Session mgmt                           │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
        signs_library.js (130 signs, keyframe-capable) + SIGN_OVERRIDES
        (real recorded data via convert/record/merge pipeline)
        → Three.js avatar (GLB, NMMs, per-sign duration)
```

**Hallucination containment (applies to every model output, local or cloud):**
model reads only the context it needs; output must match a JSON schema; sign names must
exist in the library; below-confidence → explicit "I don't know / fingerspell / ask to
repeat" rather than a guess; every accepted output logged with its validation result.
The model never gets to be the last word — the validator is.

**Latency budgets (measured in CI once the harness exists, enforced before pilot):**

| Path | Budget |
|---|---|
| Typed text → first sign on avatar | ≤ 1.0 s |
| Speech end → first sign | ≤ 3.0 s |
| Quick-sign tap → spoken TTS | ≤ 0.5 s |
| Avatar frame rate | ≥ 30 fps |
| Round-trip WS (local) | ≤ 200 ms |

---

## 5. Definition of Working (the tests that gate everything)

Built in Phase 1, run in CI forever. A feature without a gate does not ship.

1. **Golden translation fixtures** (`tests/golden/translation_cases.json`):
   greetings, daily, medical, rights, modals (WILL/MUST/CAN), aspect (FINISH),
   unknown-word fingerspell, hostile input, per-language cases. Scoring: required-sign
   recall, forbidden-sign rate, **word-order correctness** (SOV/time-first — a
   bag-of-signs score is not a SASL score), marker preservation, coverage.
2. **Sign reconstruction fixtures** — deaf→hearing intent preservation, zero invented facts.
3. **Speech fixtures** — per language, WER + urgent-phrase omission rate (zero tolerance
   for dropped "help/pain/doctor/police/must/cannot").
4. **WebSocket contract tests** — auth (subprotocol accept/reject), roles, request_id
   rules, assist path, oversized input, history isolation.
5. **Avatar gates** — every backend-emitted sign exists in the library; queueing never
   throws; canvas non-blank; keyframe signs play transition→frames→hold (regression
   test for the 2026-07-05 engine fix); fps benchmark.
6. **Static forbidden patterns** (CI job): `detail=str(e)`, renderer `fetch(`,
   renderer `require(`, `load_dotenv` outside main, wildcard CORS, hardcoded keys.
7. **Accessibility gates** — axe, keyboard-only paths for send/reply/emergency, WCAG 2.2
   contrast, reduced-motion, focus visibility.
8. **Packaged-build gate** — installer runs on a clean Windows VM with no Python and no
   Ollama; app reaches Counter Mode with deterministic translation working.

---

## 6. Phases

Sequenced so each phase leaves the project better even if everything pauses afterward.
No calendar promises — exit gates instead. Solo + AI-agent realistic.

### Phase 0 — Stop the Bleeding (small, immediate)
- Fix `sasl_transformer/routes.py:83` generic error (last live defect from the register).
- **Reorder the pipeline rules-first (D4)** with tests proving the order.
- Auth to subprotocol (D9); CORS/session-header hardening (D10).
- Repo cleanup (D12) + branch consolidation (D11).
- Reconcile `dev` branch's uncommitted work; then single-branch world.
- CI extended: static forbidden-pattern job, npm production audit job.
- **Exit gate:** CI green on main including new jobs; repo ≤ half its current size;
  one branch; pipeline order proven by test.

### Phase 1 — Define Working (the harness)
- Write all fixture files + the deterministic scorer (this is days, not weeks — the
  specs already exist in the research; they just were never typed in).
- WS contract tests; latency measurement harness; packaged-build smoke on clean VM.
- SASL interpreter reviews the grammar rules + top-50 fixtures (D15/D16 spend starts).
- **Exit gate:** every Section 5 gate exists and runs in CI; baseline numbers recorded;
  rules-only pipeline scores published as the number to beat.

### Phase 2 — Counter Mode (the product UX)
- React/TS/Vite scaffold; typed protocol package shared by preload + renderer + tests.
- One window, Counter Mode layout, flippable Deaf pane, turn indicator, emergency
  action, offline/missing-Ollama designed states, rights workspace.
- Migrate hearing pane → deaf pane (avatar behind a React adapter, engine untouched) →
  rights. Delete legacy renderer only after parity gates.
- Observation day happens before layout freeze (Section 3).
- **Exit gate:** scripted clinic dialogue completed end-to-end on the packaged build by
  two non-developers; all accessibility gates pass.

### Phase 3 — Real Sign Data Through the Avatar (parallel with Phase 2)
- Record the 130-sign library with a real signer via `scripts/record_signs.py`;
  merge via `scripts/merge_sign_data.py` overrides; Deaf consultant scores each sign
  (validator tool); NMMs from data, not hardcode.
- Priority order: quick-signs, medical, rights, greetings, then the rest.
- Expand library toward 300 signs driven by pilot-site vocabulary.
- **Exit gate:** ≥ 90% of priority signs rated "understandable" by Deaf reviewer;
  keyframe (real) data driving ≥ the top-50 signs.

### Phase 4 — Pilot
- One site (D17), consented participants, scripted + free dialogues.
- Measure: task completion time vs. pen-and-paper baseline, comprehension scores,
  latency percentiles, crash-free rate, fingerspell rate, coverage.
- **Exit gate:** the site asks to keep it. (The only exit gate that matters.)

### Phase 5+ — Scale What Worked
- Second site type; QUALITY_CLOUD rights letters; measured additional languages;
  kiosk/tablet packaging; networked two-device sessions. Each gated the same way.

---

## 7. The Dataset & Model Track (parallel, slow, decisive)

This is the moat. It runs beside the product, never blocking it, funded by it.

### 7.1 Governance before a single frame is captured
- **POPIA compliance is the floor:** sign video is biometric + potentially health-adjacent
  special personal information. Appoint the Information Officer (founder, initially),
  explicit consent records, purpose limitation, retention schedule, breach protocol,
  s72 rules before any cross-border processing (which includes cloud annotation
  assistance — cloud models see consented samples only, and never as ground truth).
- University ethics partnership (UCT — they built the 2024 SASL SLT thesis — or Wits)
  for IRB oversight and annotation collaboration.
- No minors in v1 collection. `practice_only` vs `consented_research` modes in-app;
  local preview + delete before upload; the research corpus's record schema is adopted
  with POPIA fields added (consent version, retention date, withdrawal status).

### 7.2 Collection strategy
The app is the instrument: every pilot site is a collection opportunity *only* under
consent mode. Alongside: recorded sessions with contracted interpreters (like UCT's
approach, but in real domains — medical/service vocabulary, natural backgrounds,
multiple angles where possible). Year-one target: **50–200 hours** with signer
diversity, dwarfing UCT's 5 studio hours in realism if not polish. ASL Citizen proved
crowdsourced isolated-sign collection works (~84k clips from volunteers) — replicate
that model for SASL isolated signs through Deaf organizations.

### 7.3 Pretraining corpora (transfer learning — verified vs. unverified)

General sign-language visual/temporal structure transfers across sign languages;
SASL-specific meaning does not. Pretrain the encoder on large foreign corpora, fine-tune
on ours. License check before every download.

| Dataset | Language | Scale | Status |
|---|---|---|---|
| BOBSL | BSL | ~1,400 h broadcast | Verified; research license (Oxford/BBC) — the big one for video pretraining |
| YouTube-ASL | ASL | ~1,000 h, 2,500+ signers | Verified; released as video IDs |
| How2Sign | ASL | ~80 h multimodal (RGB+pose+depth) | Verified; research use |
| WLASL | ASL isolated | 2,000 glosses | Verified; widely used for isolated-sign pretraining |
| MS-ASL | ASL isolated | 1,000 classes | Verified |
| ASL Citizen | ASL isolated | ~84k clips, 2,700 glosses | Verified; also the crowdsourcing playbook |
| RWTH-PHOENIX-2014T | DGS | 11 h, gold gloss+translation | Verified; the SLT benchmark standard |
| CSL-Daily | CSL | ~20 h daily-life domain | Verified |
| AUTSL | TSL isolated | 226 signs, 43 signers, RGB-D | Verified |
| AfriSign / African SL corpora | multiple | small | From research corpus; verify per-corpus |
| Hugging Face sign-language datasets | mixed | varies | Verify individually |
| ~~SignVerse-2M~~ | claimed 55+ languages, 2M clips | **Unverified — no confirmed source. Do not plan around it until a URL, paper, and license are in hand.** | |

### 7.4 Model plan (research track, honest about maturity)
1. **Representation:** pose-first (MediaPipe Holistic / RTMPose skeletons + face) —
   cheaper, more privacy-preserving, more signer-invariant than raw RGB; raw video kept
   for future video-encoder work (SSVP-SLT-style self-supervised pretraining showed
   video pretraining beats pose pipelines when data is large — revisit at scale).
2. **Stage 1 model:** isolated SASL sign recognition (our vocabulary), encoder
   pretrained on WLASL/ASL-Citizen/AUTSL pose sequences, fine-tuned on our isolated
   recordings. This also powers a sign-practice feature — product value from the first
   model.
3. **Stage 2:** continuous recognition on our conversational corpus; unseen-signer test
   split non-negotiable; unknown-sign rejection required; left-handedness, lighting,
   angle in the eval matrix.
4. **Stage 3:** SASL→English translation (gloss-free direction per current literature),
   only when data justifies it.
5. **Frontier cloud models** assist annotation (draft segmentation/gloss suggestions,
   human-approved only), build training tooling, and act as eval judges — never as
   the recognizer and never as unreviewed ground truth.
6. Camera features re-enter the product only when: dataset card complete, unseen-signer
   accuracy published, unknown-rejection works, Deaf reviewers sign off, and a
   confidence-gated UX ("I didn't catch that — please repeat") is in place.

---

## 8. Partnerships & Sustainability

- **Community:** DeafSA, SLED (Sign Language Education and Development), National
  Institute for the Deaf — consultant sourcing, pilot sites, collection partners,
  legitimacy. Nothing about the Deaf community without the Deaf community.
- **Academic:** UCT (SASL SLT lineage) / Wits — ethics, annotation, co-publication.
  Offer co-authorship on the dataset paper; a published SASL corpus with a datasheet is
  both a contribution and a credibility engine.
- **Funding path:** SA innovation/disability grants (TIA seed, SAB Foundation social
  innovation), then government service procurement once the pilot proves the counter
  use case. The 2023 official-language status creates the procurement argument.
- **Positioning sentence:** "AMANDLA is the counter-top communication bridge for
  SASL — reliable today with deterministic translation and a reviewed avatar, and the
  only platform building the consented SASL dataset that real translation will need."

---

## 9. What We Will Not Do (binding)

- No LLM as the unvalidated last word in any user-facing path.
- No camera-recognition claims before Section 7.6 gates. No demo-ware toggles back in.
- No language support claims without a passing fixture file.
- No new planning documents. Decisions amend THIS file with a dated changelog line.
- No multi-agent frameworks, GraphRAG, vector memory, or architecture astronautics
  before the fixture suite is green.
- No collection of real signing data before POPIA/ethics gates.
- No second long-lived branch. No parallel realities.

---

## 10. Changelog

- 2026-07-05 — v1.0 of this plan. Consolidates the codex research corpus (29 docs),
  today's keyframe-pipeline merge (PR #2), the defect-register validation (3 of 4 code
  defects already fixed; `routes.py:83` survivor scheduled in Phase 0), and the product
  rescope. All decisions in Section 2 are in force.
- 2026-07-05 — Phase 0 executed (PR #5): rules-first pipeline + order tests (D4),
  generic route errors, subprotocol WS auth + query-token rejection (D9), CORS removal
  + X-Amandla-Token gate on mutating HTTP (D10), repo cleanup (D12), static-pattern and
  npm-audit CI gates. Branch consolidation (D11): `dev` and
  `codex/modernization-research` deleted; fully preserved as tags `rescue/dev-2026-07`
  and `research-2026-07`. **D11 execution note:** `dev` was found to contain real
  features absent from `main` — interpreter role window, offline phrase library
  (`backend/data/offline_phrases.json` + pipeline step), multi-user hearing role,
  expanded `sign_maps.py` phrase maps, vendored TalkingHead/MediaPipe assets,
  `scripts/generate_modelfile.py` — mixed with noise (unrelated AMD dossier, duplicated
  `.aiassistant` blobs, 5MB wasm). These are mined feature-by-feature from the tag with
  tests during Phases 1–2, not merged wholesale. Mining checklist lives here until
  each item ships or is explicitly rejected.
- 2026-07-05 — Phase 1 golden harness landed: 24 translation fixtures + 6
  reconstruction fixtures, word-order-aware scorer (`tests/golden/scoring.py`), CI
  gate (criticals must pass 100%). First run caught and fixed four real grammar bugs
  ('need'→'NE' stemming, false FINISH from -s/-ing forms, 'walking'→'WALKE',
  RIGHTS→RIGHT library-sign mangling) and one vocabulary hole (NEED absent from the
  avatar — added as a review-flagged placeholder, conf 2). **Phase 3 vocabulary
  debt (measured):** 16 transformer signs the avatar cannot play — BOOK, BUY, FEEL,
  HE, LEARN, LIKE, LIVE, MAKE, MILK, MY, NAME, PHONE, SOUTH AFRICA, TEACH, THINK,
  YOUR. Record real signer data for these (plus CALL, HERE) before expanding further.
