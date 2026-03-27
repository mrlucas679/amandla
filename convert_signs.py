"""
AMANDLA — SignAvatars .pkl → Three.js poses.json converter
============================================================
Run this AFTER downloading the Word-level ASL subset from SignAvatars.

Usage:
    python convert_signs.py --input /path/to/word_level_asl/ --output poses.json

The Word-level ASL folder structure is typically:
    word_level_asl/
        HELP/
            001.pkl
            002.pkl
        WATER/
            001.pkl
        YES/
            001.pkl
        ...

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
import os
import argparse
from pathlib import Path


# ── The 10 AMANDLA quick-signs mapped to WLASL word names ──
# WLASL uses uppercase folder names — adjust if your dataset differs
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
# Each joint = 3 values (axis-angle: x, y, z)
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

    # Rodrigues → rotation matrix
    c = np.cos(angle)
    s = np.sin(angle)
    t = 1.0 - c
    x, y, z = axis

    R = np.array([
        [t*x*x + c,   t*x*y - s*z, t*x*z + s*y],
        [t*x*y + s*z, t*y*y + c,   t*y*z - s*x],
        [t*x*z - s*y, t*y*z + s*x, t*z*z + c  ]
    ])

    # Rotation matrix → Euler XYZ (intrinsic)
    sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
    singular = sy < 1e-6

    if not singular:
        rx = np.arctan2( R[2,1], R[2,2])
        ry = np.arctan2(-R[2,0], sy)
        rz = np.arctan2( R[1,0], R[0,0])
    else:
        rx = np.arctan2(-R[1,2], R[1,1])
        ry = np.arctan2(-R[2,0], sy)
        rz = 0.0

    return {'x': float(rx), 'y': float(ry), 'z': float(rz)}


def extract_key_frame(pkl_path):
    """
    Load a single .pkl sign file and extract the 'peak' frame —
    the frame with maximum hand displacement from neutral.
    Returns dict of joint Euler rotations.
    """
    with open(pkl_path, 'rb') as f:
        data = pickle.load(f, encoding='latin1')

    # Handle different possible formats
    if isinstance(data, dict):
        poses = data.get('poses', data.get('pose', None))
        if poses is None:
            # Try loading as list of frames
            frames = data.get('frames', [])
            if frames:
                poses = np.array([f.get('poses', np.zeros(165)) for f in frames])
        if poses is None:
            print(f"  WARNING: Could not find pose data in {pkl_path}")
            return None
    elif isinstance(data, np.ndarray):
        poses = data
    else:
        print(f"  WARNING: Unknown format in {pkl_path}: {type(data)}")
        return None

    poses = np.array(poses)
    if poses.ndim == 1:
        poses = poses[np.newaxis, :]  # single frame

    n_frames = poses.shape[0]

    # Find the peak frame: max sum of absolute hand joint values
    # Hand joints = body pose indices 13-18 (shoulders, elbows, wrists)
    hand_region = poses[:, 39:57]  # joints 13-18 = dims 39..56
    peak_idx = int(np.argmax(np.sum(np.abs(hand_region), axis=1)))

    # Also get a mid frame for comparison
    mid_idx = n_frames // 2

    # Use peak or mid — whichever has more hand activity
    frame_idx = peak_idx
    frame = poses[frame_idx]

    # Extract body pose (dims 3..66, 21 joints × 3)
    # global_orient = dims 0..2
    body_pose = frame[3:66]   # 63 values = 21 joints × 3

    result = {}
    for joint_name, joint_idx in JOINT_NAMES.items():
        start = joint_idx * 3
        aa = body_pose[start:start+3]
        result[joint_name] = axis_angle_to_euler(aa)

    # Also extract wrist rotations for hand orientation
    # Left hand pose starts at dim 66, right at 111
    if len(frame) > 111:
        left_wrist_aa  = frame[66:69]    # first joint of left hand = wrist
        right_wrist_aa = frame[111:114]  # first joint of right hand
        result['left_hand_orient']  = axis_angle_to_euler(left_wrist_aa)
        result['right_hand_orient'] = axis_angle_to_euler(right_wrist_aa)

        # Finger curl: average of all finger joints per hand
        left_fingers  = frame[69:111].reshape(-1, 3)   # 14 joints
        right_fingers = frame[114:156].reshape(-1, 3)
        result['left_finger_curl']  = float(np.mean(np.abs(left_fingers)))
        result['right_finger_curl'] = float(np.mean(np.abs(right_fingers)))

    result['source_file']  = os.path.basename(pkl_path)
    result['frame_index']  = int(frame_idx)
    result['total_frames'] = int(n_frames)

    return result


def map_to_threejs(smplx_joints):
    """
    Map SMPL-X joint Euler angles to our Three.js skeleton structure.

    Three.js skeleton groups:
        ls = leftShoulderG   (controls upper left arm direction)
        le = leftElbowG      (controls forearm bend)
        rs = rightShoulderG
        re = rightElbowG

    SMPL-X → Three.js mapping notes:
    - SMPL-X Y-axis is UP, Three.js Y-axis is also UP ✓
    - SMPL-X rotates in body-local space, we need world-space
    - Shoulder abduction = shoulder Z rotation in SMPL-X
    - Elbow flexion = elbow X rotation in SMPL-X
    - Sign for scale: arms hang down = neutral (0 rotation) in both
    """
    def get(name, default_x=0, default_y=0, default_z=0):
        j = smplx_joints.get(name, {})
        return (
            j.get('x', default_x),
            j.get('y', default_y),
            j.get('z', default_z)
        )

    ls_aa = get('left_shoulder')
    le_aa = get('left_elbow')
    rs_aa = get('right_shoulder')
    re_aa = get('right_elbow')
    lw_aa = get('left_wrist')
    rw_aa = get('right_wrist')

    # SMPL-X left shoulder: negative X = raise arm forward
    #                        negative Z = raise arm sideways (abduct)
    # Three.js leftShoulderG: negative X = raise arm up/forward
    #                          positive Z = abduct outward
    pose = {
        'ls': {
            'x': ls_aa[0],
            'y': ls_aa[1],
            'z': ls_aa[2] + 0.22    # add natural hang offset
        },
        'le': {
            'x': le_aa[0],
            'y': le_aa[1],
            'z': le_aa[2]
        },
        'rs': {
            'x': rs_aa[0],
            'y': rs_aa[1],
            'z': rs_aa[2] - 0.22    # mirror offset
        },
        're': {
            'x': re_aa[0],
            'y': re_aa[1],
            'z': re_aa[2]
        },
        'lw': {
            'x': lw_aa[0],
            'y': lw_aa[1],
            'z': lw_aa[2]
        },
        'rw': {
            'x': rw_aa[0],
            'y': rw_aa[1],
            'z': rw_aa[2]
        },
        'left_finger_curl':  smplx_joints.get('left_finger_curl', 0.0),
        'right_finger_curl': smplx_joints.get('right_finger_curl', 0.0),
    }

    return pose


def find_pkl_for_sign(base_dir, sign_folder_name):
    """Search for .pkl files matching a sign name, case-insensitive."""
    base = Path(base_dir)

    # Try exact match, then uppercase, then case-insensitive search
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
                print(f"  Found {len(pkls)} files in {candidate}")
                return pkls[0]  # use first (most common/representative)

    # Deep search
    for d in base.rglob('*'):
        if d.is_dir() and sign_folder_name.lower() in d.name.lower():
            pkls = sorted(list(d.glob('*.pkl')))
            if pkls:
                print(f"  Found via deep search: {d}")
                return pkls[0]

    return None


def convert_dataset(input_dir, output_path):
    """Main conversion: iterate over 10 signs, extract poses, write JSON."""
    print(f"\nAMANDLA SignAvatars Converter")
    print(f"Input: {input_dir}")
    print(f"Output: {output_path}")
    print("=" * 50)

    result = {}
    found = 0
    missing = []

    for amandla_name, folder_name in SIGN_MAP.items():
        print(f"\n[{amandla_name}] searching for '{folder_name}'...")

        pkl_path = find_pkl_for_sign(input_dir, folder_name)

        if pkl_path is None:
            print(f"  NOT FOUND — will use fallback pose")
            missing.append(amandla_name)
            continue

        print(f"  Loading: {pkl_path.name}")
        smplx = extract_key_frame(str(pkl_path))

        if smplx is None:
            print(f"  EXTRACTION FAILED")
            missing.append(amandla_name)
            continue

        threejs_pose = map_to_threejs(smplx)
        threejs_pose['source'] = str(pkl_path.name)
        threejs_pose['frame']  = smplx.get('frame_index', 0)
        result[amandla_name] = threejs_pose

        found += 1
        print(f"  ✓ Extracted frame {smplx['frame_index']}/{smplx['total_frames']}")
        print(f"    ls: x={threejs_pose['ls']['x']:.3f} z={threejs_pose['ls']['z']:.3f}")
        print(f"    rs: x={threejs_pose['rs']['x']:.3f} z={threejs_pose['rs']['z']:.3f}")

    print(f"\n{'='*50}")
    print(f"Extracted: {found}/10 signs")
    if missing:
        print(f"Missing: {', '.join(missing)}")
        print("These will use the existing hand-crafted fallback poses.")

    # Write output
    output = {
        'generated_by': 'AMANDLA SignAvatars Converter',
        'source': 'SignAvatars Word-Level ASL Subset (ECCV 2024)',
        'license': 'Non-commercial research use only',
        'signs': result,
        'missing': missing
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"\nWritten: {output_path}")
    print(f"Now drop poses.json next to amandla_avatar.html")
    print(f"The avatar will auto-load real SMPL-X poses where available.")

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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert SignAvatars .pkl to AMANDLA Three.js poses')
    parser.add_argument('--input',   required=True, help='Path to word_level_asl/ folder')
    parser.add_argument('--output',  default='poses.json', help='Output JSON path')
    parser.add_argument('--inspect', help='Inspect a single .pkl file structure')
    args = parser.parse_args()

    if args.inspect:
        inspect_pkl(args.inspect)
    else:
        convert_dataset(args.input, args.output)
