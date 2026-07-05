# AMANDLA Current AI And Sign Research Addendum

Status: current evidence addendum
Date: 2026-07-05
Branch: `codex/modernization-research`

## Why This Addendum Exists

The first AMANDLA model strategy correctly moved away from the old hackathon `qwen2.5:3b` assumption, but the model market changed again. A final research pass found newer local Ollama candidates and additional 2026 sign-language papers that should be reflected before calling the research complete.

This addendum originally superseded `qwen3:4b` with `qwen3.5:4b` as the first local benchmark candidate. The later dataset-first pivot in `dataset-first-sasl-foundation-strategy.md` supersedes that again: small local models are now fallback/benchmark tools only, not the strategic center of AMANDLA.

## Updated Local Model Recommendation

Optional local pull order after Python is fixed, the evaluator exists, and the user approves benchmark work:

```powershell
ollama pull qwen3.5:4b
ollama pull qwen3:4b
ollama pull qwen3.5:2b
ollama pull qwen3:8b
```

Do not pull every model casually. Pull the next model only when the previous one has been measured.

| Candidate | Current Evidence | AMANDLA Role | Decision |
|---|---|---|---|
| `qwen3.5:4b` | Ollama lists a 4.66B, 3.4 GB Apache-licensed model with text, vision, tools, thinking tags, multimodal training, efficient hybrid architecture, and expanded language coverage. | Local fallback/benchmark helper only. | Optional benchmark, not product core. |
| `qwen3:4b` | Ollama lists a smaller Qwen3 4B path with multilingual and tool-use claims. | Conservative fallback and comparison baseline. | Try if 3.5 is unstable or too slow. |
| `qwen3.5:2b` | Same model family at a smaller size. | Low-latency fallback if 4B class models are too slow. | Try only if 4B latency fails. |
| `qwen3:8b` | Larger text model in the older Qwen3 family. | Quality comparison if 4B is fast but weak. | Try after 4B class models. |
| `qwen3-vl:4b` | Ollama lists a 4.44B, 3.3 GB vision-language model with visual reasoning/OCR claims. | Optional research for UI screenshots or document/image understanding. | Do not use for production sign recognition. |
| `qwen3.6:27b` / `qwen3.6:35b` | Ollama lists larger 17 GB/24 GB models focused on coding and agentic workflows. | Developer/research comparison, not live communication. | Too heavy for first local path. |
| `gpt-oss:20b` | OpenAI/Ollama sources position it as a local open-weight reasoning model around 14 GB download / roughly 16 GB memory class. | Stretch local reasoning comparison. | Later only. |

## Why `qwen3.5:4b` Was Better Than Older Qwen3 For Local Benchmarking

It is still small enough for this laptop's RAM, but the current Ollama page shows a newer architecture, multimodal support, tool/reasoning tags, and wider language coverage than the older Qwen3 recommendation. AMANDLA should not assume the newer model is good enough for production. It is only a local benchmark/fallback candidate.

The acceptance rule does not change:

- Valid JSON first.
- Known sign names only.
- No dropped `MUST`, `WILL`, `CAN`, `FINISH`, medical, safety, or rights-critical terms.
- Better than deterministic rules on the exact weakness being tested.
- Local latency acceptable on CPU.
- Cloud disabled unless the mode permits it.

## Updated Cloud Recommendation

OpenAI `gpt-5.5` remains the first cloud text baseline because official docs present it as the latest production model family and emphasize fresh baselines, Responses API workflows, prompt caching, structured outputs, and lower reasoning-token use than prior GPT-5.x models.

Cloud speech still needs comparison, not faith:

- OpenAI speech models for direct integration and realtime options.
- Google Chirp 3 for multilingual ASR comparison.
- Azure Speech / MAI Transcribe where South African language and region support are acceptable.

No cloud provider should become the always-on default for sensitive communication or rights content without explicit product mode, consent, and privacy review.

## 2026 Sign-Language Research Updates

Recent papers strengthen the earlier decision: sign recognition must be data/community-led, not generic VLM-led.

| Research | What It Adds For AMANDLA |
|---|---|
| Sign-Language Datasets at Scale (2026) | Dataset documentation is central. AMANDLA needs a datasheet with consent, handedness, signer split, annotation, and bias fields. |
| Sign Language Recognition and Translation for Low-Resource Languages (2026) | Low-resource sign languages need tailored pathways; SASL cannot borrow ASL success claims directly. |
| SignDATA (2026) | Preprocessing and privacy are part of the research pipeline, especially because sign video is biometric data. |
| Bootstrapping Sign Language Annotations (2026) | Pseudo-annotation can help later, but it still requires human interpreter validation and does not replace SASL review. |
| Gloss-Free Sign Language Translation (2026) | Public SLT progress must be evaluated carefully because datasets, annotation formats, and metrics differ. |
| DHH access to intelligent personal assistants (2026) | LLM-assisted touch/options can help DHH interaction, supporting AMANDLA's assist phrases and quick-sign UX as reliable non-camera paths. |

## Updated Product Implication

AMANDLA should have three communication confidence tiers:

| Tier | Feature | Product Claim |
|---|---|---|
| Tier 1 | Typed text, manual signs, assist phrases, deterministic SASL mapping, avatar playback | Core communication path once protocol/runtime defects are fixed and tests pass. |
| Tier 2 | Local LLM helper, local speech, rights drafts | Helpful if fixture evaluation passes; user-facing output remains validated and editable. |
| Tier 3 | Camera sign recognition, cloud speech/model quality, future dataset training | Research/opt-in only until community-reviewed data and privacy gates exist. |

## Sources

- OpenAI GPT-5.5 guide: https://developers.openai.com/api/docs/guides/latest-model
- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Ollama Qwen3 4B: https://ollama.com/library/qwen3%3A4b
- Ollama Qwen3.6: https://ollama.com/library/qwen3.6
- Ollama Qwen3-VL 4B: https://ollama.com/library/qwen3-vl%3A4b
- Sign-Language Datasets at Scale: https://arxiv.org/html/2606.19352v1
- Sign Language Recognition and Translation for Low-Resource Languages: https://arxiv.org/html/2605.12096v1
- SignDATA: https://arxiv.org/html/2604.20357v1
- Bootstrapping Sign Language Annotations: https://arxiv.org/html/2604.07606v1
- Gloss-Free Sign Language Translation: https://arxiv.org/html/2603.13240v1
- DHH access to intelligent personal assistants: https://arxiv.org/html/2601.15209v2
