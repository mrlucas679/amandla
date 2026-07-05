# AMANDLA Dataset-First SASL Foundation Strategy

Status: strategic pivot accepted into research package
Date: 2026-07-05
Branch: `codex/modernization-research`

## Decision

AMANDLA should not be built around a small local text model as its core communication engine.

Small local language models can remain useful for cheap experiments, offline fallback tests, and developer comparisons, but they should not be treated as the product's trusted translation intelligence. For high-stakes contexts such as clinics, hospitals, public service offices, and rights support, hallucination makes it impossible to distinguish model failure from application failure. That is not acceptable for a real-time accessibility system.

The new strategy is:

1. Use powerful cloud-hosted foundation models during development, research, annotation, system design, and code assistance.
2. Keep production user communication rule-first and validation-first until AMANDLA has enough evidence for learned translation.
3. Build a consent-based, community-reviewed SASL dataset through the application and research partnerships.
4. Train AMANDLA's own specialized multimodal SASL model over time.
5. Treat the dataset, annotation process, and Deaf/SASL community review as the real long-term advantage.

## What Changes From Earlier Research

Earlier research recommended `qwen3.5:4b` as the first local model to benchmark. That remains useful only as a local comparison candidate, not as the strategic center of AMANDLA.

| Earlier Position | Revised Position |
|---|---|
| First local model to benchmark: `qwen3.5:4b`. | Keep `qwen3.5:4b` only as a local benchmark/fallback experiment. |
| Local model may help SASL and rights tasks if it passes fixtures. | Local small LLM must not be the trusted product brain for critical communication. |
| Cloud mode is optional quality mode. | Cloud foundation models are strongly recommended for development, research, annotation, and engineering quality. |
| Future camera recognition needs real SASL data. | AMANDLA's core moat is the consent-based SASL dataset and specialized multimodal model. |

## Evidence From The Attached UCT Thesis

The attached PDF is:

`Vision-Based Automatic Translation for South African Sign Language (SASL)`, Mokgadi Setshekgamollo, University of Cape Town, MSc thesis.

Key evidence extracted from the PDF:

- It reports the first vision-based neural SLT model for SASL.
- The dataset contains 5047 SASL/English sentence segments.
- The data is about five hours of signing.
- The domain is government and politics.
- Recording was studio based with a uniform green background.
- The best reported SASL result is BLEU-4 1.35.
- The thesis explicitly concludes that the results are still far from practical and that more data, better annotation, and Deaf community collaboration are needed.

This supports the conclusion that there is no production-ready SASL foundation model today. The practical product path is dataset creation and specialized model training, not plugging in a generic small LLM.

## Evidence From Current Research

Recent sign-language AI work reinforces the same direction:

| Research Source | Implication For AMANDLA |
|---|---|
| Sign-Language Datasets at Scale (2026) | Dataset fragmentation, inconsistent annotation, modality imbalance, and signer bias constrain progress. AMANDLA needs dataset governance, not just model swapping. |
| Low-Resource Sign Language Recognition and Translation (2026) | Low-resource sign languages need community co-design, dialect diversity, privacy-preserving representations, and task-specific metrics. |
| Sign Language Recognition in the Age of LLMs (2026) | Prompt-only zero-shot VLMs still lag supervised sign recognition; larger proprietary VLMs help but do not remove the need for task-specific data. |
| Gloss-Free Sign Language Translation (2026) | The field is moving toward direct video-to-text methods, but fair evaluation shows reported gains are fragile and depend heavily on implementation details and metrics. |
| UCT SASL thesis | SASL-specific neural translation is early-stage, low-data, and not practical for live deployment yet. |

## Revised Model Roles

| Role | Recommended Model Strategy |
|---|---|
| Development reasoning and engineering | Powerful cloud-hosted foundation model, defaulting to OpenAI `gpt-5.5` unless another frontier provider wins internal eval. |
| Dataset annotation assistance | Cloud multimodal foundation model plus human Deaf/SASL reviewer, never model-only ground truth. |
| Code generation and system design | Cloud foundation model with repository-aware review, tests, and security checks. |
| Production hearing text to SASL avatar | Deterministic rules and validated sign maps until a specialized AMANDLA model is trained. |
| Production deaf sign to hearing speech | Manual sign buttons and assist phrases first; learned camera recognition only after dataset/eval gates. |
| Speech transcription | Compare OpenAI speech, Google Chirp 3, Azure Speech / MAI Transcribe on consented South African fixtures. |
| Future SASL foundation model | AMANDLA-owned multimodal model trained on consented video, pose, facial expression, body posture, gloss/text, and context metadata. |
| Small local LLMs | Benchmark/fallback only. Not the product intelligence center. |

## Cloud GPU Interpretation

The original research constraint excluded GPU-first local work. This remains true:

- Do not make the current laptop's GPU the development bottleneck.
- Do not design Phase 1 around local GPU training.
- Do not require GPU setup before protocol and evaluation gates.

Cloud GPU-backed foundation models are acceptable for development and research because the user is buying capability as a service, not building AMANDLA around local GPU infrastructure. Production cloud use must still be explicit, consented, logged, and privacy reviewed.

## Dataset Strategy

AMANDLA should collect data only with explicit consent and clear purpose labels.

Minimum dataset records:

| Field | Purpose |
|---|---|
| `consent_id` | Proves collection and use permission. |
| `participant_profile` | Supports bias checks without exposing private identity. |
| `sign_language` | Must be SASL, with dialect/community notes where relevant. |
| `task_context` | Clinic, public service, education, rights, daily conversation, emergency, etc. |
| `video_uri` | Stored securely, not committed to source control. |
| `pose_uri` | Privacy-preserving derived representation where possible. |
| `facial_landmarks_uri` | Captures non-manual features when consented. |
| `gloss_annotation` | Optional but valuable, reviewed by SASL experts. |
| `english_translation` | Human-reviewed target text. |
| `review_status` | Draft, model-assisted, human-reviewed, Deaf/SASL-approved. |
| `split` | Train, validation, test, unseen signer test. |
| `safety_domain` | Flags medical, rights, emergency, child, or other sensitive contexts. |

## Product Roadmap

| Phase | Goal | Model Use |
|---|---|---|
| Phase 1 | Make app testable and honest. | No trusted LLM translation. Rules, fixtures, protocol tests. |
| Phase 2 | Add cloud-assisted research tooling. | Powerful cloud model helps annotation, reviewer workflows, dataset QA, code, and eval. |
| Phase 3 | Collect consented SASL dataset. | Model suggestions are reviewed; human labels remain ground truth. |
| Phase 4 | Train first AMANDLA SASL model. | Multimodal temporal model trained on AMANDLA data; benchmark against held-out signers. |
| Phase 5 | Carefully deploy learned translation. | Use confidence thresholds, fallback, human-review mode, and critical-domain restrictions. |

## Safety Rule

For medical, legal, rights, emergency, and government-service conversations:

- A model may assist.
- A model may suggest.
- A model may help annotate.
- A model may never silently replace validation, consent, audit logs, or human/community review.

## Updated Recommendation

The best strategic direction is no longer "which small model should AMANDLA run locally first?"

The better question is:

How does AMANDLA build the highest-quality consented SASL dataset and use cloud foundation models to accelerate that work while keeping production communication safe?

That is the direction this research package should follow.

## Sources

- Local PDF: `C:\Users\Admin\AppData\Local\Packages\5319275A.WhatsAppDesktop_cv1g1gvanyjgm\LocalState\sessions\C67C7D89A03DBCBFE9C83079965E59769ACF9D21\transfers\2026-27\content.pdf`
- UCT thesis record: https://open.uct.ac.za/items/5c66b556-1f37-4b1c-b12d-cba33a6f5728
- OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition and Translation for Low-Resource Languages: https://arxiv.org/html/2605.12096v1
- Sign Language Recognition in the Age of LLMs: https://arxiv.org/html/2604.11225v1
- Gloss-Free Sign Language Translation: https://arxiv.org/html/2603.13240v1

