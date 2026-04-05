"""
AMANDLA — SignAvatars .pkl → Three.js keyframe converter  v2.0
==============================================================
Run this AFTER downloading the Word-level ASL subset from SignAvatars.

Usage:
    python convert_signs.py --input /path/to/word_level_asl/ --output poses.json
    python convert_signs.py --input /path/to/word_level_asl/ --output poses.json --keyframes 10
    python convert_signs.py --inspect /path/to/sign.pkl

v2.0 changes from v1.0
-----------------------
- Extracts ALL frames instead of the single peak frame.
- Uses angular-displacement keyframe selection to reduce 30fps → 8–12 keyframes.
- Output now contains per-sign `frames` and `duration` arrays compatible with
  the `signWithFrames()` factory in signs_library.js v3+.
- Legacy single-frame output is available via --legacy flag.

Each .pkl contains a dict with keys:
    poses       : (N_frames, 165) SMPL-X pose params
                  [0:3]    = global orient
                  [3:66]   = body pose (21 joints × 3 axis-angle)
                  [66:111] = left hand (15 joints × 3)
                  [111:156]= right hand (15 joints × 3)
    betas       : (10,) shape params
    expression  : (N_frames, 10) face expression
    transl      : (N_frames, 3)

SMPL-X body joint indices we care about (axis-angle triplets):
    Joint 13 = left shoulder
    Joint 14 = right shoulder
    Joint 16 = left elbow
    Joint 17 = right elbow
    Joint 18 = left wrist   (drives hand orientation)
    Joint 19 = right wrist
"""

import pickle
import numpy as np
import json
import argparse
from pathlib import Path


# ── The AMANDLA signs mapped to WLASL/SignAvatars word folder names ──
SIGN_MAP = {
    'HELP':       'help',
    'YES':        'yes',
    'NO':         'no',
    'PLEASE':     'please',
    'THANK YOU':  'thankyou',
    'WATER':      'water',
    'PAIN':       'pain',
    'WAIT':       'wait',
    'REPEAT':     'repeat',
    'UNDERSTAND': 'understand',
}

# SMPL-X body pose joint indices (0-based within body_pose 63-dim vector)
JOINT_NAMES = {
    'left_collar':    11,
    'right_collar':   12,
    'left_shoulder':  13,
    'right_shoulder': 14,
    'left_elbow':     15,
    'right_elbow':    16,
    'left_wrist':     17,
    'right_wrist':    18,
}

SOURCE_FPS = 30   # SignAvatars capture rate


# ─────────────────────────────────────────────────────────────────────────────
# MATH UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def axis_angle_to_euler(aa):
    """
    Convert axis-angle (3-vector) to Euler XYZ angles (radians).
    aa: numpy array of shape (3,)
    Returns: dict {x, y, z} in radians
    """
    angle = np.linalg.norm(aa)
    if angle < 1e-6:
        return {'x': 0.0, 'y': 0.0, 'z': 0.0}

    axis = aa / angle
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1.0 - c
    x, y, z = axis

    R = np.array([
        [t*x*x + c,   t*x*y - s*z, t*x*z + s*y],
        [t*x*y + s*z, t*y*y + c,   t*y*z - s*x],
        [t*x*z - s*y, t*y*z + s*x, t*z*z + c  ]
    ])

    sy = np.sqrt(R[0, 0]**2 + R[1, 0]**2)
    singular = sy < 1e-6

    if not singular:
        rx = np.arctan2( R[2, 1], R[2, 2])
        ry = np.arctan2(-R[2, 0], sy)
        rz = np.arctan2( R[1, 0], R[0, 0])
    else:
        rx = np.arctan2(-R[1, 2], R[1, 1])
        ry = np.arctan2(-R[2, 0], sy)
        rz = 0.0

    return {'x': float(rx), 'y': float(ry), 'z': float(rz)}


def _euler_delta(a, b):
    """Sum of absolute differences between two Euler dicts."""
    return (abs(b['x'] - a['x']) + abs(b['y'] - a['y']) + abs(b['z'] - a['z']))


# ─────────────────────────────────────────────────────────────────────────────
# FRAME EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _load_poses(pkl_path):
    """Load .pkl and return (poses array, n_frames). Returns (None, 0) on error."""
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f, encoding='latin1')

    if isinstance(data, dict):
        poses = data.get('poses', data.get('pose', None))
        if poses is None:
            frames = data.get('frames', [])
            if frames:
                poses = np.array([f.get('poses', np.zeros(165)) for f in frames])
        if poses is None:
            print(f"  WARNING: No pose data found in {pkl_path}")
            return None, 0
    elif isinstance(data, np.ndarray):
        poses = data
    else:
        print(f"  WARNING: Unknown format in {pkl_path}: {type(data)}")
        return None, 0

    poses = np.array(poses)
    if poses.ndim == 1:
        poses = poses[np.newaxis, :]
    return poses, int(poses.shape[0])


def extract_joints_from_frame(frame):
    """
    Extract all relevant joint Euler angles from a single SMPL-X frame vector.
    frame: numpy array of shape (165,)
    Returns: dict with joint names → Euler dicts and finger curl scalars.
    """
    body_pose = frame[3:66]  # 21 joints × 3

    result = {}
    for joint_name, joint_idx in JOINT_NAMES.items():
        start = joint_idx * 3
        result[joint_name] = axis_angle_to_euler(body_pose[start:start + 3])

    if len(frame) > 111:
        result['left_hand_orient']  = axis_angle_to_euler(frame[66:69])
        result['right_hand_orient'] = axis_angle_to_euler(frame[111:114])

        left_fingers  = frame[69:111].reshape(-1, 3)
        right_fingers = frame[114:156].reshape(-1, 3)
        result['left_finger_curl']  = float(np.mean(np.abs(left_fingers)))
        result['right_finger_curl'] = float(np.mean(np.abs(right_fingers)))

    return result


def extract_all_frames(pkl_path):
    """
    Load a .pkl sign file and return ALL frames as a list of joint dicts.
    Each item: {'joints': {...}, 'frame_index': int}
    """
    poses, n_frames = _load_poses(pkl_path)
    if poses is None or n_frames == 0:
        return []

    frames_out = []
    for idx in range(n_frames):
        joints = extract_joints_from_frame(poses[idx])
        frames_out.append({'joints': joints, 'frame_index': idx, 'total': n_frames})
    return frames_out


# ─────────────────────────────────────────────────────────────────────────────
# KEYFRAME SELECTION — angular displacement sampling
# ─────────────────────────────────────────────────────────────────────────────

def _angular_delta_between(frame_a, frame_b):
    """
    Sum of absolute Euler angle changes across all tracked joints
    between two raw frame dicts.
    """
    total = 0.0
    joints_a = frame_a['joints']
    joints_b = frame_b['joints']
    for jname in JOINT_NAMES:
        if jname in joints_a and jname in joints_b:
            total += _euler_delta(joints_a[jname], joints_b[jname])
    return total


def select_keyframes(raw_frames, n_keyframes=10):
    """
    Reduce a list of raw frame dicts to at most n_keyframes representative
    frames using cumulative angular displacement parametric resampling.

    Algorithm:
        1. Compute per-frame angular delta (sum |joint_angle_change|).
        2. Build cumulative displacement curve.
        3. Sample n_keyframes evenly along the cumulative curve.
        4. Map each sample to the nearest actual frame.
        5. Always include frame 0 and frame N-1.

    Returns a subset of raw_frames (same dict structure).
    """
    if len(raw_frames) <= n_keyframes:
        return raw_frames

    # Step 1: per-frame deltas
    deltas = [0.0]
    for i in range(1, len(raw_frames)):
        deltas.append(deltas[-1] + _angular_delta_between(raw_frames[i - 1], raw_frames[i]))

    total_motion = deltas[-1]

    if total_motion < 1e-6:
        # Essentially static sign — just keep first and last
        return [raw_frames[0], raw_frames[-1]]

    # Step 2: uniform sample targets along cumulative curve
    targets = [total_motion * k / (n_keyframes - 1) for k in range(n_keyframes)]

    # Step 3: nearest frame for each target
    selected = []
    j = 0
    for target in targets:
        while j < len(deltas) - 1 and deltas[j] < target:
            j += 1
        selected.append(raw_frames[j])

    # Step 4: deduplicate while preserving order; ensure first/last included
    seen = set()
    result = []
    for f in selected:
        if f['frame_index'] not in seen:
            seen.add(f['frame_index'])
            result.append(f)

    # Guarantee first and last frames are present
    if raw_frames[0]['frame_index'] not in seen:
        result.insert(0, raw_frames[0])
    if raw_frames[-1]['frame_index'] not in seen:
        result.append(raw_frames[-1])

    return result


# ─────────────────────────────────────────────────────────────────────────────
# THREE.JS MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def map_to_threejs(smplx_joints):
    """
    Map SMPL-X joint Euler angles to our Three.js skeleton structure.
    Returns a pose dict with 'R' and 'L' sub-dicts (same format as signs_library.js).
    """
    def get(name):
        j = smplx_joints.get(name, {})
        return j.get('x', 0.0), j.get('y', 0.0), j.get('z', 0.0)

    ls = get('left_shoulder')
    le = get('left_elbow')
    rs = get('right_shoulder')
    re = get('right_elbow')
    lw = get('left_wrist')
    rw = get('right_wrist')

    lfc = smplx_joints.get('left_finger_curl', 0.0)
    rfc = smplx_joints.get('right_finger_curl', 0.0)

    # Build finger curl arrays in [mcp, pip, dip] format
    # Scalar curl is distributed across joints with typical proportions
    def curl_array(scalar):
        c = float(np.clip(scalar, 0.0, 1.5))
        return [round(c * 0.8, 3), round(c * 1.1, 3), round(c * 0.7, 3)]

    hand_L = {
        'i': curl_array(lfc), 'm': curl_array(lfc),
        'r': curl_array(lfc), 'p': curl_array(lfc),
        't': [round(lfc * 0.4, 3), round(lfc * 0.3, 3)],
    }
    hand_R = {
        'i': curl_array(rfc), 'm': curl_array(rfc),
        'r': curl_array(rfc), 'p': curl_array(rfc),
        't': [round(rfc * 0.4, 3), round(rfc * 0.3, 3)],
    }

    return {
        'R': {
            'sh':   {'x': round(rs[0], 4), 'y': round(rs[1], 4), 'z': round(rs[2] - 0.22, 4)},
            'el':   {'x': round(re[0], 4), 'y': round(re[1], 4), 'z': round(re[2], 4)},
            'wr':   {'x': round(rw[0], 4), 'y': round(rw[1], 4), 'z': round(rw[2], 4)},
            'hand': hand_R,
        },
        'L': {
            'sh':   {'x': round(ls[0], 4), 'y': round(ls[1], 4), 'z': round(ls[2] + 0.22, 4)},
            'el':   {'x': round(le[0], 4), 'y': round(le[1], 4), 'z': round(le[2], 4)},
            'wr':   {'x': round(lw[0], 4), 'y': round(lw[1], 4), 'z': round(lw[2], 4)},
            'hand': hand_L,
        },
    }


def build_keyframe_entry(selected_frames, all_frames, fps=SOURCE_FPS):
    """
    Build a keyframe entry compatible with signWithFrames() in signs_library.js.

    Returns:
        {
          'frames':   [{'t': float, 'R': {...}, 'L': {...}}, ...],
          'duration': int (ms),
          'source':   str,
        }
    """
    n_total = len(all_frames)
    duration_ms = int((n_total / fps) * 1000)

    keyframes = []
    for f in selected_frames:
        idx = f['frame_index']
        t = round(idx / max(n_total - 1, 1), 4)
        pose = map_to_threejs(f['joints'])
        keyframes.append({'t': t, 'R': pose['R'], 'L': pose['L']})

    return {
        'frames':   keyframes,
        'duration': duration_ms,
        'source':   all_frames[0]['joints'].get('source_file', 'smplx'),
        'n_raw_frames': n_total,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DATASET CONVERSION
# ─────────────────────────────────────────────────────────────────────────────

def find_pkl_for_sign(base_dir, sign_folder_name):
    """Search for .pkl files matching a sign name, case-insensitive."""
    base = Path(base_dir)
    candidates = [
        base / sign_folder_name,
        base / sign_folder_name.upper(),
        base / sign_folder_name.lower(),
        base / sign_folder_name.replace(' ', '_'),
        base / sign_folder_name.replace(' ', ''),
    ]
    for candidate in candidates:
        if candidate.is_dir():
            pkls = sorted(list(candidate.glob('*.pkl')))
            if pkls:
                print(f"  Found {len(pkls)} file(s) in {candidate}")
                return pkls[0]
    for d in base.rglob('*'):
        if d.is_dir() and sign_folder_name.lower() in d.name.lower():
            pkls = sorted(list(d.glob('*.pkl')))
            if pkls:
                print(f"  Found via deep search: {d}")
                return pkls[0]
    return None


def convert_dataset(input_dir, output_path, n_keyframes=10, legacy=False):
    """
    Main conversion: iterate over all signs in SIGN_MAP, extract keyframe
    sequences, write JSON.

    With legacy=True, outputs single-frame poses (v1 behaviour).
    """
    print("\nAMANDLA SignAvatars Converter v2.0")
    print(f"Input:     {input_dir}")
    print(f"Output:    {output_path}")
    print(f"Keyframes: {n_keyframes} per sign")
    print("=" * 55)

    result = {}
    found = 0
    missing = []

    for amandla_name, folder_name in SIGN_MAP.items():
        print(f"\n[{amandla_name}] searching for '{folder_name}'...")

        pkl_path = find_pkl_for_sign(input_dir, folder_name)
        if pkl_path is None:
            print("  NOT FOUND — will use existing hand-crafted sign")
            missing.append(amandla_name)
            continue

        print(f"  Loading: {pkl_path.name}")
        raw_frames = extract_all_frames(str(pkl_path))

        if not raw_frames:
            print("  EXTRACTION FAILED")
            missing.append(amandla_name)
            continue

        if legacy:
            # v1 behaviour: single peak frame
            hand_region_sums = [
                sum(abs(raw_frames[i]['joints'].get(jn, {}).get(ax, 0))
                    for jn in JOINT_NAMES for ax in ('x', 'y', 'z'))
                for i in range(len(raw_frames))
            ]
            peak = raw_frames[int(np.argmax(hand_region_sums))]
            pose = map_to_threejs(peak['joints'])
            result[amandla_name] = {**pose, 'source': str(pkl_path.name),
                                    'frame': peak['frame_index']}
        else:
            selected = select_keyframes(raw_frames, n_keyframes)
            entry = build_keyframe_entry(selected, raw_frames)
            result[amandla_name] = entry

            n_raw = entry['n_raw_frames']
            n_sel = len(entry['frames'])
            dur   = entry['duration']
            print(f"  ✓ {n_raw} raw frames → {n_sel} keyframes  ({dur}ms)")

        found += 1

    print(f"\n{'='*55}")
    print(f"Extracted: {found}/{len(SIGN_MAP)} signs")
    if missing:
        print(f"Missing:   {', '.join(missing)}")
        print("These will continue to use hand-crafted fallback poses.")

    output = {
        'generated_by': 'AMANDLA SignAvatars Converter v2.0',
        'source':       'SignAvatars Word-Level ASL Subset (ECCV 2024)',
        'license':      'Non-commercial research use only',
        'format':       'legacy' if legacy else 'keyframes',
        'signs':        result,
        'missing':      missing,
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nWritten: {output_path}")
    if not legacy:
        print("Load with signWithFrames() in signs_library.js, or run:")
        print("  python scripts/merge_sign_data.py --data poses.json --output signs_library_generated.js")

    return result


def inspect_pkl(pkl_path):
    """Quick inspection of a single .pkl — useful for debugging structure."""
    print(f"\nInspecting: {pkl_path}")
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f, encoding='latin1')

    print(f"Type: {type(data)}")
    if isinstance(data, dict):
        print(f"Keys: {list(data.keys())}")
        for k, v in data.items():
            if hasattr(v, 'shape'):
                print(f"  {k}: shape={v.shape}, dtype={v.dtype}")
            elif isinstance(v, (list, tuple)):
                print(f"  {k}: len={len(v)}")
            else:
                print(f"  {k}: {type(v)} = {v}")
    elif isinstance(data, np.ndarray):
        print(f"Array shape: {data.shape}")
    elif isinstance(data, list):
        print(f"List length: {len(data)}")
        if data:
            print(f"First element type: {type(data[0])}")
            if isinstance(data[0], dict):
                print(f"First element keys: {list(data[0].keys())}")

    # Show a quick frame-count estimate
    raw = extract_all_frames(pkl_path)
    if raw:
        print(f"\nFrame count:   {len(raw)}")
        print(f"Est. duration: {int(len(raw) / SOURCE_FPS * 1000)}ms at {SOURCE_FPS}fps")
        sample = select_keyframes(raw, 10)
        print(f"Keyframes (n=10): t values = {[round(f['frame_index']/(len(raw)-1),3) for f in sample]}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert SignAvatars .pkl to AMANDLA Three.js keyframes'
    )
    parser.add_argument('--input',     required=False, help='Path to word_level_asl/ folder')
    parser.add_argument('--output',    default='poses.json', help='Output JSON path')
    parser.add_argument('--keyframes', type=int, default=10, help='Max keyframes per sign (default 10)')
    parser.add_argument('--legacy',    action='store_true', help='v1 single-frame output (for comparison)')
    parser.add_argument('--inspect',   help='Inspect a single .pkl file structure')
    args = parser.parse_args()

    if args.inspect:
        inspect_pkl(args.inspect)
    elif args.input:
        convert_dataset(args.input, args.output, n_keyframes=args.keyframes, legacy=args.legacy)
    else:
        parser.print_help()
