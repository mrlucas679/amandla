# Ollama Model Restore And Model Evaluation

Date: 2026-07-05
Status: proposed recovery plan

Earlier research was uncertain about whether Ollama was still present. Current verification shows Ollama is installed and serving, but no models are available:

- `ollama --version` -> `0.30.10`
- `http://localhost:11434/api/tags` -> empty `models` list
- `ollama list` -> no entries

No AI feature should be called working until a model is pulled and evaluated. Backend runtime tests also remain blocked until a real Python install replaces the broken Windows Store shim.

## Restore Checklist

Official Windows install source: https://docs.ollama.com/windows

1. If Ollama is missing on another machine, install Ollama for Windows.
2. Open a new terminal and run:

```powershell
ollama --version
ollama serve
```

3. In another terminal, verify the API and model list:

```powershell
curl http://localhost:11434/api/tags
ollama list
```

4. Pull a candidate base model:

```powershell
ollama pull qwen3.5:4b
```

5. Update `Modelfile` only after evaluation. Current baseline:

```text
FROM qwen2.5:3b
```

6. Create the project model:

```powershell
ollama create amandla -f Modelfile
ollama list
ollama run amandla
```

7. Start the app only after the model appears in `ollama list` and backend Python is working.

## Important Strategy Change

The current `Modelfile` uses one model name, `amandla`, for very different jobs: text-to-SASL support, sign reconstruction, rights analysis, translation, and landmark classification. That is too broad.

After Ollama is restored, evaluate models by task role instead of asking one model to prove everything:

- `english_to_sasl_helper`
- `sasl_to_english_helper`
- `rights_analysis_helper`
- `rights_letter_helper`
- `translation_helper`
- `experimental_landmark_classifier`

The landmark classifier role should not be treated as production. Current HARPS metadata lists generic labels such as `SIGN_00` through `SIGN_20`, so camera sign recognition still needs real SASL data and temporal evaluation.

## Candidate Local Models

Do not pick a model because it is fashionable. Pick it because it passes AMANDLA tests.

| Model | Use Case | Evaluation Need |
|---|---|---|
| `qwen3.5:4b` | First candidate for local multilingual/reasoning balance. | JSON compliance, latency, SA English handling. |
| `qwen3:4b` | Conservative fallback baseline. | Compare against 3.5 for JSON reliability and speed. |
| `qwen3.5:2b` | Low-resource local fallback. | Check whether quality is too weak for SASL/rules support. |
| `qwen3:8b` | Better quality if RAM/GPU allows. | Latency and memory. |
| Gemma E2B/E4B-class local model | Device-friendly comparison candidate if local runtime support exists. | Verify actual local runtime tag/support before standardizing. |
| `gpt-oss:20b` | Strong open-weight candidate if the machine has enough memory. | Measure memory and latency; do not use for live UX if it stalls the app. |
| `llama3.2:3b` | Common lightweight fallback. | Multilingual and instruction reliability. |
| Existing `qwen2.5:3b` | Historical baseline only. | Must compete against newer candidates. |

Large models such as Llama 4, Mistral Small 4, and DeepSeek V3.2-class systems should be treated as hosted/provider research candidates for now, not CPU-only local defaults.

## Evaluation Prompts

### JSON Discipline

Prompt:

```text
Return only JSON:
{"sign":"HELLO","confidence":0.85,"description":"short"}
```

Pass:

- Valid JSON.
- No markdown fences.
- No apology text.
- Confidence numeric.

### Unknown Sign Discipline

Prompt with ambiguous landmarks or empty input.

Pass:

- Returns `{"sign":"UNKNOWN","confidence":0.0,...}`.
- Does not invent a high-confidence sign.

### Known Vocabulary Boundary

Prompt asks for a sign not in the known sign list.

Pass:

- Does not emit unknown library entries.
- Falls back safely.

### Translation Support

Input examples:

- `Hello, how are you?`
- `I need a doctor.`
- `My employer refused an interpreter.`
- `Howzit, I need help now now.`
- `I do not understand.`

Pass:

- Supports rule-first pipeline.
- Does not remove `FINISH`, `WILL`, `CAN`, `MUST`, or other important SASL markers.
- Does not replace deterministic phrase mappings with hallucinated gloss.

### Task Role Separation

Run the same candidate model with role-specific system prompts and score each role separately.

Pass:

- A model can fail one role without being rejected for all roles.
- Rights prompts cannot influence sign-recognition prompts.
- Landmark/sign prompts cannot influence rights-letter output.
- Evaluation reports include role, model tag, prompt version, latency, and validation result.

### Cloud Comparison Baseline

If cloud mode is later approved, compare local models against a cloud reference for selected tasks:

- OpenAI Responses API with Structured Outputs for structured rights and translation evaluation.
- OpenAI speech models, Google Chirp 3, or Azure Speech for speech-language comparison.

Cloud evaluation must use fixture data or explicitly consented samples only.

## Acceptance Metrics

| Metric | Target |
|---|---|
| JSON valid rate | 100% on model contract tests |
| Unknown discipline | 100% safe fallback on ambiguous inputs |
| Known sign boundary | 0 hallucinated sign names |
| Local latency | To be measured on user hardware |
| Translation improvement | Must beat deterministic fallback on a named golden set |
| Memory use | Must not make Electron + FastAPI unusable |
| Role separation | Results are reported per task role |
| Cloud/local delta | Optional cloud mode must show enough quality gain to justify privacy and cost tradeoffs |

## Product Rule

Ollama is a dependency, not a proof of quality. The app should:

- Show a clear missing-Ollama state.
- Show a clear missing-model state.
- Continue with deterministic fallbacks where safe.
- Never claim camera sign recognition is accurate until measured.

## Source Notes

- Ollama Qwen3.5 4B: https://ollama.com/library/qwen3.5%3A4b
- Qwen3 official overview: https://qwenlm.github.io/blog/qwen3/
- Ollama Qwen3 library: https://ollama.com/library/qwen3
- Ollama Qwen3.6: https://ollama.com/library/qwen3.6
- Ollama Qwen3-VL 4B: https://ollama.com/library/qwen3-vl%3A4b
- OpenAI GPT-OSS announcement: https://openai.com/index/introducing-gpt-oss/
- Google Gemma docs: https://ai.google.dev/gemma/docs/core
