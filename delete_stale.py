"""
One-time cleanup script — deletes stale markdown files that cause AI agents
to re-add intentionally deleted code. Run once then delete this script too.
"""
import os
import sys

os.chdir(os.path.dirname(os.path.abspath(__file__)))

STALE_FILES = [
    "APPLICATION_STARTED.md",
    "FINAL_STATUS_REPORT.md",
    "OPERATIONAL_STATUS.md",
    "SETUP_COMPLETE.md",
    "SETUP_VERIFICATION.md",
    "WHAT_WAS_COMPLETED.md",
    "PROJECT_SETUP_SUMMARY.md",
    "START_HERE.md",
    "NEXT_STEPS.md",
    "AGENT_TASKS.md",
    "AGENT_PROMPTS.md",
    "AMANDLA_BLUEPRINT (2).md",
]

deleted = []
missing = []
errors  = []

for filename in STALE_FILES:
    if os.path.exists(filename):
        try:
            os.remove(filename)
            deleted.append(filename)
        except Exception as exc:
            errors.append(f"{filename}: {exc}")
    else:
        missing.append(filename)

sys.stdout.write(f"\nDeleted  ({len(deleted)}):\n")
for f in deleted:
    sys.stdout.write(f"  ✓ {f}\n")

if missing:
    sys.stdout.write(f"\nAlready gone ({len(missing)}):\n")
    for f in missing:
        sys.stdout.write(f"  - {f}\n")

if errors:
    sys.stdout.write(f"\nErrors ({len(errors)}):\n")
    for e in errors:
        sys.stdout.write(f"  ! {e}\n")

sys.stdout.write("\nDone.\n")
sys.stdout.flush()

