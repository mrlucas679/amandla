# AMANDLA Modernization Research Completion Audit

Status: audit complete for current research loop; production implementation not complete
Date: 2026-07-05
Branch: `codex/modernization-research`

## Bottom Line

The research phase is substantially complete, but the overall modernization goal is not fully proven complete because no runtime evaluator has been implemented and no local model has been benchmarked. The blocking facts are current and concrete:

- Python is not available in the shell.
- Ollama is installed and serving, but no models are pulled.
- No app code has been changed or tested in this research branch.

The project now has enough research to make a responsible Phase 1 implementation plan. It does not yet have evidence that any specific model works well inside AMANDLA.

## Objective Requirements Audit

| Requirement From User Objective | Evidence Created | Status |
|---|---|---|
| Convert old hackathon AI research to AMANDLA, not AMD ACT II | `ai-paper-refresh-2026.md`, `current-ai-and-sign-research-addendum-2026.md` | Met for research. |
| Exclude GPUs for now | All model docs route large/GPU-heavy models to hosted/later research; local path is CPU/RAM-first. | Met. |
| Rethink every model choice | `ai-model-strategy-2026.md`, `model-decision-matrix-2026.md`, `ollama-restore-and-model-eval.md` | Met as strategy; unproven until eval. |
| Use new papers and current research | Added 2025/2026 sign-language, model, ASR, and provider sources. | Met for current research pass. |
| Research big model releases and open-source models | OpenAI GPT-5.5, GPT-OSS, Qwen3.5, Qwen3, Qwen3-VL, Qwen3.6, Gemma, Llama 4, Mistral, DeepSeek, Groq reviewed. | Met for shortlist. |
| Decide best model for the application | Revised decision: do not center the product on a small local LLM. Use powerful cloud foundation models for development/research and build an AMANDLA-owned specialized multimodal SASL model for production. | Met as strategy; specialized model remains future work. |
| Decide cloud path if local is not best | `cloud-local-deployment-options-2026.md` defines `LOCAL_ONLY`, `QUALITY_CLOUD`, and `RESEARCH_EVAL`. | Met as architecture plan. |
| Understand the application's abilities | `application-abilities-and-model-requirements.md` maps typed text, speech, signs, avatar, rights, history, emergency, and camera recognition. | Met. |
| Understand existing documents | `document-inventory.md` classifies active docs, stale docs, archived docs, research PDFs, and dirty-checkout references. | Met at inventory level; deep PDF extraction remains future work for some sources. |
| Create a loop until the desirable result is good for AMANDLA | `research.md`, `research-log.md`, `autoresearch-results.tsv`, and `progress.png` record nine research/packaging iterations. | Met for initial research loop; implementation loop remains future work. |
| Avoid disturbing Claude | Work was done only in `C:\Users\Admin\amandla-desktop-codex-research` on `codex/modernization-research`. | Met. |

## Current Best Model Decision

| Role | Best Current Recommendation | Why |
|---|---|---|
| Development/research reasoning | OpenAI `gpt-5.5` or equivalent frontier cloud foundation model | Use for engineering, annotation assistance, design, and eval support. |
| Local small LLMs | `qwen3.5:4b`, `qwen3:4b`, or similar | Benchmark/fallback only; not trusted product core. |
| Future production SASL model | AMANDLA-owned specialized multimodal model | Train only after consented SASL dataset, annotation, and review gates exist. |
| Cloud text quality | OpenAI `gpt-5.5` with Structured Outputs | Best current structured text/eval baseline from official OpenAI docs. |
| Cloud/local speech comparison | OpenAI speech, Google Chirp 3, Azure Speech / MAI Transcribe | Must be measured on South African language/accent fixtures. |
| Camera sign recognition | No generic LLM/VLM default | Needs consented SASL temporal data, dataset card, and community review. |

## What Is Still Not Done

These are not failures; they are honest boundaries.

1. Python must be installed or repaired before backend tests and fixture runners can execute.
2. The strategy now prioritizes cloud-assisted research and dataset building over pulling small local models.
3. The JSON fixture files have been specified but not implemented under `tests/golden/`.
4. The static forbidden-pattern checker has been designed but not implemented.
5. WebSocket contract tests have been planned but not implemented.
6. No model has been benchmarked on AMANDLA fixtures yet.
7. No Deaf/SASL community review has happened.
8. Several local PDF sources are inventoried but not all fully extracted into structured notes.

## Next Approved Work Package

The next concrete work package should be Phase 1 implementation, after user approval:

1. Repair Python.
2. Create the fixture files from `model-evaluation-fixtures-spec.md`.
3. Add static forbidden-pattern checks.
4. Add dataset consent and annotation schemas.
5. Score deterministic rules first.
6. Use cloud models only with synthetic or consented fixtures.
7. Keep local small LLM tests as optional fallback benchmarks, not core strategy.
8. Use `objective-traceability-matrix.md` to verify each implementation PR advances the original objective.

## Completion Decision

Research deliverables are complete enough to guide implementation. The full modernization objective is not complete until the app has a working evaluator, runtime fixes, and measured model results.
