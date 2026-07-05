# AMANDLA Modernization Autoresearch

Status: active research setup
Branch/worktree: `codex/modernization-research` at `C:\Users\Admin\amandla-desktop-codex-research`
Started: 2026-07-05

## Goal

Turn AMANDLA from a rushed hackathon experiment into a modern, testable, accessibility-grade desktop communication system for hearing and deaf South Africans.

This research assumes the current application is not proven working. Every subsystem must earn its place through evidence: code inspection, tests, runtime checks, accessibility review, security review, and user workflow validation.

## Success Metric

The modernization research is successful when the project has:

1. A documented keep/archive/delete decision for every current document and historical planning artifact.
2. A recommended modern frontend architecture with alternatives rejected for concrete reasons.
3. A verified defect register covering protocol, security, packaging, AI/model, frontend, avatar, and accessibility risks.
4. A rebuild roadmap that separates immediate rescue work from the larger React/TypeScript migration.
5. An Ollama reinstallation/model plan that does not assume the existing `amandla` model works.
6. A repeatable evaluation plan for translation quality, avatar signing quality, speech quality, latency, security, and accessibility.
7. A 2026 AI model strategy that separates rule-first live communication, cloud-assisted research/development, and a future AMANDLA-owned specialized SASL model.
8. A current application-ability map that connects every AI capability to model requirements and proof gates.
9. A model decision matrix that names deterministic production paths, cloud development/research baselines, and local fallback/benchmark candidates.
10. Exact fixture contracts and a benchmark runbook for deterministic, cloud, and optional local fallback model evaluation.

## Constraints

- Do not disturb Claude's working tree at `C:\Users\Admin\amandla-desktop`.
- Do research and planning on this isolated worktree only.
- Do not delete existing files without explicit approval.
- Do not treat archived documents as current instructions.
- Preserve Electron security invariants: `contextIsolation: true`, `nodeIntegration: false`, no renderer `require()`.
- Preserve AMANDLA backend invariants: CORS `allow_origins=["*"]`, `.env` loaded once by backend startup, no raw Python exception details in HTTP responses.
- Evaluator: none yet. Manual research evaluation until a mechanical evaluator is added.
- `pause_every`: major artifact review. No unattended overnight loop until the user explicitly approves it.
- `max_iterations`: initial 6-iteration budget extended through continuation to 9 research-packaging iterations.
- Guard: no production code rewrites or destructive deletions during research setup.

## Current Approach

This first pass uses the autoresearch loop as a research protocol:

1. Inspect current repository state.
2. Compare it with Claude's uncommitted external work without editing that checkout.
3. Gather current official sources for Electron, React, Vite, Ollama, MediaPipe, accessibility, and sign-language avatar research.
4. Produce durable research artifacts in `docs/research/amandla-modernization/`.
5. Convert research into a staged rebuild plan only after the evidence base is strong enough.

## Search Space

- Frontend platform: vanilla DOM, React, Svelte, Solid, Vue, Next.js, Tauri, Electron Forge, electron-vite.
- Renderer architecture: per-window bundles, single React app with role routes, shared component library, typed preload API.
- 3D/avatar architecture: current Three.js engine, React Three Fiber wrapper, GLB/Mixamo driver, VRM/TalkingHead, custom keyframe clips.
- AI/model architecture: Ollama local models, provider abstraction, deterministic rule-first SASL pipeline, translation memory, eval-driven model choice.
- Cloud model architecture: OpenAI Responses/Structured Outputs, cloud speech providers, data residency, explicit opt-in routing.
- Testing: pytest, Vitest, Playwright, accessibility checks, WebSocket contract tests, golden translation scenarios, avatar pose validation.
- Documentation cleanup: current docs, archived docs, stale docs, research papers, duplicate transformer folder, generated databases, datasets.

## Context And References

Local:

- `CLAUDE.md` - current highest-priority project rules in the clean branch.
- `AGENTS.md` - coding-agent constraints and skill triggers.
- `AMD-ACTII-AI-Research-Papers-Dossier.md` - old project research dossier in Claude's dirty checkout; useful only as transferable AI-system research.
- `amandla-rebuild-plan.md` - external dirty-checkout audit; useful but not authoritative.
- `BIOMECHANICS_IMPL.md` - external dirty-checkout avatar biomechanics notes; useful but not authoritative.
- `SASL DOCUMEENTS/AMANDLA_Research_Synthesis.md` - relevant SASL/avatar synthesis.
- `docs/WEBSOCKET_PROTOCOL.md` - needs protocol reconciliation.
- `docs/research/amandla-modernization/application-abilities-and-model-requirements.md` - current AI ability map.
- `docs/research/amandla-modernization/model-decision-matrix-2026.md` - local/cloud model scorecard.
- `docs/research/amandla-modernization/cloud-local-deployment-options-2026.md` - local desktop and cloud-assisted research architecture.
- `docs/research/amandla-modernization/model-evaluation-fixtures-spec.md` - fixture contracts and scoring rules.
- `docs/research/amandla-modernization/first-model-benchmark-runbook.md` - first safe benchmark sequence after Python is restored.
- `docs/research/amandla-modernization/current-ai-and-sign-research-addendum-2026.md` - latest model/sign-language evidence addendum.
- `docs/research/amandla-modernization/dataset-first-sasl-foundation-strategy.md` - strategic pivot away from small local LLM core.
- `docs/research/amandla-modernization/sasl-dataset-collection-governance-plan.md` - consent and governance plan for AMANDLA-owned SASL dataset.
- `docs/research/amandla-modernization/completion-audit-2026-07-05.md` - requirement-by-requirement audit of what is proven and unproven.
- `docs/research/amandla-modernization/phase-1-implementation-approval-plan.md` - approval-ready code/test plan for the next implementation phase.
- `docs/research/amandla-modernization/README.md` - start-here index for the research package.
- `docs/research/amandla-modernization/objective-traceability-matrix.md` - objective-to-evidence traceability.

External:

- Electron security: https://www.electronjs.org/docs/latest/tutorial/security
- Electron Forge Vite template: https://www.electronforge.io/templates/vite
- Vite guide: https://vite.dev/guide/
- React 19: https://react.dev/blog/2024/12/05/react-19
- Ollama Windows install: https://docs.ollama.com/windows
- Ollama qwen3 model page: https://ollama.com/library/qwen3
- Google MediaPipe Hand Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker
- SignON virtual character deliverable: https://signon-project.eu/wp-content/uploads/2023/12/SignON_D5.2_A-Virtual-Character_v1.0.pdf
- Minor sign-language research topics: https://aclanthology.org/2024.signlang-1.16.pdf
- WCAG 2.2 contrast: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- NIST AI RMF: https://www.nist.gov/itl/ai-risk-management-framework
- OpenAI latest model guide: https://developers.openai.com/api/docs/guides/latest-model.md
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition in the Age of LLMs: https://arxiv.org/html/2604.11225v1
- SignAlignLM: https://aclanthology.org/2025.findings-acl.190.pdf
- AfriSign: https://link.springer.com/article/10.1007/s44163-025-00227-7
- OpenAI data residency controls: https://developers.openai.com/api/docs/guides/your-data#data-residency-controls
- OpenAI gpt-oss: https://openai.com/index/introducing-gpt-oss/
- Ollama gpt-oss: https://ollama.com/library/gpt-oss
- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Ollama Qwen3.6: https://ollama.com/library/qwen3.6
- Ollama Qwen3-VL 4B: https://ollama.com/library/qwen3-vl%3A4b
- Google Chirp 3: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
- Microsoft Build 2026 model announcements: https://blogs.microsoft.com/blog/2026/06/02/microsoft-build-2026-be-yourself-at-work/
- Sign Language Recognition and Translation for Low-Resource Languages: https://arxiv.org/html/2605.12096v1
- SignDATA: https://arxiv.org/html/2604.20357v1
- Bootstrapping Sign Language Annotations: https://arxiv.org/html/2604.07606v1
- Gloss-Free Sign Language Translation: https://arxiv.org/html/2603.13240v1
- DHH access to intelligent personal assistants: https://arxiv.org/html/2601.15209v2

## History

Rows before iteration 9 are historical. The current model strategy is the iteration 9 dataset-first pivot: cloud foundation models for development/research/annotation assistance, deterministic rules as the live production baseline, and an AMANDLA-owned specialized multimodal SASL model as the long-term production goal.

| Iteration | Hypothesis | Evidence | Decision | Notes |
|---|---|---|---|---|
| 0 | Treating the app as unproven will expose higher-value rebuild work than polishing the current UI. | Clean branch inspection found stale docs/tests, direct renderer fetches, a WebSocket assist-phrase bug, outdated Electron/build tooling, missing Python executable, and initially uncertain Ollama state. | Kept | Build research artifacts before code rewrites; Iteration 4 later verified Ollama is installed but has no models. |
| 1 | Turning the audit into cleanup, rescue, and product-design artifacts will make the rebuild executable without touching code too early. | Verified tracked archive files, duplicate transformer folder, duplicate PDF hash, generated DB files, current framework versions, and official React/Electron/Vite/Ollama/MediaPipe/WCAG sources. | Kept | Added cleanup proposal, Phase 1 rescue plan, product design brief, and TSV results log. |
| 2 | A React migration is only useful if paired with proof gates and an evaluation harness before implementation. | Rechecked package ecosystem versions, local renderer/backend risk patterns, Product Design brief requirements, and testing constraints. | Kept | Added React migration plan, verification matrix, and evaluation harness plan. |
| 3 | AMANDLA needs a task-specific local/cloud model strategy, not one universal Ollama model inherited from the old hackathon approach. | Read the user's old AMD ACT II dossier, current AI service code, HARPS metadata, SASL/avatar research synthesis, OpenAI docs, and 2025/2026 sign-language and model sources. | Kept | Added AI model strategy and paper refresh docs; updated Ollama and evaluation plans. |
| 4 | Converting the model strategy into an ability map, decision matrix, and cloud/local deployment options will make the research actionable without touching production code. | Verified current machine RAM/CPU/GPU, Ollama `0.30.10` with empty model list, broken Python shim, OpenAI/Google/Azure/Microsoft/Qwen/Gemma/GPT-OSS/Llama/Mistral/DeepSeek/Groq sources, and sign-language community/dataset research. | Kept | Added ability map, model decision matrix, and cloud/local deployment options; corrected stale Ollama status in existing docs. |
| 5 | The model strategy needs exact fixture schemas and a first-run benchmark sequence before any model pull or cloud experiment is meaningful. | Converted the harness plan into JSON fixture contracts for translation, sign reconstruction, speech, rights, provider comparison, and sign-recognition dataset cards; defined the first local benchmark order. | Kept | Added fixture spec and benchmark runbook; linked them into the harness implementation order. |
| 6 | A completion audit and fresh current-model pass are needed before claiming the research is done. | Rechecked current OpenAI/Ollama/sign-language sources, found newer `qwen3.5:4b`, reviewed Qwen3.6/Qwen3-VL and additional 2026 sign-language papers, and audited the objective requirement by requirement. | Kept | Updated first local model recommendation to `qwen3.5:4b`; added addendum and completion audit; full implementation remains unproven until Python/model eval work runs. |
| 7 | The next gap is not more broad research, but an approval-ready Phase 1 code/test boundary. | Re-read current code anchors for assist phrase crash, preload auth lifecycle, direct renderer fetch, stale WebSocket docs/tests, and raw error details; mapped each to files, functions, tests, and stop conditions. | Kept | Added Phase 1 implementation approval plan; no production code changed. |
| 8 | The research package needs a start-here index and traceability map so the work is reviewable and not just a pile of documents. | Re-read the research folder, current completion audit, and old dossier touchpoints; mapped the original objective to current artifacts, proof state, and remaining gates. | Kept | Added README and objective traceability matrix; production code remains unchanged. |
| 9 | User research and the attached UCT thesis justify a dataset-first SASL foundation strategy instead of a small-local-LLM-centered strategy. | Extracted the UCT thesis PDF metadata and abstract evidence: 5047 sentences, about five hours of SASL data, BLEU-4 1.35, and a conclusion that results are far from practical; reconciled this with current sign-language AI research. | Kept | Added dataset-first SASL foundation strategy and dataset governance plan; downgraded small local LLMs to fallback/benchmark role. |
