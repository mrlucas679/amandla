# AMANDLA Modernization Research Loop Final Report

Status: initial research loop complete; implementation and benchmark proof still pending
Date: 2026-07-05
Branch: `codex/modernization-research`

## Best Current Result

AMANDLA should stay rule-first for live production communication while using powerful cloud foundation models for development, research, annotation, and engineering. The best current model route is:

1. Deterministic SASL rules remain the correctness base.
2. Small local LLMs are benchmark/fallback tools only, not the trusted product brain.
3. Development/research should use a powerful cloud foundation model, first baseline OpenAI `gpt-5.5`.
4. AMANDLA's long-term production engine should be its own specialized multimodal SASL model.
5. The core competitive advantage is the consent-based SASL dataset and review process.
6. Speech comparison remains OpenAI speech, Google Chirp 3, Azure Speech / MAI Transcribe.
7. Camera sign recognition has no production claim until real SASL data, temporal evaluation, and Deaf/SASL community review exist.

## What The Old Hackathon Research Contributed

The AMD ACT II dossier is not an AMANDLA architecture source, but it contributed durable AI-system habits:

- Use structured contracts.
- Validate outputs before use.
- Fall back safely.
- Log provider/model/latency.
- Evaluate with product-specific fixtures.
- Use synthetic data for tests, not fake production truth.
- Keep human review at sensitive boundaries.

The GPU/MI300X, retail multi-agent, inventory, and GraphRAG-first parts were not carried over.

## Artifacts Produced

Core research:

- `research.md`
- `research-log.md`
- `autoresearch-results.tsv`
- `progress.png`
- `completion-audit-2026-07-05.md`
- `README.md`
- `objective-traceability-matrix.md`

Model and AI strategy:

- `ai-paper-refresh-2026.md`
- `ai-model-strategy-2026.md`
- `current-ai-and-sign-research-addendum-2026.md`
- `dataset-first-sasl-foundation-strategy.md`
- `sasl-dataset-collection-governance-plan.md`
- `model-decision-matrix-2026.md`
- `cloud-local-deployment-options-2026.md`
- `ollama-restore-and-model-eval.md`

Application understanding and implementation planning:

- `application-abilities-and-model-requirements.md`
- `frontend-architecture-adr.md`
- `react-migration-plan.md`
- `modernization-roadmap.md`
- `phase-1-rescue-plan.md`
- `phase-1-implementation-approval-plan.md`
- `verification-matrix.md`
- `evaluation-harness-plan.md`
- `model-evaluation-fixtures-spec.md`
- `first-model-benchmark-runbook.md`
- `product-design-brief.md`
- `cleanup-deletion-proposal.md`
- `document-inventory.md`
- `defect-register.md`

## Evidence-Based Decisions

| Decision | Evidence |
|---|---|
| Do not keep one universal `amandla` model role. | Current services use one model for unrelated translation, rights, reconstruction, and landmark tasks. |
| Do not trust camera sign recognition yet. | HARPS metadata uses generic `SIGN_00` labels; 2026 sign-language research stresses dataset quality, signer splits, and annotation standards. |
| Do not build around a small local LLM. | User experience and research evidence show hallucination is unacceptable in critical communication paths. |
| Use cloud foundation models for development/research. | Larger cloud models reduce hallucination risk during engineering, annotation, design, and eval work. |
| Build AMANDLA's own specialized SASL model. | UCT and 2026 research show SASL needs more data, better annotation, temporal multimodal modeling, and community review. |
| Use OpenAI `gpt-5.5` as cloud text/eval baseline. | Official OpenAI docs name GPT-5.5 as the latest production model family and emphasize Structured Outputs and fresh baselines. |
| Keep cloud opt-in. | AMANDLA handles disability, communication, rights, and possible legal/employment content. |
| Build fixtures before pulling many models. | A bigger model that invents sign names is worse than deterministic rules plus validation. |

## Remaining Proof Work

The research loop cannot honestly claim the application is done. The next required proof work is:

1. Repair Python.
2. Implement the golden fixtures.
3. Add dataset consent/annotation fixtures.
4. Add a consented dataset manifest validator.
5. Run static forbidden-pattern checks.
6. Score deterministic rules first.
7. Use cloud foundation models only for development/eval assistance until production consent and privacy gates exist.
8. Add WebSocket contract tests.
9. Compare cloud only with synthetic or consented data.
10. Get explicit approval before production code changes, using `phase-1-implementation-approval-plan.md` as the boundary.
11. Keep `objective-traceability-matrix.md` current as implementation evidence replaces research-only evidence.

## Final Research Verdict

The research direction is ready to hand into Phase 1 implementation. The product itself is not yet proven modern, correct, or production-ready until the evaluator and runtime fixes run.
