# AMANDLA Modernization Research Log

Date: 2026-07-05
Branch/worktree: `codex/modernization-research`

## Iteration 0 - Baseline Evidence

### Local State

- Research worktree: `C:\Users\Admin\amandla-desktop-codex-research`
- Original Claude checkout: `C:\Users\Admin\amandla-desktop`
- Clean research branch status before docs: no tracked changes.
- Claude checkout status: dirty with many modified and untracked files. Treated as external evidence, not edited.

### Commands Run

| Command | Result |
|---|---|
| `git status --short --branch` | Research branch clean before docs. Original checkout dirty on `dev...origin/dev [ahead 1]`. |
| `rg --files` | Found active app files, archive docs, duplicate transformer folder, ASL dataset, local SASL research files, generated SQLite DB files. |
| `rg -n "fetch\\(|token=|session-secret|str\\(e\\)|load_dotenv|innerHTML"` | Found protocol drift, direct renderer fetches, raw `str(e)`, manual connect calls, and stale docs/tests. |
| `npm view react version` | `19.2.7` |
| `npm view vite version` | `8.1.3` |
| `npm view electron version` | `43.0.0` |
| `npm view electron-builder version` | `26.15.3` |
| `npm view three version` | `0.185.1` |
| `npm audit --audit-level=moderate --json` | 22 vulnerabilities: 1 low, 5 moderate, 15 high, 1 critical. |
| `npm audit --omit=dev --audit-level=moderate --json` | 1 production vulnerability: `js-yaml` moderate. |
| `Get-Command python,python3,py` | Only Windows Store Python aliases found; no real Python executable in shell path. |

### Key Local Evidence

- `backend/ws/handler.py:136` uses undefined `session_id` in the assist-phrase dispatch path.
- `src/preload/preload.js:92` authenticates WebSocket using `Sec-WebSocket-Protocol`.
- `docs/WEBSOCKET_PROTOCOL.md:13` and `tests/test_e2e_pipeline.py:122` still use `?token=`.
- `signs_library.js:1544` and `1545` directly fetch backend SASL map data.
- `sasl_transformer/routes.py:83` returns `detail=str(e)`.
- `src/windows/hearing/hearing.js:71`, `src/windows/deaf/deaf.js:81`, and `src/windows/rights/rights.js:17` manually connect without passing the secret.
- `Modelfile:1` still uses `FROM qwen2.5:3b`.

### External Sources Consulted

- Electron security checklist: https://www.electronjs.org/docs/latest/tutorial/security
- Electron Forge Vite template: https://www.electronforge.io/templates/vite
- Vite guide: https://vite.dev/guide/
- React 19 release notes: https://react.dev/blog/2024/12/05/react-19
- Ollama Windows install: https://docs.ollama.com/windows
- Ollama qwen3 library: https://ollama.com/library/qwen3
- Google MediaPipe Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- SignON D5.2 virtual character deliverable: https://signon-project.eu/wp-content/uploads/2023/12/SignON_D5.2_A-Virtual-Character_v1.0.pdf
- WCAG 2.2 contrast guidance: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- NIST AI Risk Management Framework: https://www.nist.gov/itl/ai-risk-management-framework

### Decision

Keep the research direction:

- Do not polish the current UI as the final frontend.
- Recommend React 19 + TypeScript + Vite inside Electron.
- Restore Ollama/Python before runtime claims.
- Stabilize protocol/security bugs before large UI migration.
- Keep FastAPI initially; add typed protocol/evaluation around it.
- Do not delete cleanup candidates until the user approves a deletion proposal.

### Next Research Iteration

Create a concrete cleanup/deletion proposal and a Phase 1 implementation plan that can be reviewed before any code fixes begin.

## Iteration 1 - Cleanup, Rescue, And Design Brief

### Hypothesis

Converting the baseline audit into explicit deletion, rescue, and design-brief artifacts should improve the project because the rebuild needs a smaller, more trustworthy surface before code changes begin.

### Evidence Gathered

- `archive/` contains 12 tracked stale documents.
- `amandla_sasl_transformer2/ARCHIVED.md` states that the entire duplicate transformer directory can be deleted.
- `SASL DOCUMEENTS/Ghaziasgar_MSC_2010.pdf` and `SASL DOCUMEENTS/Ghaziasgar_MSC_2010 (1).pdf` have the same SHA-256 hash.
- `ASL-Sensor-Dataglove-Dataset/` contains 1000 tracked CSV files and is about 281.55 MB.
- `data/conversations.db`, `data/conversations.db-shm`, and `data/conversations.db-wal` are tracked even though conversation history is runtime-generated.
- Official current docs support the proposed React/TypeScript/Vite/Electron direction:
  - React 19: https://react.dev/blog/2024/12/05/react-19
  - Electron Forge Vite + TypeScript: https://www.electronforge.io/templates/vite-%2B-typescript
  - Vite guide: https://vite.dev/guide/
  - Electron security: https://www.electronjs.org/docs/latest/tutorial/security
  - Ollama Windows install: https://docs.ollama.com/windows
  - MediaPipe Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
  - WCAG 2.2: https://www.w3.org/TR/WCAG22/

### Artifacts Added

- `cleanup-deletion-proposal.md`
- `phase-1-rescue-plan.md`
- `product-design-brief.md`
- `autoresearch-results.tsv`

### Decision

Kept. The new documents move the work closer to execution while preserving the no-code-change boundary.

### Next Research Iteration

Build a detailed React migration plan and a verification matrix that maps every known defect to a test or manual proof.

## Iteration 2 - React Migration, Verification, And Evaluation Harness

### Hypothesis

A React migration is only useful if paired with proof gates and an evaluation harness before implementation.

### Evidence Gathered

- Current `package.json` still has no React, Vite, TypeScript, Vitest, Playwright, or component-test stack.
- Latest checked ecosystem versions make a React 19 + TypeScript + Vite migration viable.
- Official docs support Electron Forge Vite builds, Electron security constraints, Vitest Browser Mode, Playwright Electron automation, and WCAG 2.2 accessibility gates.
- Repository pattern checks still show unresolved risks: direct renderer backend fetches, manual renderer connects, WebSocket auth drift, raw `str(e)`, and the assist-phrase `session_id` issue.
- Product Design rules require a confirmed brief and visual target before UI implementation.
- The Product Design saved-context preflight could not run because Python is unavailable; no saved context file was present.

### Artifacts Added

- `react-migration-plan.md`
- `verification-matrix.md`
- `evaluation-harness-plan.md`

### Decision

Kept. The migration recommendation is useful only when it is gated by Phase 1 rescue work and measurable checks.

### Next Research Iteration

Use the verification matrix to draft the first code-change implementation plan for Phase 1 rescue, but do not implement it until the user approves.

## Iteration 3 - AI Paper Refresh And Model Strategy

### Hypothesis

AMANDLA needs a task-specific 2026 AI model strategy, not one universal Ollama model inherited from the old hackathon approach.

### Evidence Gathered

- The user-supplied AMD ACT II dossier is useful for AI-system habits such as validation, fallback, evaluation, and observability, but it belongs to a different retail/GPU/multi-agent project.
- `backend/services/sasl_pipeline.py` and `backend/services/sign_reconstruction.py` show that AMANDLA already has deterministic rule fallbacks that should remain the correctness base.
- `backend/services/claude_service.py` is actually an Ollama-backed rights service with templates, not active Claude cloud integration.
- `backend/services/ollama_service.py` prompts a generic text model over hand-landmark features, which is not a credible production sign-recognition approach.
- `backend/harps_model/meta.json` lists generic labels `SIGN_00` through `SIGN_20` with perfect metrics, so the checkpoint cannot be treated as production SASL evidence.
- Current OpenAI docs support `gpt-5.5`, Responses API, Structured Outputs, and separate speech/realtime models as cloud quality baselines.
- Current sign-language research emphasizes dataset quality, signer bias, annotation quality, temporal recognition, and the limits of zero-shot/general LLM or VLM recognition.

### External Sources Consulted

- OpenAI latest model guide: https://developers.openai.com/api/docs/guides/latest-model.md
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Realtime API: https://developers.openai.com/api/docs/guides/realtime
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI GPT-OSS announcement: https://openai.com/index/introducing-gpt-oss/
- OpenAI data residency update: https://openai.com/index/expanding-data-residency-access-to-business-customers-worldwide/
- Qwen3 announcement: https://qwenlm.github.io/blog/qwen3/
- Google Gemma docs: https://ai.google.dev/gemma/docs/core
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition in the Age of LLMs: https://arxiv.org/html/2604.11225v1
- SignAlignLM: https://aclanthology.org/2025.findings-acl.190.pdf
- AfriSign: https://link.springer.com/article/10.1007/s44163-025-00227-7

### Artifacts Added Or Updated

- Added `ai-model-strategy-2026.md`
- Added `ai-paper-refresh-2026.md`
- Updated `ollama-restore-and-model-eval.md`
- Updated `evaluation-harness-plan.md`

### Decision

Kept. AMANDLA should be local-first, cloud-optional, rule-first for SASL correctness, dataset-first for camera recognition, and schema-first for model outputs.

### Next Research Iteration

Draft the Phase 1 implementation plan that fixes protocol/security/runtime blockers and introduces evaluation gates, but do not implement app code until the user approves.

## Iteration 4 - Ability Map, Model Decision Matrix, And Cloud Options

### Hypothesis

Converting the 2026 model strategy into an application-ability map, a model decision matrix, and cloud/local deployment options should make the research actionable without touching production code.

### Evidence Gathered

- Current machine is an MSI Thin 15 B13UC with Intel i5-13420H, about 40 GB RAM, RTX 3050 Laptop GPU, and Intel UHD graphics.
- GPU work remains excluded by user instruction; the RTX 3050 Laptop GPU also has too little VRAM for serious local sign-language vision work.
- `ollama --version` returns `0.30.10`.
- `http://localhost:11434/api/tags` responds with an empty model list.
- `ollama list` has no entries.
- `python --version` still fails through the Windows Store shim, and `py` is unavailable.
- OpenAI docs position `gpt-5.5` as the current text/reasoning cloud baseline and recommend Responses API plus Structured Outputs.
- OpenAI speech docs list `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, `gpt-4o-transcribe-diarize`, and `gpt-realtime-whisper`, but supported language lists do not prove all South African official languages.
- Google Chirp 3 and Azure Speech provide important speech comparison paths because they publish feature/language support tables.
- Microsoft Build 2026 introduced additional MAI speech/model options in Foundry, useful as enterprise speech/cloud comparison candidates.
- Qwen3 and Ollama Qwen3 sources made `qwen3:4b` the best first local candidate at that point in the research. Iteration 6 later supersedes this with `qwen3.5:4b`.
- GPT-OSS 20B is plausible on 40 GB RAM, but likely too slow on CPU for live communication and should be a stretch experiment.
- New sign-language research and community feedback reinforce that camera sign recognition must be dataset/community-led, not a generic VLM/LLM claim.

### External Sources Consulted

- OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI Realtime guide: https://developers.openai.com/api/docs/guides/realtime
- OpenAI data residency guide: https://developers.openai.com/api/docs/guides/your-data#data-residency-controls
- OpenAI gpt-oss announcement: https://openai.com/index/introducing-gpt-oss/
- Ollama Qwen3: https://ollama.com/library/qwen3
- Ollama gpt-oss: https://ollama.com/library/gpt-oss
- Qwen3 announcement: https://qwenlm.github.io/blog/qwen3/
- Google Gemma 4 docs: https://ai.google.dev/gemma/docs/core
- Google Chirp 3 docs: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
- Azure Speech language support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- Microsoft Build 2026: https://blogs.microsoft.com/blog/2026/06/02/microsoft-build-2026-be-yourself-at-work/
- Meta Llama 4 announcement: https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- Mistral Small 4 announcement: https://mistral.ai/news/mistral-small-4/
- DeepSeek V3.2 release: https://api-docs.deepseek.com/news/news251201
- Groq OpenAI compatibility: https://console.groq.com/docs/openai
- Northeastern Deaf community survey article: https://news.northeastern.edu/2026/03/19/sign-language-technology-skepticism/

### Artifacts Added Or Updated

- Added `application-abilities-and-model-requirements.md`
- Added `model-decision-matrix-2026.md`
- Added `cloud-local-deployment-options-2026.md`
- Updated `defect-register.md`
- Updated `modernization-roadmap.md`
- Updated `ollama-restore-and-model-eval.md`
- Updated `evaluation-harness-plan.md`
- Updated `phase-1-rescue-plan.md`
- Updated `verification-matrix.md`

### Decision

Kept. At this point the best recommendation was `qwen3:4b` first for local text-model evaluation, deterministic rules for SASL correctness, no production camera recognition claim, and OpenAI `gpt-5.5` plus cloud speech providers as opt-in quality/evaluation baselines. Iteration 6 later supersedes the first local candidate with `qwen3.5:4b`.

### Next Research Iteration

Build the runnable evaluation design in more detail: exact fixture schemas, pass/fail scoring, and a no-code implementation plan for the first model benchmark run after Python is restored.

## Iteration 5 - Fixture Contracts And First Benchmark Runbook

### Hypothesis

The model strategy needs exact fixture schemas and a first-run benchmark sequence before any model pull, prompt rewrite, or cloud experiment is meaningful.

### Evidence Gathered

- The evaluation harness plan listed the right test layers but did not yet specify exact fixture contracts.
- The current first local model candidate should not be pulled or trusted until the benchmark has scoring rules.
- The app's core communication path needs deterministic scoring for required signs, forbidden signs, modal/aspect markers, unknown signs, and critical omissions.
- Speech support must be measured with language-tagged, consented or synthetic cases instead of inferred from provider language marketing.
- Rights outputs need structured sections, forbidden legal claims, and mandatory review disclaimers.
- Camera sign recognition still needs a dataset card before any production claim.

### Artifacts Added Or Updated

- Added `model-evaluation-fixtures-spec.md`
- Added `first-model-benchmark-runbook.md`
- Updated `evaluation-harness-plan.md`
- Updated `document-inventory.md`
- Updated `research.md`

### Decision

Kept. The next technical milestone should be runtime repair plus fixture implementation, not another model debate. Local rules should be scored first, then the current first local 4B-class candidate, then larger or cloud candidates only if the measurements justify them.

### Next Research Iteration

Review the existing backend and renderer code against the fixture/runbook requirements, then draft a user-approvable Phase 1 code-change plan for Python/runtime repair, WebSocket contract fixes, and the first static/fixture evaluator.

## Iteration 6 - Current Model Refresh And Completion Audit

### Hypothesis

A completion audit and a fresh current-model pass are required before claiming the research is done, because model recommendations can go stale quickly and the user's objective asks for current model/paper research.

### Evidence Gathered

- OpenAI official docs still position `gpt-5.5` as the current production text/reasoning baseline and recommend fresh baselines, Responses API, and Structured Outputs.
- Ollama now lists `qwen3.5:4b`, a 4.66B / 3.4 GB local model with text, vision, tools, thinking tags, efficient hybrid architecture, and expanded language coverage.
- Ollama lists `qwen3.6` in larger 27B/35B-class local variants focused on coding/agentic workflows; these are not a good first local live-communication path for AMANDLA.
- Ollama lists `qwen3-vl:4b`, but generic VLM capability is not enough to claim production SASL camera recognition.
- Additional 2026 sign-language papers reinforce that low-resource sign-language work depends on dataset documentation, consent, annotation quality, signer splits, preprocessing, and community review.
- The current AMANDLA runtime remains blocked for actual model evaluation because Python is unavailable and Ollama has no pulled models.

### External Sources Consulted

- OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model
- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Ollama Qwen3 4B: https://ollama.com/library/qwen3%3A4b
- Ollama Qwen3.6: https://ollama.com/library/qwen3.6
- Ollama Qwen3-VL 4B: https://ollama.com/library/qwen3-vl%3A4b
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition and Translation for Low-Resource Languages: https://arxiv.org/html/2605.12096v1
- SignDATA: https://arxiv.org/html/2604.20357v1
- Bootstrapping Sign Language Annotations: https://arxiv.org/html/2604.07606v1
- Gloss-Free Sign Language Translation: https://arxiv.org/html/2603.13240v1
- DHH access to intelligent personal assistants: https://arxiv.org/html/2601.15209v2

### Artifacts Added Or Updated

- Added `current-ai-and-sign-research-addendum-2026.md`
- Added `completion-audit-2026-07-05.md`
- Updated `model-decision-matrix-2026.md`
- Updated `first-model-benchmark-runbook.md`
- Updated `ollama-restore-and-model-eval.md`
- Updated `ai-model-strategy-2026.md`
- Updated `ai-paper-refresh-2026.md`
- Updated `cloud-local-deployment-options-2026.md`
- Updated `evaluation-harness-plan.md`
- Updated `modernization-roadmap.md`
- Updated `model-evaluation-fixtures-spec.md`
- Updated `document-inventory.md`
- Updated `research.md`

### Decision

Kept. The first local model recommendation is now `qwen3.5:4b`, with `qwen3:4b` as a conservative fallback baseline. OpenAI `gpt-5.5` remains the first cloud text/evaluation baseline. Camera sign recognition remains research-only until a consented SASL dataset and community review exist.

### Completion Audit Result

The research phase is complete enough to guide Phase 1 implementation. The full modernization goal is not proven complete because the project still needs Python repair, fixture implementation, model pulls, static checks, WebSocket tests, and real model benchmark results.

## Iteration 7 - Approval-Ready Phase 1 Implementation Boundary

### Hypothesis

The next useful step is not another broad research sweep, but an approval-ready code/test boundary that preserves the user's "plan first" rule and turns the research into a precise implementation scope.

### Evidence Gathered

- `backend/ws/handler.py` still has the assist phrase `session_id` / `sessionId` mismatch.
- `src/preload/preload.js` opens the WebSocket with `amandla-${currentSecret || ''}`, so an empty token remains possible if callers race the secret.
- `src/windows/hearing/hearing.js`, `src/windows/deaf/deaf.js`, and `src/windows/rights/rights.js` still manually call the preload connection path in addition to preload auto-connect behavior.
- `signs_library.js` still contains direct backend fetch usage, violating the preload-only boundary.
- `sasl_transformer/routes.py` still returns `detail=str(e)` for `ValueError`.
- Existing docs/tests still need WebSocket auth reconciliation around subprotocol auth versus `?token=`.
- Current source research still supports `qwen3.5:4b` first locally, with `qwen3:4b` as fallback and OpenAI `gpt-5.5` as cloud text/eval baseline.

### Artifacts Added Or Updated

- Added `phase-1-implementation-approval-plan.md`
- Updated `document-inventory.md`
- Updated `research.md`
- Updated `final_report.md`
- Updated `autoresearch-results.tsv`

### Decision

Kept. The approval-ready plan separates minimal, evaluation-first, and full Phase 1 scopes, and names exact files, functions, tests, acceptance gates, and stop conditions. Production code remains unchanged until the user approves an implementation scope.

### Next Step

Wait for explicit approval before changing production code. Recommended first implementation scope is the first PR shape from `phase-1-implementation-approval-plan.md`: static gate, fixture skeleton, assist phrase fix/test, WebSocket auth docs/tests reconciliation, and generic error fix.

## Iteration 8 - Research Package Index And Objective Traceability

### Hypothesis

The research package needs a start-here index and traceability map so the work is reviewable and directly tied to the user's original objective, not just a collection of disconnected markdown files.

### Evidence Gathered

- The folder contains many useful artifacts but no single `README.md` explaining reading order.
- `completion-audit-2026-07-05.md` proves the research state, but it is not optimized as a navigation document.
- The pasted AMD ACT II dossier's transferable themes are evidence contracts, validation, fallback, HITL, synthetic fixtures, and evaluation; the GPU/retail/multi-agent pieces remain excluded.
- The original objective contains multiple requirements: convert old research, exclude GPUs, rethink models, use current papers, choose local/cloud model routes, understand app abilities, understand docs, and keep iterating until the result is good for AMANDLA.

### Artifacts Added Or Updated

- Added `README.md`
- Added `objective-traceability-matrix.md`
- Updated `research.md`
- Updated `document-inventory.md`
- Updated `completion-audit-2026-07-05.md`
- Updated `final_report.md`
- Updated `research-log.md`
- Updated `autoresearch-results.tsv`

### Decision

Kept. The package now has a clear reading path and an objective-to-evidence map. This makes the next implementation phase auditable against the user's actual objective.

### Next Step

No production code should change until the user approves an implementation scope from `phase-1-implementation-approval-plan.md`.

## Iteration 9 - Dataset-First SASL Foundation Strategy

### Hypothesis

The research package should pivot away from a small-local-LLM-centered strategy because the user has correctly identified hallucination risk as unacceptable for critical real-time communication, and the attached UCT SASL thesis supports a dataset-first interpretation.

### Evidence Gathered

- The attached PDF is a UCT MSc thesis titled `Vision-Based Automatic Translation for South African Sign Language (SASL)`.
- The thesis reports a SASL/English dataset of 5047 sentence segments, about five hours of signing, collected in a studio domain focused on government and politics.
- The thesis reports a best SASL BLEU-4 result of 1.35 and concludes the results are still not practical for removing communication barriers.
- The thesis recommends more data, better annotation, and Deaf community collaboration.
- Current 2026 sign-language research also emphasizes dataset quality, low-resource constraints, continuous motion, non-manual features, signer splits, annotation quality, and community review.
- Small local LLM hallucinations would make critical app debugging and live communication unsafe.

### Artifacts Added Or Updated

- Added `dataset-first-sasl-foundation-strategy.md`
- Added `sasl-dataset-collection-governance-plan.md`
- Updated `README.md`
- Updated `final_report.md`
- Updated `completion-audit-2026-07-05.md`
- Updated `objective-traceability-matrix.md`
- Updated `model-decision-matrix-2026.md`
- Updated `phase-1-implementation-approval-plan.md`
- Updated `current-ai-and-sign-research-addendum-2026.md`
- Updated `first-model-benchmark-runbook.md`
- Updated `ai-model-strategy-2026.md`
- Updated `cloud-local-deployment-options-2026.md`
- Updated `model-evaluation-fixtures-spec.md`
- Updated `document-inventory.md`

### Decision

Kept. The strategic center is now AMANDLA's consent-based SASL dataset and future specialized multimodal SASL model. Cloud foundation models should be used for development, research, engineering, annotation assistance, and evaluation. Small local LLMs are downgraded to fallback/benchmark tools only.

### Next Step

The next implementation phase should add consent and dataset schema work alongside the existing protocol/evaluation rescue plan. No production code should change until the user approves the implementation scope.
