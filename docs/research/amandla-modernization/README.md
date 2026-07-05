# AMANDLA Modernization Research Index

Status: start-here index
Date: 2026-07-05
Branch: `codex/modernization-research`

## Start Here

Read these first:

1. `final_report.md` - high-level research verdict and best current recommendations.
2. `completion-audit-2026-07-05.md` - what is proven, what is not proven, and why.
3. `objective-traceability-matrix.md` - original user objective mapped to evidence, decisions, and remaining gates.
4. `phase-1-implementation-approval-plan.md` - exact next code/test plan that still needs explicit approval.

## Current Best Answer

AMANDLA should be:

- Local-first.
- Rule-first for SASL correctness.
- Cloud-optional only by explicit mode.
- Evaluation-driven before trusting any model.
- Honest that camera sign recognition is research-only until there is consented SASL data and Deaf/SASL review.

Current model route:

| Role | Recommendation |
|---|---|
| Deterministic SASL correctness | `backend/services/sign_maps.py` and SASL transformer rules |
| Development/research reasoning | Powerful cloud foundation model, first baseline OpenAI `gpt-5.5` |
| Dataset annotation assistance | Cloud multimodal model plus Deaf/SASL human review |
| Local small LLMs | Benchmark/fallback only; not the product brain |
| Future production model | AMANDLA-owned specialized multimodal SASL model |
| Cloud text/eval baseline | OpenAI `gpt-5.5` with Structured Outputs |
| Speech comparison | OpenAI speech, Google Chirp 3, Azure Speech / MAI Transcribe |
| Camera sign recognition | No production model yet |

## Document Map

### Research State

| File | Use |
|---|---|
| `research.md` | Living autoresearch state and history table. |
| `research-log.md` | Detailed iteration log. |
| `autoresearch-results.tsv` | Machine-readable iteration log. |
| `progress.png` | Visual progress chart. |
| `final_report.md` | Best current result and remaining proof work. |
| `completion-audit-2026-07-05.md` | Requirement-level completion audit. |
| `objective-traceability-matrix.md` | Original objective to artifact/proof mapping. |

### Model And AI Strategy

| File | Use |
|---|---|
| `ai-paper-refresh-2026.md` | Adapts the old AMD ACT II AI dossier to AMANDLA. |
| `current-ai-and-sign-research-addendum-2026.md` | Latest model and sign-language research update. |
| `dataset-first-sasl-foundation-strategy.md` | Strategic pivot away from small local LLM core toward cloud-assisted dataset building and AMANDLA-owned SASL model. |
| `sasl-dataset-collection-governance-plan.md` | Consent, annotation, storage, review, split, and model-training plan for AMANDLA's SASL dataset. |
| `ai-model-strategy-2026.md` | Task-specific model roles and routing principles. |
| `model-decision-matrix-2026.md` | Local/cloud candidate scorecard. |
| `cloud-local-deployment-options-2026.md` | `LOCAL_ONLY`, `QUALITY_CLOUD`, and `RESEARCH_EVAL` deployment modes. |
| `ollama-restore-and-model-eval.md` | How to recover Ollama and evaluate local models. |

### Application Understanding

| File | Use |
|---|---|
| `application-abilities-and-model-requirements.md` | Maps app abilities to models and proof gates. |
| `defect-register.md` | Evidence-backed defects and risk register. |
| `verification-matrix.md` | Verification gates for defects and modernization work. |
| `document-inventory.md` | Keep/archive/delete/reconcile inventory. |

### Evaluation And Implementation Planning

| File | Use |
|---|---|
| `evaluation-harness-plan.md` | Test layers and evaluation strategy. |
| `model-evaluation-fixtures-spec.md` | Exact JSON fixture contracts and scoring rules. |
| `first-model-benchmark-runbook.md` | First safe local benchmark sequence. |
| `phase-1-rescue-plan.md` | Broad Phase 1 rescue roadmap. |
| `phase-1-implementation-approval-plan.md` | Approval-ready file/function/test plan. |
| `cleanup-deletion-proposal.md` | Deletion/move proposal, not yet executed. |

### Frontend And Product Direction

| File | Use |
|---|---|
| `frontend-architecture-adr.md` | Frontend architecture recommendation. |
| `react-migration-plan.md` | React/TypeScript/Vite migration plan. |
| `product-design-brief.md` | Product design brief for hearing/deaf/rights workflows. |
| `modernization-roadmap.md` | Phased modernization roadmap. |

## What Not To Do Yet

- Do not build the product around a small local LLM.
- Do not pull many models before fixture evaluation exists.
- Do not wire cloud providers directly into renderers.
- Do not claim all South African languages are supported until speech and translation fixtures pass.
- Do not claim camera sign recognition is production-ready.
- Do not delete archived files or generated data without approval.
- Do not touch Claude's checkout.

## Next Decision

The next decision is not a research question. It is an approval question:

Which Phase 1 implementation scope should start?

| Scope | Meaning |
|---|---|
| Minimal | Fix assist crash, auth docs/tests, and generic errors. |
| Evaluation-first | Add static gate, fixture skeleton, and deterministic evaluator before app fixes. |
| Full Phase 1 | Execute the full approval plan A-I in the research worktree. |
