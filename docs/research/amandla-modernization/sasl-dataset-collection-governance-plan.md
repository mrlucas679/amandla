# AMANDLA SASL Dataset Collection And Governance Plan

Status: proposed research/data plan, not implemented
Date: 2026-07-05
Branch: `codex/modernization-research`

## Purpose

AMANDLA's long-term translation quality should come from a consent-based South African Sign Language dataset and a specialized multimodal SASL model. This document defines the minimum data and governance plan before the app starts collecting real signing data.

## Core Principle

The dataset is not exhaust. It is a research asset involving people, language, identity, disability, and biometric video.

Every sample must be:

- Consented.
- Purpose-limited.
- Reviewable.
- Withdrawable where feasible.
- Separated from source control.
- Auditable from raw capture to model training split.

## Collection Modes

| Mode | Use | Data Status |
|---|---|---|
| `practice_only` | User tries signs without contributing data. | Not stored beyond local session unless user opts in. |
| `consented_research` | User explicitly contributes to SASL dataset. | Stored with consent ID and governance metadata. |
| `review_session` | Deaf/SASL reviewer annotates or validates samples. | Stored as annotation event. |
| `synthetic_fixture` | Generated or scripted test case. | Clearly labeled synthetic, never treated as real signing data. |

## Minimum Consent Flow

Before collecting real video or landmarks:

1. Explain what will be collected.
2. Explain why it is collected.
3. Explain whether it may train future models.
4. Explain who can review it.
5. Explain how long it may be retained.
6. Explain withdrawal limits.
7. Ask for explicit opt-in.
8. Store a consent record before storing the sample.

No consent means no dataset contribution.

## Dataset Record Schema

Proposed metadata shape:

```json
{
  "sample_id": "sasl-sample-000001",
  "consent_id": "consent-000001",
  "collection_mode": "consented_research",
  "sign_language": "SASL",
  "task_context": "clinic",
  "prompt_text": "I need help with my medication.",
  "video_uri": "secure://raw/sasl-sample-000001.mp4",
  "pose_uri": "secure://pose/sasl-sample-000001.json",
  "facial_landmarks_uri": "secure://face/sasl-sample-000001.json",
  "audio_uri": null,
  "gloss_annotation": null,
  "english_translation": null,
  "review_status": "captured",
  "review_events": [],
  "participant_profile": {
    "age_band": "adult",
    "handedness": "right",
    "deaf_or_hard_of_hearing": "prefer_not_to_say",
    "region": "not_public",
    "primary_sasl_background": "not_public"
  },
  "capture_conditions": {
    "device": "unknown",
    "camera_resolution": "unknown",
    "lighting": "indoor",
    "background": "natural",
    "distance_band": "near"
  },
  "safety_domain": ["medical"],
  "split": "unassigned",
  "created_at": "2026-07-05T00:00:00+02:00"
}
```

## Annotation Workflow

| Stage | Actor | Output |
|---|---|---|
| Capture | User/contributor | Raw sample and consent metadata. |
| Preprocess | System | Pose, face, hand, and body landmarks where consented. |
| Model suggestion | Cloud multimodal foundation model | Draft gloss, segmentation, quality flags, possible English translation. |
| Human annotation | Trained annotator | Corrected gloss/translation and segment boundaries. |
| Deaf/SASL review | Deaf/SASL reviewer | Approval, correction, or rejection. |
| Dataset QA | Research lead | Split assignment, bias checks, leakage checks. |
| Training export | Research pipeline | Versioned dataset manifest, not raw app database. |

Cloud model suggestions are never ground truth. They are draft assistance.

## Quality Gates

Samples should be excluded or flagged when:

- Consent is missing or invalid.
- Face/hands are not visible enough for the task.
- The target meaning is unclear.
- Prompt and signing do not match.
- Reviewers disagree without resolution.
- The same signer leaks into an unseen-signer test split.
- The sample contains private third-party information.
- The sample belongs to a sensitive domain but lacks extra review.

## Required Splits

| Split | Purpose |
|---|---|
| `train` | Model learning. |
| `validation` | Hyperparameter and prompt/model selection. |
| `test` | Held-out final evaluation. |
| `unseen_signer_test` | Measures generalization to people not seen in training. |
| `critical_domain_test` | Medical, rights, emergency, and public-service phrases. |

The unseen-signer split is non-negotiable. A model that only works for seen signers is not product-ready.

## Privacy And Storage Rules

- Do not commit raw video, audio, consent records, or real landmarks to Git.
- Store sensitive media outside the repo in an encrypted or access-controlled store.
- Keep source control fixtures synthetic unless explicit publication consent exists.
- Keep audit logs for annotation changes.
- Redact third-party personal information from prompts and transcripts.
- Use derived landmarks for some experiments when raw video is not needed.
- Treat sign video as biometric and culturally sensitive data.

## App Changes Needed Later

Future app features:

- Dataset contribution consent screen.
- Clear "practice only" versus "contribute to research" mode.
- Local preview and deletion before upload.
- Contributor metadata form with minimal, optional demographic fields.
- Secure upload endpoint.
- Reviewer dashboard.
- Annotation status tracking.
- Export tool for versioned dataset manifests.

These are not Phase 1 rescue features. They belong after runtime/protocol/eval stability.

## Model Training Roadmap

| Milestone | Requirement |
|---|---|
| Dataset v0 | Synthetic fixtures and a small consented pilot. |
| Dataset v1 | Diverse signers, contexts, review workflow, unseen-signer split. |
| Baseline model | Supervised temporal model trained on landmarks/video with held-out signers. |
| Foundation-assisted annotation | Cloud model accelerates segmentation and draft labels, humans approve. |
| AMANDLA SASL model v1 | Multimodal model trained on AMANDLA data; restricted beta only. |
| Production candidate | Meets critical-domain gates, latency gates, signer-generalization gates, and community review. |

## Success Metrics

| Metric | Why |
|---|---|
| Consent completeness | No sample without valid consent. |
| Annotation agreement | Measures label quality. |
| Unseen-signer accuracy | Prevents overfitting to known contributors. |
| Critical omission rate | Protects medical, rights, and emergency contexts. |
| Unknown/rejection quality | Model should say uncertain instead of guessing. |
| Latency | Real-time communication needs bounded response time. |
| Community review score | Accuracy alone is not enough. |

## Strategic Implication

The dataset is the product moat.

AMANDLA should use cloud AI to accelerate engineering and annotation, but the long-term defensible system is a specialized SASL model trained on high-quality, consented, reviewed South African data.

