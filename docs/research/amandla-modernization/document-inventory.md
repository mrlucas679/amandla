# AMANDLA Document Inventory

Date: 2026-07-05
Scope: clean `codex/modernization-research` worktree plus notable documents seen in Claude's dirty checkout.

This file does not delete anything. It classifies documents so the project can remove noise deliberately after approval.

## Decision Legend

- **Keep authoritative** - current instruction or source of truth.
- **Keep reference** - useful source material, not controlling instructions.
- **Reconcile** - useful but likely stale or overlapping; must be merged into newer docs or retired.
- **Archive/delete candidate** - not useful in active repo once confirmed.
- **Review later** - binary/large research material not fully extracted in this pass.

## Active Project Documents

| Path | Decision | Reason |
|---|---|---|
| `CLAUDE.md` | Keep authoritative | Explicitly states it overrides other docs. Needs reconciliation with current code and Claude WIP, but remains top rule file. |
| `AGENTS.md` | Keep authoritative for agent behavior | Detailed coding rules and skills. Some protocol details may be stale, but process rules remain important. |
| `README.md` | Reconcile | Useful public overview, but it claims zero direct renderer fetch while `signs_library.js` fetches backend data directly. |
| `QUICKSTART.md` | Reconcile | Useful onboarding, but includes duplicate sections and references stale files such as `SETUP_COMPLETE.md`. |
| `PROJECT_PLAN.md` | Reconcile | Useful history and planning, but must be checked against current code and Claude's uncommitted work. |
| `PRODUCTION_READINESS.md` | Reconcile | Useful audit artifact, but should become a dated reference or be folded into a new readiness tracker. |
| `INVESTIGATION_AND_PLAN.md` | Reconcile | Valuable failure analysis, but likely overlaps with newer research and plans. |
| `AMANDLA_FINAL_BLUEPRINT.md` | Keep reference | Avatar/Three.js spec material. Not authoritative until checked against actual `avatar.js`. |
| `AMANDLA_MISSING_PIECES.md` | Keep reference | Backend integration blueprint. Must not be followed blindly because some items are already implemented or stale. |
| `SASL_Transformer_README.md` | Keep reference | Relevant documentation for the transformer module. Should be updated after protocol/backend cleanup. |
| `docs/WEBSOCKET_PROTOCOL.md` | Reconcile urgently | Stale auth docs mention `?token=...` while current code uses WebSocket subprotocol. Tests also follow stale docs. |
| `requirements.txt` | Keep authoritative dependency input | Must be refreshed after Python/runtime research. |
| `amandla_sasl_transformer2/README2.md` | Archive/delete candidate | Duplicate archived transformer tree exists alongside active `sasl_transformer/`. |
| `amandla_sasl_transformer2/ARCHIVED.md` | Archive/delete candidate | Confirms the folder is archived. Candidate for deletion after verifying no imports. |
| `amandla_sasl_transformer2/requirements.txt` | Archive/delete candidate | Belongs to archived duplicate. |

## Local Research Material

| Path | Decision | Reason |
|---|---|---|
| `docs/research/amandla-modernization/application-abilities-and-model-requirements.md` | Keep reference | Maps current AMANDLA abilities to model requirements, proof gates, and runtime evidence. |
| `docs/research/amandla-modernization/ai-model-strategy-2026.md` | Keep reference | Current model-routing and cloud/local strategy for AMANDLA. |
| `docs/research/amandla-modernization/ai-paper-refresh-2026.md` | Keep reference | Adapts the old AMD ACT II dossier and newer sign-language/model research to AMANDLA. |
| `docs/research/amandla-modernization/completion-audit-2026-07-05.md` | Keep reference | Audits the user objective against current evidence and names remaining unproven work. |
| `docs/research/amandla-modernization/cloud-local-deployment-options-2026.md` | Keep reference | Defines local-only, cloud quality, and research-eval deployment paths. |
| `docs/research/amandla-modernization/current-ai-and-sign-research-addendum-2026.md` | Keep reference | Updates the local model recommendation to `qwen3.5:4b` and adds newer 2026 sign-language research. |
| `docs/research/amandla-modernization/dataset-first-sasl-foundation-strategy.md` | Keep reference | Strategic pivot away from small local LLM core toward cloud-assisted dataset building and AMANDLA-owned SASL model. |
| `docs/research/amandla-modernization/final_report.md` | Keep reference | Summarizes the initial research loop outcome and clearly separates research completion from implementation proof. |
| `docs/research/amandla-modernization/first-model-benchmark-runbook.md` | Keep reference | Defines the first safe local model benchmark sequence once Python is restored. |
| `docs/research/amandla-modernization/model-evaluation-fixtures-spec.md` | Keep reference | Defines JSON fixture contracts, pass/fail metrics, and privacy labels for model evaluation. |
| `docs/research/amandla-modernization/model-decision-matrix-2026.md` | Keep reference | Ranks local and cloud model candidates by AMANDLA task role. |
| `docs/research/amandla-modernization/objective-traceability-matrix.md` | Keep reference | Maps the original user objective to evidence artifacts, proof status, and remaining gates. |
| `docs/research/amandla-modernization/phase-1-implementation-approval-plan.md` | Keep reference | Approval-ready implementation plan with exact files, functions, tests, and stop conditions for Phase 1. |
| `docs/research/amandla-modernization/README.md` | Keep reference | Start-here index for the modernization research package. |
| `docs/research/amandla-modernization/sasl-dataset-collection-governance-plan.md` | Keep reference | Consent, annotation, privacy, split, and review plan for building AMANDLA's own SASL dataset. |
| `SASL DOCUMEENTS/AMANDLA_Research_Synthesis.md` | Keep reference | Highly relevant SASL/avatar synthesis. Should be cleaned up and moved under `docs/research/sasl/`. |
| `SASL DOCUMEENTS/AMANDLA_Master_Implementation_Prompt.md` | Keep reference, then retire | Useful to understand previous Claude work, but it is a prompt, not current architecture. |
| `SASL DOCUMEENTS/SignON_D5.2_A-Virtual-Character_v1.0.pdf` | Keep reference | Relevant avatar/NMF/blendshape research. |
| `SASL DOCUMEENTS/South_African_sign_language_machine_translation_pr.pdf` | Keep reference | Directly relevant SASL MT material. |
| `SASL DOCUMEENTS/devilliers_visionbased_2014.pdf` | Keep reference | Relevant SASL recognition/background research. |
| `SASL DOCUMEENTS/Einsteinhands dictionary Inside pages_lowres.pdf` | Keep reference | Sign dictionary source material. |
| `SASL DOCUMEENTS/2020.signlang-1.16.pdf` | Keep reference | Relevant sign-language translation/avatar research. |
| `SASL DOCUMEENTS/37948-985-31042-1-10-20251030.pdf` | Review later | Needs title/metadata extraction before decision. |
| `SASL DOCUMEENTS/draftcwaxrlpa_publiccommenting.pdf` | Review later | Likely legal/disability-rights source; needs extraction. |
| `SASL DOCUMEENTS/Ghaziasgar_MSC_2010.pdf` | Keep one copy | Relevant thesis/source material if used. |
| `SASL DOCUMEENTS/Ghaziasgar_MSC_2010 (1).pdf` | Archive/delete candidate | Duplicate by name and size; verify hash before deletion. |

## Archived Documents

All files below start with `# ARCHIVED - DO NOT USE` or are listed by `CLAUDE.md` as stale. They should not guide implementation.

| Path | Decision | Reason |
|---|---|---|
| `archive/AGENT_PROMPTS.md` | Archive/delete candidate | Explicit stale prompts with wrong fixes. |
| `archive/AGENT_TASKS.md` | Archive/delete candidate | Explicitly stale status. |
| `archive/AMANDLA_BLUEPRINT (2).md` | Archive/delete candidate | Superseded hackathon blueprint. |
| `archive/APPLICATION_STARTED.md` | Archive/delete candidate | Historical snapshot. |
| `archive/FINAL_STATUS_REPORT.md` | Archive/delete candidate | Historical snapshot. |
| `archive/NEXT_STEPS.md` | Archive/delete candidate | Outdated roadmap. |
| `archive/OPERATIONAL_STATUS.md` | Archive/delete candidate | Historical snapshot. |
| `archive/PROJECT_SETUP_SUMMARY.md` | Archive/delete candidate | Duplicate setup history. |
| `archive/SETUP_COMPLETE.md` | Archive/delete candidate | Stale setup doc referenced by old quickstart. |
| `archive/SETUP_VERIFICATION.md` | Archive/delete candidate | Stale verification doc. |
| `archive/START_HERE.md` | Archive/delete candidate | Stale entry point. |
| `archive/WHAT_WAS_COMPLETED.md` | Archive/delete candidate | Historical status, not active truth. |

## Skill And Agent Rule Documents

| Path | Decision | Reason |
|---|---|---|
| `.aiassistant/rules/ai rules.md` | Keep reference | Agent behavior rules. |
| `.aiassistant/rules/skills/*.md` | Keep reference | Local skill library. Consider moving out of product repo if it is tool-specific noise. |

## Dirty Checkout Documents Not Present In Clean Branch

These were observed in `C:\Users\Admin\amandla-desktop`, not edited here.

| Path | Decision | Reason |
|---|---|---|
| `AMD-ACTII-AI-Research-Papers-Dossier.md` | Keep reference outside product docs | Useful AI-system lessons only. It is from a different project and should not become AMANDLA authority. |
| `amandla-rebuild-plan.md` | Reconcile | Contains valuable audit claims, but should be merged into this research set after verifying against code. |
| `BIOMECHANICS_IMPL.md` | Reconcile | Useful avatar implementation notes, likely from Claude WIP. Must be checked against actual code before adoption. |
| `Screen Recording 2026-04-10 132737.mp4` | Review later | Could be useful UX evidence; not a doc. |

## Non-Document Noise Seen During Inventory

These are not documents, but they are likely cleanup candidates in a modernization effort.

| Path | Decision | Reason |
|---|---|---|
| `data/conversations.db`, `data/conversations.db-shm`, `data/conversations.db-wal` | Review/delete from repo after approval | Runtime-generated SQLite data should normally not be source-controlled. |
| `ASL-Sensor-Dataglove-Dataset/` | Review later | Large ASL glove dataset may not support SASL product goals and increases repo noise. |
| `backend/harps_model/model.pth` | Review later | Model provenance/eval unclear. Keep only if tied to documented evaluation. |
| `assets/js/three.min.js`, `assets/js/GLTFLoader.js` | Reconcile | Vendored JS may be replaced by package-managed Three in React/Vite rebuild, but packaging/offline benefits matter. |

## Proposed Cleanup Policy

1. Keep `CLAUDE.md` and `AGENTS.md` as rule files until replaced by a single current contributor guide.
2. Move active research under `docs/research/`.
3. Move dated planning under `docs/archive/` or delete after approval.
4. Delete archived duplicates only after a search proves no code imports or links require them.
5. Remove generated runtime data from Git and add ignore rules after confirming the user does not need the current database.
6. Replace stale quickstart references before deleting old setup docs.
