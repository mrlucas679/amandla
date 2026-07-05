# AMANDLA Model Evaluation Fixtures Spec

Status: proposed, not implemented
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

This document defines the fixture contracts AMANDLA should use before trusting any local or cloud model. The goal is to make model quality measurable, repeatable, and tied to the application's real communication workflows.

The fixture suite should answer five questions:

1. Does the pipeline preserve meaning?
2. Does it use only valid SASL sign names unless fingerspelling is expected?
3. Does it avoid dropping safety, medical, legal, or rights-critical information?
4. Does it return machine-checkable structures instead of prose when the app needs structure?
5. Does it respect the selected privacy mode: local-only, opt-in cloud, or research evaluation?

## Shared Fixture Rules

Every fixture file should be UTF-8 JSON. Each case must include stable IDs so historical results can be compared across model versions.

Common fields:

```json
{
  "id": "string-stable-kebab-case",
  "group": "string",
  "priority": "critical | high | normal | exploratory",
  "privacy_mode": "local_only | cloud_allowed | synthetic_only",
  "source": "synthetic | consented_sample | public_reference | community_reviewed",
  "review_status": "draft | linguist_reviewed | deaf_reviewer_approved | retired",
  "notes": "short human-readable context"
}
```

Rules:

- Do not include real user conversations unless consent is explicit and documented.
- Do not put secrets, access tokens, phone numbers, ID numbers, or private addresses in fixtures.
- Mark generated examples as `synthetic`; do not pretend they are community-reviewed.
- Keep South African language labels explicit, for example `en-ZA`, `af-ZA`, `zu-ZA`, `xh-ZA`, `st-ZA`, `tn-ZA`, `nso-ZA`, `ts-ZA`, `ve-ZA`, `nr-ZA`, or `ss-ZA`.
- A fixture can be useful before it is perfect, but the `review_status` must tell the truth.

## Proposed Layout

```text
tests/
  golden/
    translation_cases.json
    sign_reconstruction_cases.json
    speech_language_cases.json
    rights_cases.json
    provider_comparison_cases.json
    sign_recognition_dataset_card.json
    dataset_consent_cases.json
```

After the dataset-first pivot, `dataset_consent_cases.json` becomes a required fixture file before any real user signing data is collected.

## Translation Cases

File: `tests/golden/translation_cases.json`

Purpose: evaluate hearing-side text or speech transcript to SASL sign sequence.

Case shape:

```json
{
  "id": "medical-help-001",
  "group": "medical",
  "priority": "critical",
  "privacy_mode": "local_only",
  "source": "synthetic",
  "review_status": "draft",
  "input_language": "en-ZA",
  "input_text": "I need help. My chest hurts.",
  "expected_required_signs": ["HELP", "MY", "CHEST", "HURT"],
  "expected_optional_signs": ["NEED"],
  "expected_forbidden_signs": [],
  "expected_markers": [],
  "allow_fingerspell": false,
  "max_unknown_signs": 0,
  "notes": "Safety-critical phrase; must not drop pain or body location."
}
```

Additional required groups:

| Group | Why It Matters |
|---|---|
| `greeting` | Basic trust-building conversation. |
| `daily` | Ordinary communication, not only emergencies. |
| `medical` | Safety-critical intent must survive. |
| `rights` | Legal/rights assistance language must remain accurate. |
| `modal` | `will`, `must`, and `can` must not be treated as filler. |
| `aspect` | `FINISH` and `WILL` grammar markers must survive where expected. |
| `unknown_word` | Unknown words should fingerspell or use an explicit fallback. |
| `hostile_input` | Sanitisation and size limits must hold. |
| `multilingual` | Local-language and code-switched phrases must be measured, not assumed. |

Sample modal fixture:

```json
{
  "id": "modal-must-001",
  "group": "modal",
  "priority": "critical",
  "privacy_mode": "local_only",
  "source": "synthetic",
  "review_status": "draft",
  "input_language": "en-ZA",
  "input_text": "You must wait here.",
  "expected_required_signs": ["YOU", "MUST", "WAIT", "HERE"],
  "expected_optional_signs": [],
  "expected_forbidden_signs": [],
  "expected_markers": ["MUST"],
  "allow_fingerspell": false,
  "max_unknown_signs": 0,
  "notes": "Protects against incorrectly adding modal verbs to FILLER."
}
```

Pass/fail metrics:

| Metric | Formula | Initial Gate |
|---|---|---:|
| Required sign recall | required signs found / required signs expected | 95%+ |
| Critical required sign recall | critical required signs found / critical required signs expected | 100% |
| Forbidden sign rate | forbidden signs emitted / forbidden signs expected absent | 0 |
| Unknown sign count | output signs not in `signs_library.js` | <= case `max_unknown_signs` |
| Marker preservation | required markers found / required markers expected | 100% for critical cases |
| Sanitisation survival | hostile input does not crash or leak internals | 100% |

## Sign Reconstruction Cases

File: `tests/golden/sign_reconstruction_cases.json`

Purpose: evaluate deaf-side sign sequence to English text.

Case shape:

```json
{
  "id": "signs-to-help-001",
  "group": "medical",
  "priority": "critical",
  "privacy_mode": "local_only",
  "source": "synthetic",
  "review_status": "draft",
  "input_signs": ["ME", "NEED", "HELP"],
  "expected_intents": ["speaker_needs_help"],
  "expected_text_contains": ["help"],
  "forbidden_text_contains": ["fine", "joke", "not"],
  "allow_fluency_variation": true,
  "notes": "English wording can vary, but urgent help intent must remain."
}
```

Pass/fail metrics:

| Metric | Initial Gate |
|---|---:|
| Intent preservation | 95%+ normal, 100% critical |
| Forbidden phrase rate | 0 critical forbidden phrases |
| Empty output rate | 0 on valid sign input |
| Hallucinated fact rate | 0 critical cases |
| Latency | Measure baseline first; do not set target blindly |

## Speech Language Cases

File: `tests/golden/speech_language_cases.json`

Purpose: evaluate speech-to-text providers before claiming language or accent support.

Metadata-only case shape:

```json
{
  "id": "speech-enza-urgent-001",
  "group": "urgent",
  "priority": "critical",
  "privacy_mode": "synthetic_only",
  "source": "consented_sample",
  "review_status": "draft",
  "audio_file": "fixtures/audio/speech-enza-urgent-001.wav",
  "language": "en-ZA",
  "environment": "quiet | noisy_room | outdoor | low_quality_mic",
  "speaker_profile": {
    "accent": "South African English",
    "age_band": "adult",
    "consent_id": "redacted-or-internal-reference"
  },
  "reference_transcript": "I need help now.",
  "expected_intents": ["urgent_help_request"],
  "forbidden_omissions": ["help", "now"],
  "notes": "Audio fixture must not be committed unless consent and storage policy are approved."
}
```

For research planning, the spec can be committed without audio files. Real audio collection needs consent and storage rules first.

Pass/fail metrics:

| Metric | Initial Gate |
|---|---:|
| Word error rate | Baseline by language and provider |
| Critical omission rate | 0 for safety, medical, rights-critical terms |
| Intent preservation | 95%+ normal, 100% critical |
| Language mis-detection rate | Baseline first |
| Median latency | Baseline first |
| Cloud consent compliance | 100% |

## Rights Cases

File: `tests/golden/rights_cases.json`

Purpose: evaluate rights analysis and letter generation as structured assistance, not legal advice.

Case shape:

```json
{
  "id": "rights-access-transport-001",
  "group": "accessibility",
  "priority": "high",
  "privacy_mode": "cloud_allowed",
  "source": "synthetic",
  "review_status": "draft",
  "user_story": "A taxi driver refused to take me because I use sign language and needed extra time to explain my destination.",
  "expected_issue_tags": ["accessibility", "public_transport", "discrimination"],
  "expected_required_sections": ["summary", "possible_rights", "suggested_next_steps", "review_disclaimer"],
  "forbidden_claims": ["guaranteed legal outcome", "attorney-client relationship"],
  "letter_required_fields": ["recipient", "sender", "incident_summary", "requested_remedy"],
  "notes": "Draft output must encourage review by a qualified person or rights organisation."
}
```

Pass/fail metrics:

| Metric | Initial Gate |
|---|---:|
| Valid schema rate | 100% |
| Required section rate | 100% |
| Forbidden claim rate | 0 |
| Factual consistency | 95%+ on synthetic cases |
| Review disclaimer presence | 100% |
| Generic user-facing error on failure | 100% |

## Provider Comparison Cases

File: `tests/golden/provider_comparison_cases.json`

Purpose: run the same case through local and opt-in cloud providers.

Case shape:

```json
{
  "id": "provider-sasl-001",
  "group": "translation",
  "priority": "high",
  "privacy_mode": "cloud_allowed",
  "source": "synthetic",
  "review_status": "draft",
  "task": "english_to_sasl",
  "input": {
    "language": "en-ZA",
    "text": "Tomorrow I will go to the clinic."
  },
  "expected": {
    "required_signs": ["TOMORROW", "I", "WILL", "GO", "CLINIC"],
    "forbidden_signs": [],
    "schema": "sign_sequence_v1"
  },
  "providers": ["rules", "ollama:qwen3.5:4b", "openai:gpt-5.5"],
  "notes": "Cloud provider is comparison only; live default remains local/rules unless product mode permits cloud."
}
```

Comparison report fields:

```json
{
  "case_id": "provider-sasl-001",
  "provider": "ollama:qwen3.5:4b",
  "model_version": "unknown",
  "privacy_mode": "cloud_allowed",
  "valid_schema": true,
  "score": 0.94,
  "latency_ms": 1234,
  "errors": [],
  "raw_output_path": "reports/eval/raw/provider-sasl-001-qwen3-4b.json"
}
```

## Sign Recognition Dataset Card

File: `tests/golden/sign_recognition_dataset_card.json`

Purpose: prevent camera-recognition claims from outrunning the evidence.

Card shape:

```json
{
  "dataset_id": "amandla-sasl-camera-eval-v0",
  "status": "not_collected",
  "sign_language": "SASL",
  "labels": [],
  "num_signers": 0,
  "num_clips": 0,
  "consent_model": "not_defined",
  "annotation_process": "not_defined",
  "reviewers": [],
  "splits": {
    "train": "not_defined",
    "validation": "not_defined",
    "test": "not_defined",
    "unseen_signer_test": "required"
  },
  "required_bias_checks": [
    "handedness",
    "skin_tone_lighting",
    "camera_angle",
    "signer_age_band",
    "unseen_signer_split",
    "unknown_sign_rejection"
  ],
  "known_limitations": [
    "No production SASL camera-recognition claim until this card is complete."
  ]
}
```

Camera recognition gates:

| Gate | Requirement |
|---|---|
| Label provenance | Every class maps to a validated SASL sign label. |
| Consent | Every clip has documented consent. |
| Split integrity | No signer leakage into unseen-signer test. |
| Unknown rejection | The model can reject signs outside its vocabulary. |
| Community review | Deaf/SASL reviewers assess meaningfulness, not only accuracy. |

## Result Summary Contract

Every evaluation run should produce a summary that is easy to compare over time.

```json
{
  "run_id": "2026-07-05T05-31-00+02-00",
  "branch": "codex/modernization-research",
  "commit": "unknown",
  "machine": "MSI Thin 15 B13UC",
  "mode": "local_only",
  "providers": ["rules", "ollama:qwen3.5:4b"],
  "summary": {
    "cases_total": 0,
    "cases_passed": 0,
    "cases_failed": 0,
    "cases_blocked": 0
  },
  "blocking_conditions": [
    "Python unavailable",
    "Ollama has no pulled models"
  ],
  "critical_failures": [],
  "next_action": "Restore Python, then run static and golden fixture checks."
}
```

## Implementation Notes

- Start with synthetic fixtures so the harness exists before collecting real data.
- Keep model raw outputs in ignored `reports/eval/raw/` files if they may contain sensitive text.
- Validate output schemas before scoring semantic quality.
- Compare against deterministic rules first; a model should improve the app only where rules are weak.
- Treat every failure as useful research data, not an embarrassment to hide.
