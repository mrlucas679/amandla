"""
AMANDLA — MediaPipe Holistic Sign Recorder
==========================================
Records real SASL signs via webcam and exports keyframe JSON compatible
with signWithFrames() in signs_library.js.

Usage:
    python scripts/record_signs.py
    python scripts/record_signs.py --output-dir data/recorded_signs --keyframes 10

Controls (in the OpenCV window):
    SPACE  — start / stop recording a sign
    Q      — quit
    R      — discard last recording and re-record

Requires:
    pip install mediapipe opencv-python numpy

Output format (per file):
    data/recorded_signs/{WORD}_{timestamp}.json
    {
      "word": "HELP",
      "recorded_at": "2026-04-05T14:23:00",
      "source": "mediapipe_holistic",
      "fps": 30,
      "n_raw_frames": 47,
      "frames": [{"t": 0.0, "R": {...}, "L": {...}}, ...],
      "duration": 1566
    }

The output matches the format produced by convert_signs.py --keyframes,
so merge_sign_data.py can process both sources the same way.
"""

import sys
import os
import json
import time
import argparse
import math
from datetime import datetime
from pathlib import Path

try:
    import cv2
except ImportError:
    sys.exit("opencv-python is required: pip install opencv-python")

try:
    import mediapipe as mp
except ImportError:
    sys.exit("mediapipe is required: pip install mediapipe")

try:
    import numpy as np
except ImportError:
    sys.exit("numpy is required: pip install numpy")

# Re-use the keyframe selection algorithm from convert_signs.py
sys.path.insert(0, str(Path(__file__).parent.parent))
from convert_signs import select_keyframes, SOURCE_FPS


# ─────────────────────────────────────────────────────────────────────────────
# MEDIAPIPE LANDMARK → ARM JOINT ANGLES
# ─────────────────────────────────────────────────────────────────────────────

# MediaPipe Pose landmark indices for arms
# https://developers.google.com/mediapipe/solutions/vision/pose_landmarker
MP_LANDMARKS = {
    'left_shoulder':  11,
    'right_shoulder': 12,
    'left_elbow':     13,
    'right_elbow':    14,
    'left_wrist':     15,
    'right_wrist':    16,
    'left_hip':       23,
    'right_hip':      24,
}


def _vec3(lm):
    """Return (x, y, z) from a MediaPipe landmark."""
    return np.array([lm.x, lm.y, lm.z], dtype=np.float32)


def _angle_between(v1, v2):
    """Angle (radians) between two 3D vectors."""
    n1 = np.linalg.norm(v1)
    n2 = np.linalg.norm(v2)
    if n1 < 1e-6 or n2 < 1e-6:
        return 0.0
    return float(math.acos(np.clip(np.dot(v1 / n1, v2 / n2), -1.0, 1.0)))


def landmark_to_arm_angles(pose_landmarks, side):
    """
    Compute approximate shoulder / elbow / wrist Euler angles from
    MediaPipe Pose landmarks using 3-point joint geometry.

    MediaPipe coordinate system: x=right, y=down, z=into screen.
    We remap to signs_library.js conventions:
        sh.x negative = arm raised forward/up
        sh.z negative = right arm abducts outward

    Returns: {'sh': {x,y,z}, 'el': {x,y,z}, 'wr': {x,y,z}}
    """
    lms = pose_landmarks.landmark

    if side == 'R':
        sh_i, el_i, wr_i = (MP_LANDMARKS['right_shoulder'],
                             MP_LANDMARKS['right_elbow'],
                             MP_LANDMARKS['right_wrist'])
        hip_i = MP_LANDMARKS['right_hip']
        z_sign = -1.0  # right arm abducts in -Z
    else:
        sh_i, el_i, wr_i = (MP_LANDMARKS['left_shoulder'],
                             MP_LANDMARKS['left_elbow'],
                             MP_LANDMARKS['left_wrist'])
        hip_i = MP_LANDMARKS['left_hip']
        z_sign = 1.0   # left arm abducts in +Z

    sh_pt = _vec3(lms[sh_i])
    el_pt = _vec3(lms[el_i])
    wr_pt = _vec3(lms[wr_i])
    hip_pt = _vec3(lms[hip_i])

    # Upper-arm vector (shoulder → elbow)
    upper_arm = el_pt - sh_pt
    # Reference vectors for shoulder angles
    body_down  = hip_pt - sh_pt           # direction of hanging arm
    body_front = np.array([0, 0, -1], dtype=np.float32)  # into screen

    # Shoulder elevation (flex/extension): angle of upper_arm vs body_down in sagittal plane
    sh_flex = _angle_between(
        np.array([upper_arm[0], upper_arm[1], 0]),
        np.array([body_down[0], body_down[1], 0])
    )
    # Shoulder abduction: angle of upper_arm vs body_down in frontal plane
    sh_abd  = _angle_between(
        np.array([0, upper_arm[1], upper_arm[2]]),
        np.array([0, body_down[1], body_down[2]])
    )

    # Map to signs_library.js conventions
    sh_x = -sh_flex * (1.0 if upper_arm[1] < body_down[1] else -1.0)
    sh_z = z_sign * sh_abd

    # Elbow flexion: angle at elbow between upper arm and forearm
    forearm  = wr_pt - el_pt
    el_angle = _angle_between(-upper_arm, forearm)  # 0 = straight
    el_x     = -el_angle  # negative = bent

    # Wrist: simple tilt relative to forearm direction
    wr_tilt = _angle_between(forearm, np.array([forearm[0], forearm[1], 0]))
    wr_x    = wr_tilt * (1.0 if forearm[2] > 0 else -1.0)

    return {
        'sh': {'x': round(float(sh_x), 4), 'y': 0.0, 'z': round(float(sh_z), 4)},
        'el': {'x': round(float(el_x), 4), 'y': 0.0, 'z': 0.0},
        'wr': {'x': round(float(wr_x), 4), 'y': 0.0, 'z': 0.0},
    }


def compute_finger_curl(hand_landmarks):
    """
    Estimate per-finger curl from MediaPipe Hand landmarks.
    Uses y-coordinate ratio of fingertip vs MCP (knuckle).
    Returns hand dict: {'i', 'm', 'r', 'p', 't'} each [mcp, pip, dip].

    MediaPipe hand landmark indices:
        0=WRIST, 1-4=THUMB, 5-8=INDEX, 9-12=MIDDLE, 13-16=RING, 17-20=PINKY
    """
    lms = hand_landmarks.landmark

    def curl_for_finger(mcp_i, pip_i, dip_i, tip_i):
        mcp = _vec3(lms[mcp_i])
        pip = _vec3(lms[pip_i])
        dip = _vec3(lms[dip_i])
        tip = _vec3(lms[tip_i])
        wrist = _vec3(lms[0])

        # Compute extension angles at each joint
        def ext_angle(a, b, c):
            return _angle_between(b - a, c - b)

        mcp_angle = ext_angle(wrist, mcp, pip)
        pip_angle = ext_angle(mcp, pip, dip)
        dip_angle = ext_angle(pip, dip, tip)

        # Map extension angle (0=straight, π=fully curled) to [0..1.5] curl scale
        scale = 1.5 / math.pi
        return [
            round(mcp_angle * scale, 3),
            round(pip_angle * scale * 1.1, 3),
            round(dip_angle * scale * 0.7, 3),
        ]

    def thumb_curl(cmc_i, mcp_i, ip_i, tip_i):
        cmc = _vec3(lms[cmc_i])
        mcp = _vec3(lms[mcp_i])
        ip  = _vec3(lms[ip_i])
        tip = _vec3(lms[tip_i])
        a1 = _angle_between(mcp - cmc, ip  - mcp)
        a2 = _angle_between(mcp - cmc, tip - ip)
        scale = 0.6 / math.pi
        return [round(a1 * scale, 3), round(a2 * scale, 3)]

    return {
        'i': curl_for_finger(5, 6, 7, 8),
        'm': curl_for_finger(9, 10, 11, 12),
        'r': curl_for_finger(13, 14, 15, 16),
        'p': curl_for_finger(17, 18, 19, 20),
        't': thumb_curl(1, 2, 3, 4),
    }


_DEFAULT_HAND = {
    'i': [0.2, 0.15, 0.1], 'm': [0.2, 0.15, 0.1],
    'r': [0.2, 0.15, 0.1], 'p': [0.2, 0.15, 0.1],
    't': [0.2, 0.12],
}


# ─────────────────────────────────────────────────────────────────────────────
# SIGN RECORDER
# ─────────────────────────────────────────────────────────────────────────────

class SignRecorder:
    def __init__(self, output_dir='data/recorded_signs', n_keyframes=10):
        self.output_dir  = Path(output_dir)
        self.n_keyframes = n_keyframes
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _process_frame(self, results):
        """
        Extract R and L arm/hand data from a MediaPipe Holistic result.
        Returns a raw frame dict compatible with select_keyframes().
        """
        joints = {}

        if results.pose_landmarks:
            for side, key_r, key_l in [('R', 'right_shoulder', 'left_shoulder'),
                                        ('L', 'right_shoulder', 'left_shoulder')]:
                arm_side = 'R' if side == 'R' else 'L'
                angles = landmark_to_arm_angles(results.pose_landmarks, arm_side)
                joints[f'{arm_side}_sh'] = angles['sh']
                joints[f'{arm_side}_el'] = angles['el']
                joints[f'{arm_side}_wr'] = angles['wr']

        # Hand landmarks → finger curls
        right_hand = (compute_finger_curl(results.right_hand_landmarks)
                      if results.right_hand_landmarks else _DEFAULT_HAND)
        left_hand  = (compute_finger_curl(results.left_hand_landmarks)
                      if results.left_hand_landmarks else _DEFAULT_HAND)

        return {
            'joints': joints,
            'hand_R': right_hand,
            'hand_L': left_hand,
        }

    def _raw_to_sign_frame(self, raw_frame, frame_index, total):
        """Convert recorder raw frame to the same format as convert_signs.py."""
        j = raw_frame['joints']
        return {
            'frame_index': frame_index,
            'total': total,
            'joints': {
                # Pack joint angles under JOINT_NAMES-compatible keys
                # (select_keyframes uses these via _angular_delta_between)
                'right_shoulder': j.get('R_sh', {'x': 0, 'y': 0, 'z': 0}),
                'left_shoulder':  j.get('L_sh', {'x': 0, 'y': 0, 'z': 0}),
                'right_elbow':    j.get('R_el', {'x': 0, 'y': 0, 'z': 0}),
                'left_elbow':     j.get('L_el', {'x': 0, 'y': 0, 'z': 0}),
                'right_wrist':    j.get('R_wr', {'x': 0, 'y': 0, 'z': 0}),
                'left_wrist':     j.get('L_wr', {'x': 0, 'y': 0, 'z': 0}),
            },
            '_hand_R': raw_frame['hand_R'],
            '_hand_L': raw_frame['hand_L'],
        }

    def _export_sign(self, word, raw_buffer):
        """
        Downsample raw_buffer to keyframes, build output JSON, save to disk.
        Returns the output file path.
        """
        total = len(raw_buffer)
        # Wrap in the format select_keyframes() expects
        wrapped = [self._raw_to_sign_frame(f, i, total) for i, f in enumerate(raw_buffer)]
        selected = select_keyframes(wrapped, self.n_keyframes)

        # Build Three.js-compatible keyframe list
        frames_out = []
        for f in selected:
            idx = f['frame_index']
            t   = round(idx / max(total - 1, 1), 4)
            j   = f['joints']
            frames_out.append({
                't': t,
                'R': {
                    'sh':   j.get('right_shoulder', {'x': 0, 'y': 0, 'z': 0}),
                    'el':   j.get('right_elbow',    {'x': 0, 'y': 0, 'z': 0}),
                    'wr':   j.get('right_wrist',    {'x': 0, 'y': 0, 'z': 0}),
                    'hand': f.get('_hand_R', _DEFAULT_HAND),
                },
                'L': {
                    'sh':   j.get('left_shoulder', {'x': 0, 'y': 0, 'z': 0}),
                    'el':   j.get('left_elbow',    {'x': 0, 'y': 0, 'z': 0}),
                    'wr':   j.get('left_wrist',    {'x': 0, 'y': 0, 'z': 0}),
                    'hand': f.get('_hand_L', _DEFAULT_HAND),
                },
            })

        duration_ms = int((total / SOURCE_FPS) * 1000)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"{word.upper()}_{ts}.json"

        output = {
            'word':         word.upper(),
            'recorded_at':  datetime.now().isoformat(timespec='seconds'),
            'source':       'mediapipe_holistic',
            'fps':          SOURCE_FPS,
            'n_raw_frames': total,
            'frames':       frames_out,
            'duration':     duration_ms,
        }

        with open(filename, 'w') as fh:
            json.dump(output, fh, indent=2)

        return filename

    def _draw_overlay(self, frame, recording, word, frame_count):
        """Draw status overlay on the OpenCV window."""
        h, w = frame.shape[:2]

        if recording:
            # Red recording indicator
            cv2.circle(frame, (30, 30), 12, (0, 0, 220), -1)
            cv2.putText(frame, f'REC  {word}  [{frame_count} frames]',
                        (55, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 0, 220), 2)
            cv2.putText(frame, 'SPACE = stop',
                        (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        else:
            cv2.putText(frame, 'SPACE = record  |  Q = quit  |  R = re-record last',
                        (10, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
            cv2.putText(frame, 'AMANDLA Sign Recorder',
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 200, 120), 2)

    def run(self):
        mp_holistic  = mp.solutions.holistic
        mp_drawing   = mp.solutions.drawing_utils
        mp_draw_styles = mp.solutions.drawing_styles

        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            sys.exit("ERROR: Could not open webcam. Check camera permissions.")

        holistic = mp_holistic.Holistic(
            model_complexity=1,
            enable_segmentation=False,
            refine_face_landmarks=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        recording     = False
        frames_buffer = []
        current_word  = None
        last_saved    = None

        print("\nAMANDLA Sign Recorder ready.")
        print("Controls: SPACE=start/stop  R=re-record last  Q=quit\n")

        try:
            while True:
                ret, bgr = cap.read()
                if not ret:
                    break

                bgr = cv2.flip(bgr, 1)  # mirror for natural feel
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                rgb.flags.writeable = False
                results = holistic.process(rgb)
                rgb.flags.writeable = True
                display = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

                # Draw landmarks
                if results.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        display, results.pose_landmarks,
                        mp_holistic.POSE_CONNECTIONS,
                        landmark_drawing_spec=mp_draw_styles.get_default_pose_landmarks_style(),
                    )
                if results.right_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        display, results.right_hand_landmarks,
                        mp_holistic.HAND_CONNECTIONS,
                    )
                if results.left_hand_landmarks:
                    mp_drawing.draw_landmarks(
                        display, results.left_hand_landmarks,
                        mp_holistic.HAND_CONNECTIONS,
                    )

                self._draw_overlay(display, recording, current_word,
                                   len(frames_buffer))
                cv2.imshow('AMANDLA Sign Recorder', display)

                # Accumulate frames while recording
                if recording and results.pose_landmarks:
                    frames_buffer.append(self._process_frame(results))

                key = cv2.waitKey(1) & 0xFF

                if key == ord('q') or key == 27:
                    break

                elif key == ord(' '):
                    if not recording:
                        # Prompt for sign word in terminal
                        word = input('Sign word name (e.g. HELP): ').strip().upper()
                        if not word:
                            print("  No word entered — not starting recording.")
                            continue
                        current_word  = word
                        frames_buffer = []
                        recording     = True
                        print(f"  Recording '{word}'... press SPACE to stop.")
                    else:
                        # Stop recording
                        recording = False
                        n = len(frames_buffer)
                        if n < 5:
                            print(f"  Only {n} frames captured — too short, discarded.")
                            current_word  = None
                            frames_buffer = []
                        else:
                            path = self._export_sign(current_word, frames_buffer)
                            last_saved = path
                            print(f"  Saved {n} frames → {path}")
                            current_word  = None
                            frames_buffer = []

                elif key == ord('r'):
                    if recording:
                        print("  Recording cancelled.")
                        recording     = False
                        current_word  = None
                        frames_buffer = []
                    elif last_saved and last_saved.exists():
                        last_saved.unlink()
                        print(f"  Deleted {last_saved.name} — ready to re-record.")
                        last_saved = None
                    else:
                        print("  Nothing to re-record.")

        finally:
            cap.release()
            holistic.close()
            cv2.destroyAllWindows()
            print("\nRecorder closed.")


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='AMANDLA MediaPipe Sign Recorder')
    parser.add_argument('--output-dir', default='data/recorded_signs',
                        help='Directory for output JSON files (default: data/recorded_signs)')
    parser.add_argument('--keyframes', type=int, default=10,
                        help='Max keyframes to keep per sign (default: 10)')
    args = parser.parse_args()

    recorder = SignRecorder(output_dir=args.output_dir, n_keyframes=args.keyframes)
    recorder.run()
