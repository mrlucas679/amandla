"""
AMANDLA — Signs Library Merge Tool
====================================
Merges real keyframe data from convert_signs.py / record_signs.py into
signs_library_generated.js without modifying the hand-crafted signs_library.js.

Strategy:
    1. Read input JSON files (produced by convert_signs.py or record_signs.py).
    2. Build a SIGN_OVERRIDES JS block containing only the new keyframe data.
    3. Write signs_library_generated.js = <script src="signs_library.js"> + overrides.

The generated file appends a SIGN_OVERRIDES object that Object.assign()s new
fields (frames, duration, nmm) onto existing sign objects at runtime. Signs
not covered by real data continue to use their synthetic SLERP poses unchanged.

Usage:
    # Merge converted .pkl data
    python scripts/merge_sign_data.py \\
        --source signs_library.js \\
        --data poses.json \\
        --output signs_library_generated.js

    # Merge multiple recorded sign JSONs
    python scripts/merge_sign_data.py \\
        --source signs_library.js \\
        --data data/recorded_signs/*.json \\
        --output signs_library_generated.js

    # Print coverage table without writing output
    python scripts/merge_sign_data.py --data poses.json --report

    # Show which HTML files need to be updated to use the generated library
    python scripts/merge_sign_data.py --data poses.json --output signs_library_generated.js --check-html src/
"""

import json
import glob
import argparse
import sys
from datetime import datetime
from pathlib import Path


# ─────────────────────────────────────────────────────────────────────────────
# SIGN NAME EXTRACTION — read SIGN_LIBRARY keys from the source JS
# ─────────────────────────────────────────────────────────────────────────────

def read_sign_names_from_js(js_path):
    """
    Extract all sign names (keys) defined in SIGN_LIBRARY by scanning
    the source JS for the pattern  'WORD': sign(  or  'WORD': signWithFrames(
    """
    import re
    names = set()
    pattern = re.compile(r"'([A-Z][A-Z0-9 _\-]*)'\s*:\s*sign")
    with open(js_path, encoding='utf-8') as fh:
        for line in fh:
            m = pattern.search(line)
            if m:
                names.add(m.group(1))
    return names


# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

def load_sign_data(data_paths):
    """
    Load sign keyframe data from one or more JSON files.
    Supports two formats:
      - convert_signs.py output:   {'signs': {'WORD': {'frames':..., 'duration':...}}}
      - record_signs.py output:    {'word': 'WORD', 'frames': [...], 'duration': ...}

    Returns: dict mapping sign_name (uppercase) → {'frames': [...], 'duration': int}
    """
    merged = {}

    for path in data_paths:
        path = Path(path)
        if not path.exists():
            print(f"  WARNING: File not found — {path}")
            continue

        with open(path, encoding='utf-8') as fh:
            data = json.load(fh)

        # Batch format (convert_signs.py)
        if 'signs' in data:
            for name, sign_data in data['signs'].items():
                if 'frames' in sign_data and sign_data['frames']:
                    merged[name.upper()] = {
                        'frames':   sign_data['frames'],
                        'duration': sign_data.get('duration', 400),
                        'source':   sign_data.get('source', str(path.name)),
                    }
            print(f"  Loaded {len(data['signs'])} signs from {path.name}")

        # Single-sign format (record_signs.py)
        elif 'word' in data and 'frames' in data:
            name = data['word'].upper()
            if data['frames']:
                # If this word was already loaded, prefer the newer file (later in list)
                merged[name] = {
                    'frames':   data['frames'],
                    'duration': data.get('duration', 400),
                    'source':   str(path.name),
                }
            print(f"  Loaded '{name}' from {path.name}")

        else:
            print(f"  WARNING: Unrecognised format in {path.name} — skipping")

    return merged


# ─────────────────────────────────────────────────────────────────────────────
# JS GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _frames_to_js(frames):
    """Serialise a keyframe array to a compact JS literal (not pretty-printed)."""
    lines = ['[']
    for f in frames:
        t = f['t']
        R = f['R']
        L = f['L']

        def arm_to_js(arm):
            sh = arm['sh']
            el = arm['el']
            wr = arm['wr']
            hand = arm.get('hand', None)
            hand_js = json.dumps(hand) if hand else 'null'
            return (
                f"{{sh:{{x:{sh['x']},y:{sh['y']},z:{sh['z']}}},"
                f"el:{{x:{el['x']},y:{el['y']},z:{el['z']}}},"
                f"wr:{{x:{wr['x']},y:{wr['y']},z:{wr['z']}}},"
                f"hand:{hand_js}}}"
            )

        lines.append(f"  {{t:{t},R:{arm_to_js(R)},L:{arm_to_js(L)}}},")
    lines.append(']')
    return '\n'.join(lines)


def build_overrides_block(sign_data):
    """
    Build the SIGN_OVERRIDES JavaScript block string.
    sign_data: dict of name → {frames, duration, source}
    """
    lines = [
        '',
        '// ═══════════════════════════════════════════════════════════════════',
        '// AUTO-GENERATED SIGN OVERRIDES',
        f'// Generated by scripts/merge_sign_data.py on {datetime.now().isoformat(timespec="seconds")}',
        '// DO NOT EDIT — regenerate with: python scripts/merge_sign_data.py',
        '// ═══════════════════════════════════════════════════════════════════',
        'const SIGN_OVERRIDES = {',
    ]

    for name, data in sorted(sign_data.items()):
        frames_js = _frames_to_js(data['frames'])
        dur       = data['duration']
        src       = data.get('source', 'unknown')
        lines.append(f"  // source: {src}")
        lines.append(f"  '{name}': {{")
        lines.append(f"    duration: {dur},")
        lines.append(f"    frames: {frames_js},")
        lines.append("    nmm: null,")
        lines.append("  }},")  # noqa: the double-brace is intentional JS literal

    lines += [
        '};',
        '',
        '// Apply overrides at load time',
        '(function applySignOverrides() {',
        '  if (typeof SIGN_LIBRARY === "undefined") {',
        '    console.warn("[AMANDLA] SIGN_LIBRARY not found — overrides skipped");',
        '    return;',
        '  }',
        '  var applied = 0;',
        '  Object.keys(SIGN_OVERRIDES).forEach(function(name) {',
        '    if (!SIGN_LIBRARY[name]) return;',
        '    var override = SIGN_OVERRIDES[name];',
        '    SIGN_LIBRARY[name].duration = override.duration;',
        '    SIGN_LIBRARY[name].frames   = override.frames;',
        '    SIGN_LIBRARY[name].nmm      = override.nmm;',
        '    // Pre-bake quaternions for the keyframe engine',
        '    if (typeof prebakeFrameQuats === "function") {',
        '      prebakeFrameQuats(SIGN_LIBRARY[name].frames);',
        '    } else if (window.AMANDLA_SIGNS && window.AMANDLA_SIGNS.prebakeFrameQuats) {',
        '      window.AMANDLA_SIGNS.prebakeFrameQuats(SIGN_LIBRARY[name].frames);',
        '    }',
        '    applied++;',
        '  });',
        '  console.log("[AMANDLA] Applied " + applied + " real-data sign override(s).");',
        '})();',
        '',
    ]

    return '\n'.join(lines)


def write_generated_library(source_js_path, overrides_block, output_path):
    """
    Write the generated library: re-export everything from source_js,
    then append the overrides block.

    For browser usage the generated file simply includes the source via a
    <script> tag comment at the top (the HTML must load source_js first,
    then this file). For Node.js / module usage a require() is emitted.
    """
    source_name = Path(source_js_path).name

    header = f"""\
/**
 * signs_library_generated.js
 * AUTO-GENERATED — DO NOT EDIT BY HAND.
 * Generated:  {datetime.now().isoformat(timespec='seconds')}
 * Source:     {source_name}
 * Generator:  scripts/merge_sign_data.py
 *
 * BROWSER USAGE:
 *   Load signs_library.js BEFORE this file in your HTML:
 *     <script src="{source_name}"></script>
 *     <script src="signs_library_generated.js"></script>
 *
 * NODE USAGE:
 *   require('./{source_name}');
 *   require('./signs_library_generated.js');
 */

'use strict';
"""

    with open(output_path, 'w', encoding='utf-8') as fh:
        fh.write(header)
        fh.write(overrides_block)

    print(f"\nWritten: {output_path}")


# ─────────────────────────────────────────────────────────────────────────────
# REPORTING
# ─────────────────────────────────────────────────────────────────────────────

def print_coverage_report(all_sign_names, real_data, source_js_path=None):
    """Print a table showing which signs have real data vs remain synthetic."""
    if source_js_path:
        lib_names = read_sign_names_from_js(source_js_path)
    else:
        lib_names = set()

    total_lib   = len(lib_names) if lib_names else '?'
    total_real  = len(real_data)
    total_synth = (len(lib_names) - total_real) if lib_names else '?'

    print(f"\n{'─'*55}")
    print("  COVERAGE REPORT")
    print(f"{'─'*55}")
    print(f"  Library signs:   {total_lib}")
    print(f"  Real-data signs: {total_real}")
    print(f"  Still synthetic: {total_synth}")
    print(f"{'─'*55}")

    if real_data:
        print(f"\n  REAL DATA ({total_real} signs):")
        for name, data in sorted(real_data.items()):
            n_frames = len(data['frames'])
            dur      = data['duration']
            src      = data.get('source', 'unknown')
            print(f"    ✓ {name:<20} {n_frames:>2} keyframes  {dur:>5}ms  [{src}]")

    if lib_names:
        synthetic = sorted(lib_names - set(real_data.keys()))
        if synthetic:
            print(f"\n  SYNTHETIC SLERP ({len(synthetic)} signs):")
            # Print in columns of 5
            for i in range(0, len(synthetic), 5):
                chunk = synthetic[i:i+5]
                print('    ' + '  '.join(f"{n:<20}" for n in chunk))

    print(f"{'─'*55}\n")


def find_html_files(src_dir, current_lib='signs_library.js'):
    """Find HTML files in src_dir that still load the old library name."""
    html_files = []
    for html in Path(src_dir).rglob('*.html'):
        content = html.read_text(encoding='utf-8', errors='ignore')
        if current_lib in content:
            html_files.append(html)
    return html_files


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='AMANDLA Signs Library Merge Tool'
    )
    parser.add_argument(
        '--source', default='signs_library.js',
        help='Path to the hand-crafted source library (default: signs_library.js)',
    )
    parser.add_argument(
        '--data', nargs='+', required=True,
        help='One or more JSON data files from convert_signs.py or record_signs.py. '
             'Glob patterns are supported (e.g. data/recorded_signs/*.json).',
    )
    parser.add_argument(
        '--output', default='signs_library_generated.js',
        help='Output path for the generated library (default: signs_library_generated.js)',
    )
    parser.add_argument(
        '--report', action='store_true',
        help='Print coverage table and exit without writing output',
    )
    parser.add_argument(
        '--check-html', metavar='SRC_DIR',
        help='Scan a directory for HTML files that still load signs_library.js '
             'and should be updated to load signs_library_generated.js',
    )
    args = parser.parse_args()

    # Expand globs in --data arguments
    expanded_paths = []
    for pattern in args.data:
        matched = glob.glob(pattern, recursive=True)
        if matched:
            expanded_paths.extend(matched)
        else:
            expanded_paths.append(pattern)  # keep as-is (will warn if missing)

    if not expanded_paths:
        sys.exit("ERROR: No data files found. Check your --data argument.")

    print("\nAMANDLA Signs Library Merge Tool")
    print(f"Source:  {args.source}")
    print(f"Data:    {len(expanded_paths)} file(s)")
    print(f"Output:  {args.output}")

    sign_data = load_sign_data(expanded_paths)

    if not sign_data:
        sys.exit("ERROR: No valid sign data found in the provided files.")

    print_coverage_report(set(sign_data.keys()), sign_data,
                          source_js_path=args.source if Path(args.source).exists() else None)

    if args.report:
        sys.exit(0)

    overrides = build_overrides_block(sign_data)
    write_generated_library(args.source, overrides, args.output)

    if args.check_html:
        html_files = find_html_files(args.check_html)
        if html_files:
            print("\nHTML files to update (replace signs_library.js → signs_library_generated.js):")
            for f in html_files:
                print(f"  {f}")
        else:
            print(f"\nNo HTML files found still referencing signs_library.js in {args.check_html}")

    print("Done. Load signs_library.js BEFORE signs_library_generated.js in HTML.")
