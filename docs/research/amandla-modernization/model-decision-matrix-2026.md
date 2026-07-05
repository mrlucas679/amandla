# AMANDLA Model Decision Matrix 2026

Date: 2026-07-05
Status: research recommendation, not implementation

## Decision Summary

Recommended default path after the dataset-first pivot:

1. Restore Python first; no backend tests can be trusted without it.
2. Keep deterministic SASL rules as the production source of truth until a specialized AMANDLA SASL model exists.
3. Do not treat small local LLMs as the trusted product brain.
4. Use OpenAI `gpt-5.5` or an equivalent frontier cloud model as the first development/research/annotation baseline.
5. Build a consent-based SASL dataset and human review workflow as the main strategic asset.
6. Compare OpenAI speech, Google Chirp 3, Azure Speech, and Microsoft MAI Transcribe for speech only after target-language fixtures exist.
7. Keep `qwen3.5:4b`, `qwen3:4b`, and `gpt-oss:20b` as optional local benchmark/fallback candidates, not product strategy.

## Local Candidate Matrix

These models are not the strategic core. They are fallback or benchmark candidates only.

| Candidate | Evidence | Best AMANDLA Role | Local Fit On This Machine | Decision |
|---|---|---|---|---|
| `qwen3.5:4b` | Ollama lists a 4.66B, 3.4 GB model with vision/tools/thinking tags, efficient hybrid architecture, and expanded language coverage. | Local fallback/benchmark helper only. | Good test on 40 GB RAM CPU laptop; must measure CPU latency. | Optional benchmark, not product core. |
| `qwen3:4b` | Ollama lists 2.5 GB size; Qwen says Qwen3 supports hybrid thinking and 100+ languages/dialects. | Conservative fallback and comparison baseline. | Very practical. | Try if 3.5 is unstable or slow. |
| `qwen3.5:2b` | Smaller model in the newer 3.5 family. | Emergency low-latency fallback. | Easy to run. | Try if 4B latency fails. |
| `qwen3:8b` | Ollama lists 5.2 GB. | Better local quality if 4B underperforms. | Possible; likely slower. | Try after 4B class models. |
| `qwen3-vl:4b` | Ollama lists a 4.44B, 3.3 GB vision-language model. | Optional visual/document/UI research. | Plausible locally. | Not for production sign recognition. |
| `qwen3.6:27b` / `qwen3.6:35b` | Ollama lists 17 GB / 24 GB model files and coding-agent focus. | Developer/research comparison. | Too large for first live local path on CPU. | Defer. |
| `gpt-oss:20b` | Ollama lists 14 GB; OpenAI says 20B can run around 16 GB memory and supports reasoning/tooling/Structured Outputs. | Strong local reasoning and rights/translation comparison. | Possible in RAM, but CPU latency may be poor; GPU excluded. | Stretch experiment, not default. |
| Gemma 4 E2B/E4B class | Google lists E2B/E4B sizes and GGUF/mobile artifacts. | Local comparison for speed and structured text. | Plausible if runtime packaging is easy. | Compare after Qwen. |
| `llama3.2:3b` | Common Ollama baseline. | Backup baseline. | Easy. | Only if Qwen fails. |
| Current `qwen2.5:3b` | Current `Modelfile` baseline. | Historical compatibility check. | Likely easy. | Do not keep as target unless it wins eval. |

## Cloud Candidate Matrix

| Candidate | Evidence | Best AMANDLA Role | Concern | Decision |
|---|---|---|---|---|
| OpenAI `gpt-5.5` | Official docs name it as latest and recommend Responses API, reasoning controls, prompt caching, and Structured Outputs. | Rights analysis, rights letters, structured eval judge, difficult translation review. | OpenAI data residency does not include South Africa; cloud must be opt-in. | First cloud text baseline. |
| OpenAI speech models | Official docs list `gpt-4o-transcribe`, `gpt-4o-mini-transcribe`, diarization, and `gpt-realtime-whisper`. | Speech transcription and live mic comparison. | Supported language list omits several South African official languages. | Evaluate, do not assume full coverage. |
| Google Chirp 3 | Google docs call Chirp 3 latest multilingual ASR, with streaming, diarization, and automatic language detection. | Speech-language coverage benchmark. | Regional support is `us` and `eu`; many languages are preview. | Strong speech comparison candidate. |
| Azure Speech / MAI Transcribe | Microsoft docs say language support varies by feature; Build 2026 says MAI Transcribe 1.5 covers 43 languages. | Enterprise speech comparison, possible Azure governance alignment. | Need exact South African language and regional availability checks. | Strong speech comparison candidate. |
| Claude Sonnet 5 / Opus class | Anthropic docs/news position Claude as strong for agents, long context, and knowledge work. | Optional rights-letter and research-writing comparison. | No existing active integration in current AMANDLA code; no speech role. | Compare later, not first. |
| Groq OpenAI-compatible API | Groq docs support OpenAI client `base_url` swap. | Low-latency hosted open-model comparison. | Provider privacy and model availability must be checked per task. | Good provider-router experiment. |
| DeepSeek V3.2 API | DeepSeek docs describe reasoning-first agent models and tool-use. | Non-sensitive reasoning benchmark. | Cloud/privacy/legal review needed; not speech/sign-specific. | Research comparator only. |
| Mistral Small 4 | Mistral says it is Apache 2.0, multimodal, reasoning-optimized, 256k context, but minimum infra is multi-H100 class. | Hosted/cloud multimodal comparison. | Not local for this phase. | Cloud comparator only. |
| Llama 4 Scout/Maverick | Meta says Llama 4 is open-weight, multimodal MoE with large active/total parameter counts and huge context. | Hosted multimodal/long-context comparison. | Not local CPU/laptop path. | Cloud/hosted comparison only. |

## Task Routing Matrix

| AMANDLA Task | Default | Local Model Candidate | Cloud Candidate | Acceptance Gate |
|---|---|---|---|---|
| Typed English to SASL signs | Rules and `sign_maps.py`. | `qwen3.5:4b` only as constrained helper. | `gpt-5.5` as eval/reference, not live default. | Required signs present; no unknown sign hallucination. |
| Non-English to English | Local model after eval. | `qwen3.5:4b`, fallback `qwen3:4b`, then `qwen3:8b` if quality needs it. | OpenAI/Google/Azure depending on language. | Intent preserved per language fixture. |
| Speech transcription | Local faster-whisper. | None for first pass; this is ASR, not LLM chat. | OpenAI, Chirp 3, Azure/MAI. | WER and urgent-intent preservation. |
| Sign sequence to English | Rule reconstruction. | `qwen3.5:4b` for fluency after sign validation. | `gpt-5.5` for review/eval. | No invented facts/signs. |
| Rights analysis | Template fallback. | `qwen3:8b` or `gpt-oss:20b` if measured. | `gpt-5.5`, Claude comparison later. | Structured schema, disclaimers, generic errors. |
| Rights letter | Template fallback. | `qwen3:8b` or `gpt-oss:20b` if measured. | `gpt-5.5`, Claude comparison later. | Editable draft, factual consistency, review-required. |
| Camera recognition | Manual buttons/assist mode. | No local LLM default. | No cloud default. | Real SASL temporal model and dataset. |
| Avatar production | Deterministic sign library. | No LLM. | No LLM. | Canvas/pose/sign-name tests and Deaf review. |

## Pull Order After Python Is Fixed

Run only after user approves implementation/testing work:

```powershell
ollama pull qwen3.5:4b
ollama pull qwen3:4b
ollama pull qwen3.5:2b
ollama pull qwen3:8b
```

Do not pull `gpt-oss:20b` until the small-model evaluation harness exists. It is a large download and will only be useful if the app can measure latency and quality.

## Why Bigger Is Not Automatically Better

AMANDLA's core correctness is constrained by SASL vocabulary, signing grammar, privacy, and accessibility. A bigger model that writes nicer English but invents sign names is worse than a small model plus deterministic rules. A cloud model that improves rights letters but sends sensitive data without user consent is not a product improvement.

## Sources

- OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model
- OpenAI Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI speech-to-text guide: https://developers.openai.com/api/docs/guides/speech-to-text
- OpenAI data residency guide: https://developers.openai.com/api/docs/guides/your-data#data-residency-controls
- OpenAI gpt-oss announcement: https://openai.com/index/introducing-gpt-oss/
- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Ollama Qwen3: https://ollama.com/library/qwen3
- Ollama Qwen3.6: https://ollama.com/library/qwen3.6
- Ollama Qwen3-VL 4B: https://ollama.com/library/qwen3-vl%3A4b
- Ollama gpt-oss: https://ollama.com/library/gpt-oss
- Qwen3 blog: https://qwenlm.github.io/blog/qwen3/
- Google Gemma 4 docs: https://ai.google.dev/gemma/docs/core
- Google Chirp 3 docs: https://docs.cloud.google.com/speech-to-text/docs/models/chirp-3
- Azure Speech language support: https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support
- Microsoft Build 2026 model announcements: https://blogs.microsoft.com/blog/2026/06/02/microsoft-build-2026-be-yourself-at-work/
- Meta Llama 4 announcement: https://ai.meta.com/blog/llama-4-multimodal-intelligence/
- Mistral Small 4 announcement: https://mistral.ai/news/mistral-small-4/
- DeepSeek V3.2 release: https://api-docs.deepseek.com/news/news251201
- Groq OpenAI compatibility: https://console.groq.com/docs/openai
