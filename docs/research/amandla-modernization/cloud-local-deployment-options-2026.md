# AMANDLA Cloud And Local Deployment Options 2026

Date: 2026-07-05
Status: research proposal, not implementation

Strategic update: cloud foundation models should be used for development, research, annotation assistance, code generation, and evaluation. Live production communication still requires explicit consent and safety gates. Small local LLMs are fallback/benchmark tools, not the trusted translation core.

## Position

AMANDLA should not choose between "local" and "cloud" as a religion. It should expose three modes and route by task, consent, privacy, latency, and measured quality.

| Mode | Purpose | Network | Suitable Tasks |
|---|---|---:|---|
| `LOCAL_ONLY` | Default privacy and offline resilience. | No cloud AI calls. | Typed English to SASL, quick signs, history, emergency, local STT where good enough. |
| `QUALITY_CLOUD` | User-enabled quality boost. | Cloud calls allowed for selected tasks. | Rights drafts, difficult transcription, hard translation, evaluation. |
| `RESEARCH_EVAL` | Developer model comparison. | Cloud calls allowed only with fixtures or consented samples. | Benchmarking local vs cloud providers. |

## Recommended Architecture

```text
Renderer windows
  -> preload bridge only
  -> FastAPI WebSocket
  -> TaskRouter
       -> deterministic SASL services
       -> SpeechProvider
       -> TextModelProvider
       -> RightsProvider
       -> SignRecognitionProvider
       -> EvaluationLogger
```

Provider decisions should happen on the backend, never directly in renderer code.

## Provider Contracts

Each provider response should include:

```json
{
  "task": "english_to_sasl",
  "provider": "ollama",
  "model": "qwen3.5:4b",
  "mode": "LOCAL_ONLY",
  "prompt_version": "english_to_sasl_v1",
  "latency_ms": 0,
  "validated": true,
  "fallback_used": false,
  "output": {}
}
```

Logs should store provider metadata and validation status, not raw secrets, API keys, or unnecessary sensitive text.

## Local Deployment

Current local machine can evaluate small models:

- 40 GB RAM gives enough room for `qwen3.5:4b`, `qwen3:4b`, `qwen3:8b`, and possibly `gpt-oss:20b`.
- CPU-only inference is acceptable for research but may be too slow for live conversation.
- The RTX 3050 Laptop GPU is excluded for this phase by user instruction.
- Ollama is installed and serving, but no models are pulled.
- Python is still missing, so backend tests remain blocked.

Local defaults:

- Text tasks: `qwen3.5:4b` first.
- Speech: local faster-whisper once Python works.
- SASL correctness: deterministic rules.
- Camera recognition: disabled/experimental.

## Cloud Deployment

Cloud should be added through provider adapters, not direct calls in renderers.

### Option A: Desktop Local Backend With Optional Cloud Providers

The Electron app keeps its local FastAPI backend. Cloud providers are called only from backend services when mode allows it.

Pros:

- Minimal architecture change.
- Works offline for core flows.
- Privacy mode is easy to explain.
- Good for research and local demos.

Cons:

- User machine still needs Python/runtime packaging.
- Cloud keys and provider errors must be handled carefully.

Recommended first.

### Option B: Hosted Backend, Electron As Client

FastAPI runs in the cloud. Electron windows connect to the hosted backend.

Pros:

- Centralized model routing and observability.
- Easier cloud provider integration.
- Easier to run heavier evals/server-side jobs.

Cons:

- Offline story weakens.
- Privacy/data residency becomes more serious.
- WebSocket auth/session design must be hardened.
- Camera/audio data may cross network boundaries.

Use only after local product loop is stable.

### Option C: Hybrid Hosted Evaluation Service

The desktop app remains local. A separate cloud eval service receives only fixtures or explicitly consented samples.

Pros:

- Best research path.
- Keeps real user communication local by default.
- Lets researchers compare OpenAI, Google, Azure, Groq, DeepSeek, Claude, and other providers.

Cons:

- Requires careful data labeling and consent tracking.
- Does not solve production cloud UX by itself.

Recommended for research after Phase 1.

## Data Residency And Privacy

OpenAI data residency currently supports listed regions such as United States, Europe, Australia, Canada, Japan, India, Singapore, South Korea, United Kingdom, and United Arab Emirates, with regional processing varying by region. South Africa is not listed as an OpenAI data residency region in the current docs.

Implication for AMANDLA:

- Do not promise South African data residency for OpenAI calls.
- If South African residency is mandatory, host app data in a South African region where possible and evaluate Azure/other providers separately for AI processing locality.
- Treat rights incidents, disability information, voice recordings, and camera data as sensitive.
- Require explicit opt-in for cloud quality mode.

## Cloud Provider Ranking For AMANDLA

| Rank | Provider Path | Why | Use First For |
|---:|---|---|---|
| 1 | OpenAI Responses API with `gpt-5.5` | Strong structured text, reasoning, evals, and current docs. | Rights drafts, structured evaluation, hard translation review. |
| 2 | Google Chirp 3 | Strong multilingual ASR candidate with streaming, diarization, and auto language detection. | Speech comparison. |
| 3 | Azure Speech / Microsoft MAI Transcribe | Enterprise governance and language tables; Microsoft says MAI Transcribe 1.5 covers 43 languages. | Speech comparison and possible enterprise deployment. |
| 4 | Groq OpenAI-compatible API | Low-latency hosted model experiments with simple client abstraction. | Hosted open-model latency tests. |
| 5 | Claude Sonnet/Opus | Strong long-context and knowledge work candidate. | Rights/research drafting comparison. |
| 6 | DeepSeek/Mistral/Llama hosted | Strong reasoning/open-weight ecosystem. | Non-sensitive model comparison. |

## Implementation Guardrails For Later

No implementation should start until the user approves a code plan. When approved:

1. Add environment variables for model mode and provider keys.
2. Add backend provider interfaces.
3. Add schema validation for every provider output.
4. Add static checks proving renderers do not call cloud APIs.
5. Add a privacy indicator in the UI for local vs cloud mode.
6. Add a consent gate before sending rights text, audio, or camera data to a cloud provider.
7. Add eval logs with model, provider, latency, validation result, and fallback reason.

## Sources

- OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model
- OpenAI data residency guide: https://developers.openai.com/api/docs/guides/your-data#data-residency-controls
- OpenAI Realtime guide: https://developers.openai.com/api/docs/guides/realtime
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- Google Chirp 3 docs: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
- Azure Speech language support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- Microsoft Build 2026 model announcements: https://blogs.microsoft.com/blog/2026/06/02/microsoft-build-2026-be-yourself-at-work/
- Groq OpenAI compatibility: https://console.groq.com/docs/openai
