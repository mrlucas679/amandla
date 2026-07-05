# AI Paper Refresh For AMANDLA

Date: 2026-07-05
Status: research synthesis, not implementation

## Why This Exists

The old AMD ACT II paper dossier was written for a different retail, multi-agent, GPU-oriented hackathon project. AMANDLA should reuse only the durable research habits:

- Define evidence contracts for every AI output.
- Prefer validation, retry, fallback, and deterministic recovery.
- Build project-specific evaluations instead of trusting public benchmark scores.
- Log latency, failures, and model validation results.
- Treat synthetic data as a development scaffold, not proof of real-world quality.

AMANDLA should not inherit:

- Retail operations assumptions.
- GPU-first hosting assumptions.
- Multi-agent orchestration as a default architecture.
- GraphRAG or vector memory before the core translation and avatar loop works.

## Current Paper Themes

### 1. Sign-Language Datasets Are Still Hard

The 2026 survey "Sign-Language Datasets at Scale" catalogs the dataset landscape and highlights recurring problems: uneven modality coverage, annotation inconsistency, signer bias, limited metadata, and weak coverage for many languages.

AMANDLA action:

- Do not claim production sign recognition without a project-specific SASL dataset.
- Record handedness, signer consent, camera conditions, annotation source, signer split, and license for any future data.
- Keep signer-disjoint test sets so the recognizer is not only memorizing one person.

### 2. General VLMs/LLMs Are Not A Free Sign Recognizer

"Sign Language Recognition in the Age of LLMs" evaluates the promise and limits of modern large models for sign recognition. The important lesson for AMANDLA is that sign recognition remains a specialized vision/temporal-language problem.

AMANDLA action:

- Stop treating an Ollama prompt over hand landmarks as a production recognizer.
- Use temporal landmark/video models for camera recognition.
- Keep manual sign buttons and assist phrases as reliable paths while recognition research continues.

### 3. Sign-Language Translation Needs Linguistic Structure

SignAlignLM and related 2025 work show that adapting large models to sign-language tasks can help, but signed languages differ from spoken languages in grammar, visual form, and timing.

AMANDLA action:

- Keep the SASL grammar transformer and `sign_maps.py` as the safety base.
- Use LLMs to assist under schema, not to replace linguistic rules blindly.
- Evaluate whether a model preserves SASL markers such as `FINISH`, `WILL`, `CAN`, and `MUST`.

### 4. African Sign-Language Work Points Toward Practical SLT

AfriSign frames African sign-language machine translation as a practical need and notes that many earlier efforts focus on isolated recognition or generic action-recognition framing.

AMANDLA action:

- Optimize for communication outcomes, not only isolated-sign accuracy.
- Measure end-to-end tasks: "Can a deaf user communicate a need to a hearing user?" and "Can a hearing user send a usable signed message?"
- Include South African accessibility and rights contexts in golden tests.

### 5. SASL-Specific Work Exists But Must Be Operationalized

The University of Cape Town SASL translation work is directly relevant because it addresses vision-based translation for South African Sign Language.

AMANDLA action:

- Use SASL-specific research to guide dataset design and evaluation categories.
- Do not import old results as proof for AMANDLA's current code.
- Compare any camera recognizer against SASL-specific baselines where available.

### 6. Avatar Research Supports Deterministic Motion Plus Human Review

Local AMANDLA research synthesis points to SignON avatar work, VLibras correction findings, and motion-evaluation ideas such as trajectory comparison. The recurring message is that motion quality matters and hand movement errors are highly visible.

AMANDLA action:

- Keep avatar motion deterministic and inspectable.
- Build tests that check sign names map to valid motion definitions.
- Add visual/canvas checks and later trajectory-style comparisons for important signs.
- Use deaf consultant review for production sign quality.

## Model Release Implications

### OpenAI

OpenAI's current platform docs position `gpt-5.5` as the latest general model and recommend the Responses API, reasoning controls, prompt caching, and Structured Outputs. The audio docs also separate live realtime transcription/translation from file transcription.

AMANDLA action:

- Use OpenAI cloud mode as a high-quality optional path for rights analysis, rights letters, hard translation cases, and evaluation assistance.
- Use Structured Outputs for any cloud model response that feeds app logic.
- Use `gpt-4o-transcribe` or `gpt-realtime-whisper` as speech baselines in evaluation.
- Do not make OpenAI the default for raw camera data.

### Qwen

Qwen3 and Qwen3.5 are strong local/open candidate families and are available through Ollama. After the dataset-first pivot, `qwen3.5:4b` is only the better optional local fallback/benchmark candidate than the old `qwen2.5:3b` baseline or the earlier `qwen3:4b` recommendation. It should not become AMANDLA's trusted translation brain.

AMANDLA action:

- Run local text-model evaluation only after deterministic fixtures, consent schemas, and cloud-assisted research baselines exist.
- If a local fallback benchmark is still useful, test `qwen3.5:4b` before older Qwen baselines.
- Compare `qwen3.5:2b` for low-resource fallback, `qwen3:4b` as the conservative baseline, and `qwen3:8b` if hardware allows.

### Gemma

Google's Gemma family now includes device-oriented models. These are plausible local candidates when runtime support and licensing fit the project.

AMANDLA action:

- Treat Gemma E2B/E4B-class models as comparison candidates.
- Verify actual local runtime availability before committing to an Ollama tag.

### GPT-OSS

OpenAI's GPT-OSS models introduce open-weight reasoning options, including a 20B model described for edge-class memory.

AMANDLA action:

- Consider `gpt-oss:20b` only after measuring memory and latency on the target machine.
- Do not use it for live workflows if it makes the desktop app feel frozen.

### Llama, Mistral, DeepSeek, Groq

Current Llama 4, Mistral Small 4, DeepSeek V3.2, and Groq-hosted options are interesting for cloud/provider comparisons. They are not the right CPU-only default path for AMANDLA's immediate rescue phase.

AMANDLA action:

- Use them as optional research comparators.
- Keep privacy, data residency, and provider-locking concerns visible.

## Product-Specific Evaluation Questions

The next evaluation harness should answer:

1. Does local STT handle AMANDLA's target South African languages and accents well enough?
2. Does the model preserve required SASL signs and markers?
3. Does the model ever emit unknown signs not present in `signs_library.js`?
4. Does sign reconstruction preserve the user's intent without inventing facts?
5. Does rights analysis produce useful structure without pretending to be legal advice?
6. Does the avatar play every emitted sign without throwing or going blank?
7. Does the system fall back safely when a provider is missing, slow, or invalid?
8. Does every cloud call require an explicit mode decision and avoid raw sensitive logging?

## Updated Research Direction

AMANDLA should become:

- Local-first for core communication.
- Cloud-optional for quality, evaluation, and hard language cases.
- Rule-first for SASL correctness.
- Dataset-first for camera sign recognition.
- Schema-first for model outputs.
- Evidence-first for every "working" claim.

## Sources

- AMD ACT II pasted research dossier supplied by the user in this thread.
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition in the Age of LLMs: https://arxiv.org/html/2604.11225v1
- SignAlignLM: https://aclanthology.org/2025.findings-acl.190.pdf
- AfriSign: https://link.springer.com/article/10.1007/s44163-025-00227-7
- UCT SASL translation work: https://open.uct.ac.za/items/5c66b556-1f37-4b1c-b12d-cba33a6f5728
- OpenAI latest model guide: https://developers.openai.com/api/docs/guides/latest-model.md
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Realtime API: https://developers.openai.com/api/docs/guides/realtime
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI GPT-OSS announcement: https://openai.com/index/introducing-gpt-oss/
- Qwen3 announcement: https://qwenlm.github.io/blog/qwen3/
- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Google Gemma docs: https://ai.google.dev/gemma/docs/core
- Meta Llama 4 announcement: https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- DeepSeek API news: https://api-docs.deepseek.com/news/news251201
- Groq OpenAI compatibility: https://console.groq.com/docs/openai
