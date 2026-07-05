# AMANDLA Objective Traceability Matrix

Status: current traceability map
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

This matrix maps the user's original objective to the current research artifacts and proof status. It exists to prevent the work from feeling "done" just because many documents exist.

## Traceability

| Objective Requirement | Current Decision | Evidence Artifact | Proof Status | Remaining Gate |
|---|---|---|---|---|
| Convert old hackathon research to AMANDLA | Keep only transferable AI-system habits: contracts, validation, fallback, observability, fixtures, human review. Drop retail/GPU/multi-agent specifics. | `ai-paper-refresh-2026.md`, `final_report.md` | Researched and documented. | None for research; implementation still needs evaluators. |
| Exclude GPUs for now | Local path is CPU/RAM-first. GPU-heavy models are hosted/later research only. | `model-decision-matrix-2026.md`, `current-ai-and-sign-research-addendum-2026.md` | Met. | Revisit only if user re-enables GPU work. |
| Rethink every model choice | Split one `amandla` model into task roles: SASL helper, reconstruction helper, rights helper, speech provider, future sign recognition model. | `ai-model-strategy-2026.md`, `application-abilities-and-model-requirements.md` | Strategy complete. | Benchmark per role. |
| Use new papers | Added 2025/2026 sign-language, ASR, model, and cloud provider sources. | `current-ai-and-sign-research-addendum-2026.md`, `research.md` | Met for current pass. | Refresh again before implementation if delayed. |
| Research this year's big models | Compared OpenAI GPT-5.5, GPT-OSS, Qwen3.5, Qwen3, Qwen3-VL, Qwen3.6, Gemma, Llama 4, Mistral, DeepSeek, Groq. | `model-decision-matrix-2026.md`, `ai-paper-refresh-2026.md` | Met as shortlist. | Public claims remain secondary to AMANDLA fixture results. |
| Pick the best model strategy for AMANDLA | Do not center AMANDLA on a small local LLM. Use cloud foundation models for development/research/annotation and build a specialized AMANDLA SASL model for production. | `dataset-first-sasl-foundation-strategy.md`, `final_report.md` | Strategy updated. | Build dataset and evaluator evidence. |
| Decide if cloud is needed | Cloud is needed for development/research quality and annotation assistance. Production cloud use remains explicit and consented. | `dataset-first-sasl-foundation-strategy.md`, `cloud-local-deployment-options-2026.md` | Architecture complete. | Implement backend-only provider router later. |
| Understand application abilities | Mapped typed text, speech, multilingual input, manual signs, assist phrases, camera recognition, avatar production, rights help, history, emergency. | `application-abilities-and-model-requirements.md` | Met. | Validate against runtime after Python works. |
| Understand documents in hand | Classified active docs, stale docs, archived docs, local PDFs, dirty-checkout references, and cleanup candidates. | `document-inventory.md`, `cleanup-deletion-proposal.md` | Inventory complete enough. | Extract remaining local PDFs only if they become implementation inputs. |
| Create a loop until desirable result | Nine iterations logged; research now has model decision, fixture plan, benchmark runbook, approval-ready implementation boundary, and dataset-first SASL strategy. | `research.md`, `research-log.md`, `autoresearch-results.tsv`, `progress.png` | Initial research loop complete. | Implementation/evaluation loop still pending. |
| Avoid disturbing Claude | Work stayed in `C:\Users\Admin\amandla-desktop-codex-research` on `codex/modernization-research`. | `git status`, research docs | Met. | Continue using isolated worktree. |
| Make the app modern | Recommended React 19 + TypeScript + Vite inside Electron after Phase 1 backend/protocol rescue. | `frontend-architecture-adr.md`, `react-migration-plan.md`, `modernization-roadmap.md` | Planned, not implemented. | User approval and code changes. |
| Make the model path safe | Validate model JSON, sign names, critical omissions, latency, privacy mode, and cloud consent. | `model-evaluation-fixtures-spec.md`, `evaluation-harness-plan.md` | Designed, not implemented. | Create fixtures and evaluator. |
| Make sign recognition honest | Camera sign recognition remains research-only; no generic LLM/VLM production claim. | `current-ai-and-sign-research-addendum-2026.md`, `application-abilities-and-model-requirements.md` | Met as product stance. | Build consented SASL dataset and community review. |

## Current Readiness By Area

| Area | Current State | Ready For Code? |
|---|---|---|
| Research strategy | Strong enough to proceed. | Yes. |
| Runtime | Python missing; Ollama has no models. | No. |
| Local model choice | Small local models downgraded to fallback/benchmark role only. | Optional, after evaluator skeleton exists. |
| Cloud strategy | Opt-in backend-only modes defined. | Later. |
| Evaluation fixtures | Spec complete; fixture files not created. | Yes, with approval. |
| Protocol fixes | Bugs identified and scoped. | Yes, with approval. |
| React migration | Planned after Phase 1. | Not yet. |
| Camera recognition | Research-only. | No production claim. |

## Definition Of Done For The Next Phase

The next phase is done only when:

1. Python works.
2. Static safety gate runs.
3. Golden fixtures exist and validate.
4. Assist phrase WebSocket path has a regression test.
5. WebSocket auth docs/tests match subprotocol auth.
6. Dataset consent/annotation schemas exist.
7. Cloud foundation model use is constrained to synthetic or consented data.
8. The app still preserves Electron/FastAPI security invariants.
