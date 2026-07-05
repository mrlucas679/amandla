# AMANDLA AI Model Strategy 2026

Date: 2026-07-05
Status: research proposal, not implemented
Branch/worktree: `codex/modernization-research` at `C:\Users\Admin\amandla-desktop-codex-research`

## Purpose

AMANDLA needs a model strategy that fits this project, not the old AMD ACT II retail hackathon project. The useful idea from the old dossier is not a specific model stack. The useful idea is discipline: every AI output needs a task-specific contract, validation, fallback, and evaluation.

The current app should be treated as a local desktop accessibility system with deterministic live-communication baselines, cloud-assisted development/research/annotation modes, and a future AMANDLA-owned specialized SASL model. GPU-first local plans, vLLM hosting, and retail multi-agent architecture are out of scope for the current phase.

## Local Reality Check

Current code has several AI surfaces:

| Surface | Current Implementation | Research Decision |
|---|---|---|
| Speech to text | `backend/services/whisper_service.py` uses local faster-whisper with optional NVIDIA fallback. | Keep local STT as the default offline path, but benchmark it by language and noise level. |
| English to SASL signs | `backend/services/sasl_pipeline.py` uses rule-based transformer plus Ollama fallback. | Keep rules as the source of truth. Use models only as constrained helpers. |
| Non-English to English | Ollama translation helper before SASL conversion. | Evaluate per South African language. Do not claim broad SA language support without measured results. |
| Sign sequence to English | `backend/services/sign_reconstruction.py` uses Ollama then a rule fallback. | Prefer rule-first reconstruction for safety, then model fluency under a schema. |
| Rights analysis and letters | `backend/services/claude_service.py` is actually an Ollama-backed rights service with templates. | Keep templates as fallback. Cloud quality mode may be valuable here, but privacy and legal review matter. |
| Camera sign recognition | HARPS recognizer exists, plus an Ollama landmark classifier. | Treat as experimental. The current checkpoint labels are generic `SIGN_00` to `SIGN_20`, not production SASL signs. |
| Avatar signing | Three.js sign library and avatar drivers. | Do not use an LLM for motion. Use deterministic sign data, human review, and motion tests. |

## Task-Specific Model Roles

AMANDLA should stop treating one Ollama model named `amandla` as the universal brain. The project also should not treat any small local LLM as the trusted product brain. The strategic direction is cloud-assisted development/research plus an AMANDLA-owned specialized multimodal SASL model trained on consented data.

| Role | Default | Optional Quality Mode | Hard Rule |
|---|---|---|---|
| `speech_transcription` | Local faster-whisper CPU model. | OpenAI `gpt-4o-transcribe` or `gpt-realtime-whisper`; Google Chirp 3 or Azure Speech if target languages test better. | Measure language coverage before claims. |
| `text_translate_to_english` | Local rules and local model only when validated. | Cloud translation/STT provider selected by language coverage tests. | Sanitize input before model calls. |
| `english_to_sasl` | `sign_maps.py` plus SASL transformer rules. | Cloud LLM can propose glosses under strict schema for review/eval. | Never drop critical signs such as `FINISH`, `WILL`, `CAN`, or `MUST`. |
| `sasl_to_english` | Rule reconstruction from known sign sequences. | Cloud/local model can improve fluency after signs are validated. | Do not invent signs that were not observed. |
| `rights_analysis` | Local template plus local LLM if it passes golden tests. | OpenAI Responses API with Structured Outputs for better quality. | User-facing errors stay generic; no raw provider output leaks. |
| `rights_letter` | Local template plus local LLM if it passes golden tests. | Cloud model for opt-in quality mode. | Keep generated letters editable and clearly review-required. |
| `sign_recognition` | Manual sign buttons and assist phrases until evidence improves. | Future temporal landmark/video model trained on consented SASL data. | Do not rely on generic text LLM landmark classification. |
| `eval_judge` | Deterministic checks where possible. | Cloud LLM can help judge nuance, but cannot be the only evaluator. | Keep product-specific golden tests primary. |

## Local Model Candidates

Local models are useful only if they pass AMANDLA tests on the user's hardware.

| Candidate | Best Fit | Caution |
|---|---|---|
| `qwen3.5:4b` | Local fallback and benchmark candidate for multilingual instruction following and JSON discipline. | Must not be treated as the trusted product brain. |
| `qwen3:4b` | Conservative fallback baseline. | Older than Qwen3.5 but smaller and likely practical. |
| `qwen3:8b` | Higher-quality local candidate if memory and latency allow. | May be too slow on CPU-only hardware. |
| `qwen3.5:2b` | Low-resource fallback. | Likely too weak for nuanced rights or translation work. |
| Gemma 4 E2B/E4B class models | Device-friendly comparison candidate if local runtime support is available. | Verify actual Ollama/runtime availability before standardizing. |
| `gpt-oss:20b` | Strong open-weight reasoning candidate for machines with enough memory. | OpenAI describes 20B as edge-capable around 16 GB memory; latency may still be too high for live desktop UX. |
| `llama3.2:3b` | Compatibility baseline. | Use as a fallback comparison, not the target. |
| Existing `qwen2.5:3b` | Historical baseline. | Do not keep it just because the old `Modelfile` used it. |

Large open-weight models such as Llama 4, Mistral Small 4, and DeepSeek V3.2-class systems are better treated as hosted/provider candidates for now. They are not a practical CPU-only local path for this phase.

## Cloud Model Strategy

Cloud use should be opt-in and role-specific.

### Recommended First Cloud Provider

OpenAI is the strongest first cloud target for this research phase because the current documentation supports:

- `gpt-5.5` as the latest general model for high-quality reasoning and generation.
- Responses API for reasoning, tools, and structured workflows.
- Structured Outputs for JSON Schema constrained responses.
- `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, and `gpt-realtime-whisper` for speech.
- `gpt-realtime-translate` for live speech translation where appropriate.

Use cloud quality mode first for:

- Rights analysis and rights letters.
- Evaluation assistance for translation quality.
- Difficult multilingual transcription or translation cases after local failure.

Avoid cloud by default for:

- Raw camera frames or landmarks.
- Sensitive personal incidents unless the user explicitly enables cloud mode.
- Any path where local deterministic logic is already accurate enough.

### Other Provider Candidates

| Provider | Why Consider It | Current Position |
|---|---|---|
| Google Speech-to-Text Chirp 3 | Broad multilingual ASR and cloud speech tooling. | Evaluate if South African language speech support beats OpenAI/local Whisper. |
| Azure Speech | Enterprise deployment, regional cloud infrastructure, language tables. | Evaluate especially if the deployment must align with Microsoft/Azure governance. |
| Groq | Low-latency hosted inference with OpenAI-compatible APIs. | Good research candidate for hosted open models, not the first privacy-sensitive path. |
| DeepSeek API | Strong hosted reasoning/coding models. | Compare for non-sensitive evaluation or developer tooling only until privacy/compliance is reviewed. |
| NVIDIA NIM | Current code has optional NIM hooks. | Defer because user explicitly excluded GPU-first work for now. |

## Privacy And Data Residency

AMANDLA handles disability, communication, employment, education, and possible legal-rights content. Model routing must be privacy-aware.

Proposed modes:

| Mode | Behavior |
|---|---|
| `LOCAL_ONLY` | No cloud model calls. Deterministic rules, local STT, local LLM if installed, template fallbacks. |
| `QUALITY_CLOUD` | User-enabled cloud calls for specific tasks such as rights letters or hard transcription cases. |
| `RESEARCH_EVAL` | Developer-only model comparison mode. Uses fixtures or explicitly consented samples. |

OpenAI's current data residency list does not include South Africa. If South African data residency is mandatory, AMANDLA should host app data in a South African cloud region where possible and separately verify where each AI provider processes model requests.

## Sign Recognition Direction

Do not invest more effort in prompt-based landmark classification as a production path. The correct direction is:

1. Keep manual sign buttons and assist phrases working as reliable communication paths.
2. Build consented SASL data collection with metadata: signer consent, handedness, camera conditions, signer demographics where appropriate, annotation protocol, and train/test split.
3. Train or fine-tune a temporal landmark/video recognizer on real SASL labels.
4. Evaluate isolated signs, continuous sign sequences, signer generalization, low light, distance, occlusion, left-handed signing, and camera angle changes.
5. Only then expose camera recognition as a user-facing feature.

The existing HARPS checkpoint is useful as a framework proof, not as production evidence, because its metadata lists generic class names such as `SIGN_00`.

## Architecture Proposal

Add a provider abstraction later, after the user approves code work.

```text
ModelRouter
  -> SpeechProvider
       -> LocalWhisperProvider
       -> OpenAITranscribeProvider
       -> GoogleSpeechProvider
       -> AzureSpeechProvider
  -> TextModelProvider
       -> OllamaProvider
       -> OpenAIResponsesProvider
       -> GroqCompatibleProvider
  -> SignRecognitionProvider
       -> ManualSignProvider
       -> HarpsExperimentalProvider
       -> FutureTemporalSaslProvider
```

Routing rules should be explicit:

- Each request declares its task role.
- Each provider declares whether it is local or cloud.
- Cloud providers are disabled unless the current mode permits them.
- Structured responses are validated before use.
- Unknown or invalid model output falls back to deterministic logic.
- Logs record provider name, latency, status, and validation result, not secrets or raw sensitive payloads.

## Immediate Decisions

1. Keep AMANDLA as a local desktop app with a deterministic live-communication baseline.
2. Split the single `amandla` model concept into task-specific roles.
3. Treat the current `qwen2.5:3b` model as a baseline only.
4. Use powerful cloud foundation models for development, research, annotation assistance, code generation, and system design.
5. Keep local small LLMs as fallback/benchmark tools only.
6. Benchmark speech by target South African languages before making language-support claims.
7. Treat camera sign recognition as experimental until there is real SASL data and temporal evaluation.
8. Build AMANDLA's own consent-based SASL dataset and specialized multimodal model as the long-term production path.

## Sources

- OpenAI latest model guide: https://developers.openai.com/api/docs/guides/latest-model.md
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI Realtime API: https://developers.openai.com/api/docs/guides/realtime
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI GPT-OSS announcement: https://openai.com/index/introducing-gpt-oss/
- OpenAI data residency update: https://openai.com/index/expanding-data-residency-access-to-business-customers-worldwide/
- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Qwen3 announcement: https://qwenlm.github.io/blog/qwen3/
- Ollama Qwen3 library: https://ollama.com/library/qwen3
- Google Gemma docs: https://ai.google.dev/gemma/docs/core
- Meta Llama 4 announcement: https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- DeepSeek API news: https://api-docs.deepseek.com/news/news251201
- Groq OpenAI compatibility: https://console.groq.com/docs/openai
- Google Cloud Chirp 3 docs: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
- Azure Speech language support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
