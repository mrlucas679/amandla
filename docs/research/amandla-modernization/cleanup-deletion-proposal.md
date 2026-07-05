# Cleanup And Deletion Proposal

Date: 2026-07-05
Status: proposal only - no files deleted

The goal is to remove noise without losing evidence. This proposal separates safe deletion candidates from files that need review, provenance, or migration first.

## Rules Before Deleting

1. Do not delete anything from Claude's active checkout.
2. Delete only on the isolated research/implementation branch after approval.
3. Before deleting any directory, verify its absolute path.
4. Do not delete generated data if the user wants to preserve the current conversation history.
5. Do not delete model/checkpoint files until their provenance and evaluation status are documented.

## Delete After Approval

These items have strong evidence for removal from the active source tree.

| Path | Evidence | Proposed Action |
|---|---|---|
| `archive/` | All 12 files are listed by `CLAUDE.md` as stale and their first line says archived/do not use. | Delete from active repo or move to external historical storage. |
| `amandla_sasl_transformer2/` | `amandla_sasl_transformer2/ARCHIVED.md` explicitly says the entire directory can be safely deleted. Active code imports root `sasl_transformer/`, not this duplicate. | Delete directory after one final import/link scan. |
| `SASL DOCUMEENTS/Ghaziasgar_MSC_2010 (1).pdf` | SHA-256 matches `SASL DOCUMEENTS/Ghaziasgar_MSC_2010.pdf`: `7D305494E0AA099BBE4EC8E394705A04C0469BC7E284B02655AF2B14C9EB4FF6`. | Delete duplicate copy, keep one. |
| `data/conversations.db-shm` | SQLite runtime sidecar file. | Remove from Git; add ignore rule for SQLite sidecars. |
| `data/conversations.db-wal` | SQLite runtime sidecar file. | Remove from Git; add ignore rule for SQLite sidecars. |

## Delete Or Regenerate After User Decision

These are likely noise, but may contain user/session data or useful seed material.

| Path | Evidence | Decision Needed |
|---|---|---|
| `data/conversations.db` | Runtime SQLite database is tracked; AGENTS says it is auto-created and "Never (auto)" to edit. | Ask whether current local conversation history should be preserved/exported before deletion from Git. |
| `data/sign_library.json` | Structured sign data may be useful as seed data. | Keep if it is canonical/generated deterministically; otherwise document generator and source. |
| `delete_stale.py` | Script exists to remove stale docs, but archive already exists. | Keep only if we want repeatable cleanup; otherwise delete after cleanup lands. |

## Quarantine / Review Before Deleting

These are large or ambiguous. Do not delete until their role is clear.

| Path | Evidence | Proposed Review |
|---|---|---|
| `ASL-Sensor-Dataglove-Dataset/` | 1000 tracked CSV files, about 281.55 MB. It is ASL glove-sensor data, not SASL reference signing. | Move to `external-datasets/` or remove from app repo if not used by evaluated model training. |
| `backend/harps_model/model.pth` | HARPS model checkpoint is loaded by `backend/services/harps_recognizer.py`, but provenance/eval is unclear. | Keep temporarily; add model card before trusting it. |
| `backend/harps_model/meta.json`, `scaler.json`, `convergence.png` | Model support artifacts. | Keep with model card or regenerate from a documented training run. |
| `SASL DOCUMEENTS/` | About 87.75 MB of source research. Some material is directly relevant. Folder name is misspelled and mixed. | Rename/move to `docs/research/sasl-sources/` after extracting metadata. |
| `assets/js/three.min.js`, `assets/js/GLTFLoader.js` | Vendored JS supports offline Electron today, but React/Vite would package Three via npm. | Keep until React/Vite build owns avatar bundling. |

## Keep

| Path | Reason |
|---|---|
| `CLAUDE.md` | Current rule file until superseded. |
| `AGENTS.md` | Current agent guide and constraints. |
| `sasl_transformer/` | Active transformer package imported by backend/tests. |
| `signs_library.js` | Active sign library until replaced by typed/generated sign data. |
| `Modelfile` | Required to recreate local Ollama model, though the base model must be reevaluated. |
| `SASL DOCUMEENTS/AMANDLA_Research_Synthesis.md` | Relevant synthesis for avatar/sign-language direction. |
| `SASL DOCUMEENTS/SignON_D5.2_A-Virtual-Character_v1.0.pdf` | Relevant sign-avatar research. |
| `SASL DOCUMEENTS/Einsteinhands dictionary Inside pages_lowres.pdf` | Sign dictionary/source material. |

## Proposed Cleanup PR Shape

Do this as a dedicated cleanup PR, separate from functional fixes:

1. Update `.gitignore` for SQLite runtime files:

```gitignore
data/*.db
data/*.db-shm
data/*.db-wal
!data/sign_library.json
```

2. Remove approved archived/duplicate files.
3. Update `README.md` and `QUICKSTART.md` so they no longer link stale docs.
4. Add a short `docs/archive/README.md` or `docs/history.md` only if historical context must remain in repo.
5. Run `rg` to confirm no active file references deleted docs.

## Safe Deletion Commands After Approval

These are examples only. Run them from `C:\Users\Admin\amandla-desktop-codex-research` after explicit approval and after verifying the current branch.

```powershell
$repo = Resolve-Path .
$targets = @(
  "archive",
  "amandla_sasl_transformer2",
  "SASL DOCUMEENTS\Ghaziasgar_MSC_2010 (1).pdf",
  "data\conversations.db-shm",
  "data\conversations.db-wal"
)

foreach ($target in $targets) {
  $resolved = Resolve-Path -LiteralPath $target
  if (-not $resolved.Path.StartsWith($repo.Path)) {
    throw "Refusing to delete outside repo: $resolved"
  }
  Remove-Item -LiteralPath $resolved.Path -Recurse -Force
}
```

