"""
scripts/gen_harps_from_library.py
===================================
Generate HARPS training data from signs_library.js joint-angle data.

NO VIDEOS NEEDED — we already have everything we need:
  - signs_library.js stores exact shoulder/elbow/wrist rotations for 120+ SASL signs
  - HS presets give per-finger curl angles for each handshape
  - Forward kinematics converts angles → 3D joint positions → MediaPipe-format landmarks

The output replaces backend/harps_model/ with a model trained on real SASL sign names.
Each sign gets 30 training frames: idle→pose transition (15) + pose hold with noise (15).

Usage:
    python scripts/gen_harps_from_library.py
    # or with options:
    python scripts/gen_harps_from_library.py --epochs 500 --hidden_dim 128
"""

import argparse
import json
import os
import sys
import numpy as np
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "backend" / "harps_model"

# ─── HANDSHAPE PRESETS (mirrors signs_library.js Section 1) ───────────────────
HS = {
    "open5":  {"i":[0.08,0.05,0.03],"m":[0.08,0.05,0.03],"r":[0.08,0.05,0.03],"p":[0.08,0.05,0.03],"t":[0.05,0.05,0.0]},
    "flat":   {"i":[0.10,0.06,0.04],"m":[0.10,0.06,0.04],"r":[0.10,0.06,0.04],"p":[0.10,0.06,0.04],"t":[0.28,0.40,0.0]},
    "fist_A": {"i":[1.15,1.55,1.05],"m":[1.15,1.55,1.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[-0.15,0.10,0.0]},
    "fist_S": {"i":[1.15,1.55,1.05],"m":[1.15,1.55,1.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[0.45,0.55,0.0]},
    "point1": {"i":[0.15,0.08,0.05],"m":[1.15,1.55,1.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[0.45,0.25,0.0]},
    "vhand":  {"i":[0.15,0.08,0.05],"m":[0.15,0.08,0.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[0.50,0.35,0.0]},
    "whand":  {"i":[0.08,0.05,0.03],"m":[0.08,0.05,0.03],"r":[0.08,0.05,0.03],"p":[1.15,1.55,1.05],"t":[0.50,0.75,0.0]},
    "yhand":  {"i":[1.15,1.55,1.05],"m":[1.15,1.55,1.05],"r":[1.15,1.55,1.05],"p":[0.08,0.05,0.03],"t":[-0.10,0.05,0.0]},
    "lhand":  {"i":[0.15,0.08,0.05],"m":[1.15,1.55,1.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[-0.20,0.05,0.0]},
    "chand":  {"i":[0.70,0.90,0.60],"m":[0.70,0.90,0.60],"r":[0.70,0.90,0.60],"p":[0.70,0.90,0.60],"t":[0.15,0.20,0.0]},
    "xhand":  {"i":[0.55,1.55,1.05],"m":[1.15,1.55,1.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[0.45,0.25,0.0]},
    "claw":   {"i":[0.70,0.90,0.60],"m":[0.70,0.90,0.60],"r":[0.70,0.90,0.60],"p":[0.70,0.90,0.60],"t":[0.30,0.30,0.0]},
    "fhand":  {"i":[0.55,0.90,0.60],"m":[0.08,0.05,0.03],"r":[0.08,0.05,0.03],"p":[0.08,0.05,0.03],"t":[0.55,0.55,0.0]},
    "uhand":  {"i":[0.15,0.08,0.05],"m":[0.15,0.08,0.05],"r":[1.15,1.55,1.05],"p":[1.15,1.55,1.05],"t":[0.50,0.55,0.0]},
    "rest":   {"i":[0.20,0.15,0.10],"m":[0.20,0.15,0.10],"r":[0.20,0.15,0.10],"p":[0.20,0.15,0.10],"t":[0.20,0.12,0.0]},
}

# ─── IDLE ARM POSITIONS ────────────────────────────────────────────────────────
IDLE_R = {"sh":{"x":0.05,"y":0,"z":-0.22},"el":{"x":0.08,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0}}
IDLE_L = {"sh":{"x":0.05,"y":0,"z": 0.22},"el":{"x":0.08,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0}}

# ─── SIGN DEFINITIONS (from signs_library.js) ─────────────────────────────────
# Format: { name, R:{sh,el,wr,hand_key}, L:{sh,el,wr,hand_key} }
# IL = IDLE_L, NR/NL = "rest" handshape
SIGNS = [
    # ── Greetings ────────────────────────────────────────────────────────────
    {"name":"HELLO",      "R":{"sh":{"x":-1.35,"y":0,"z":-0.18},"el":{"x":0.05,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"},    "L":"idle"},
    {"name":"GOODBYE",    "R":{"sh":{"x":-1.30,"y":0,"z":-0.15},"el":{"x":0.05,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"},    "L":"idle"},
    {"name":"HOW ARE YOU","R":{"sh":{"x":-0.55,"y":0,"z":-0.30},"el":{"x":-0.60,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"lhand"},
                          "L":{"sh":{"x":-0.55,"y":0,"z": 0.30},"el":{"x":-0.60,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"lhand"}},
    {"name":"I'M FINE",   "R":{"sh":{"x":-0.80,"y":0,"z":-0.20},"el":{"x":-0.30,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"},   "L":"idle"},
    {"name":"PLEASE",     "R":{"sh":{"x":-0.28,"y":0,"z":-0.68},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0.18,"y":0,"z":0},"h":"flat"},"L":"idle"},
    {"name":"THANK YOU",  "R":{"sh":{"x":-1.25,"y":0,"z":-0.08},"el":{"x":0.05,"y":0,"z":0},"wr":{"x":-0.12,"y":0,"z":0},"h":"flat"},"L":"idle"},
    {"name":"SORRY",      "R":{"sh":{"x":-1.20,"y":0,"z":-0.15},"el":{"x":-0.10,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fist_A"},"L":"idle"},
    # ── Yes/No/Basic ─────────────────────────────────────────────────────────
    {"name":"YES",        "R":{"sh":{"x":-0.45,"y":0,"z":-0.10},"el":{"x":-0.95,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fist_S"},"L":"idle"},
    {"name":"NO",         "R":{"sh":{"x":-0.50,"y":0,"z":-0.14},"el":{"x":-0.88,"y":0,"z":0},"wr":{"x":0,"y":0.3,"z":0},"h":"vhand"},"L":"idle"},
    # ── Instructions ─────────────────────────────────────────────────────────
    {"name":"HELP",       "R":{"sh":{"x":-1.28,"y":0,"z":-0.30},"el":{"x":-0.50,"y":0,"z":0},"wr":{"x":0.12,"y":0,"z":0},"h":"fist_A"},
                          "L":{"sh":{"x":-1.20,"y":0,"z": 0.28},"el":{"x":-0.25,"y":0,"z":0},"wr":{"x":-0.65,"y":0.3,"z":0},"h":"flat"}},
    {"name":"WAIT",       "R":{"sh":{"x":-0.70,"y":0,"z":-0.24},"el":{"x":-1.28,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"open5"},
                          "L":{"sh":{"x":-0.70,"y":0,"z": 0.24},"el":{"x":-1.28,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"open5"}},
    {"name":"STOP",       "R":{"sh":{"x":-0.60,"y":0,"z":-0.18},"el":{"x":-1.10,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"},
                          "L":{"sh":{"x":-0.60,"y":0,"z": 0.18},"el":{"x":-1.10,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"}},
    {"name":"REPEAT",     "R":{"sh":{"x":-0.48,"y":0,"z":-0.22},"el":{"x":-0.78,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fist_A"},
                          "L":{"sh":{"x":-0.55,"y":0,"z": 0.35},"el":{"x":-0.40,"y":0,"z":0},"wr":{"x":-0.55,"y":0.2,"z":0},"h":"flat"}},
    {"name":"UNDERSTAND", "R":{"sh":{"x":-1.50,"y":0,"z":-0.06},"el":{"x":-0.18,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"point1"},"L":"idle"},
    {"name":"COME",       "R":{"sh":{"x":-0.55,"y":0,"z":-0.18},"el":{"x":-0.88,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"point1"},"L":"idle"},
    {"name":"GO",         "R":{"sh":{"x":-0.50,"y":0,"z":-0.22},"el":{"x":-0.80,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"point1"},"L":"idle"},
    # ── Medical ───────────────────────────────────────────────────────────────
    {"name":"WATER",      "R":{"sh":{"x":-1.38,"y":0,"z":-0.08},"el":{"x":-0.22,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"whand"},  "L":"idle"},
    {"name":"PAIN",       "R":{"sh":{"x":-0.32,"y":0,"z":-0.56},"el":{"x":-0.85,"y":0,"z":0.24},"wr":{"x":0,"y":0,"z":0},"h":"point1"},
                          "L":{"sh":{"x":-0.32,"y":0,"z": 0.56},"el":{"x":-0.85,"y":0,"z":-0.24},"wr":{"x":0,"y":0,"z":0},"h":"point1"}},
    {"name":"DOCTOR",     "R":{"sh":{"x":-0.90,"y":0,"z":-0.55},"el":{"x":-0.40,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"chand"},
                          "L":{"sh":{"x":-0.90,"y":0,"z": 0.55},"el":{"x":-0.40,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"chand"}},
    {"name":"NURSE",      "R":{"sh":{"x":-1.00,"y":0,"z":-0.45},"el":{"x":-0.30,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"uhand"},
                          "L":{"sh":{"x":-1.00,"y":0,"z": 0.45},"el":{"x":-0.30,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"uhand"}},
    {"name":"HOSPITAL",   "R":{"sh":{"x":-1.10,"y":0,"z":-0.45},"el":{"x":-0.35,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"uhand"},
                          "L":{"sh":{"x":-0.40,"y":0,"z": 0.30},"el":{"x":-0.50,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"}},
    {"name":"SICK",       "R":{"sh":{"x":-1.45,"y":0,"z":-0.10},"el":{"x":-0.15,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fhand"},
                          "L":{"sh":{"x":-0.22,"y":0,"z": 0.38},"el":{"x":-0.25,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fhand"}},
    {"name":"AMBULANCE",  "R":{"sh":{"x":-1.30,"y":0,"z":-0.35},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"},
                          "L":{"sh":{"x":-1.30,"y":0,"z": 0.35},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"}},
    {"name":"MEDICINE",   "R":{"sh":{"x":-0.65,"y":0,"z":-0.30},"el":{"x":-0.75,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"whand"},
                          "L":{"sh":{"x":-0.45,"y":0,"z": 0.35},"el":{"x":-0.55,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"}},
    {"name":"HURT",       "R":{"sh":{"x":-0.65,"y":0,"z":-0.30},"el":{"x":-0.70,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fist_S"},
                          "L":{"sh":{"x":-0.65,"y":0,"z": 0.30},"el":{"x":-0.70,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fist_S"}},
    {"name":"EMERGENCY",  "R":{"sh":{"x":-1.25,"y":0,"z":-0.38},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"},
                          "L":{"sh":{"x":-1.25,"y":0,"z": 0.38},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"}},
    # ── Emotions ──────────────────────────────────────────────────────────────
    {"name":"HAPPY",      "R":{"sh":{"x":-1.28,"y":0,"z":-0.12},"el":{"x":-0.15,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"yhand"},  "L":"idle"},
    {"name":"SAD",        "R":{"sh":{"x":-1.22,"y":0,"z":-0.10},"el":{"x":-0.15,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"chand"},  "L":"idle"},
    {"name":"ANGRY",      "R":{"sh":{"x":-0.20,"y":0,"z":-0.40},"el":{"x":-0.30,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"},   "L":"idle"},
    {"name":"SCARED",     "R":{"sh":{"x":-1.15,"y":0,"z":-0.20},"el":{"x":-0.25,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"},
                          "L":{"sh":{"x":-1.15,"y":0,"z": 0.20},"el":{"x":-0.25,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"claw"}},
    {"name":"LOVE",       "R":{"sh":{"x":-0.95,"y":0,"z":-0.40},"el":{"x":-0.20,"y":0,"z":0.35},"wr":{"x":0,"y":0,"z":0},"h":"fist_S"},
                          "L":{"sh":{"x":-0.95,"y":0,"z": 0.40},"el":{"x":-0.20,"y":0,"z":-0.35},"wr":{"x":0,"y":0,"z":0},"h":"fist_S"}},
    {"name":"I LOVE YOU", "R":{"sh":{"x":-0.90,"y":0,"z":-0.20},"el":{"x":-0.55,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"yhand"},  "L":"idle"},
    {"name":"TIRED",      "R":{"sh":{"x":-0.25,"y":0,"z":-0.40},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"open5"},
                          "L":{"sh":{"x":-0.25,"y":0,"z": 0.40},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"open5"}},
    {"name":"HUNGRY",     "R":{"sh":{"x":-0.30,"y":0,"z":-0.48},"el":{"x":-0.45,"y":0,"z":0},"wr":{"x":0.15,"y":0,"z":0},"h":"chand"},"L":"idle"},
    {"name":"THIRSTY",    "R":{"sh":{"x":-1.38,"y":0,"z":-0.06},"el":{"x":-0.20,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"chand"},  "L":"idle"},
    # ── Rights / Social ──────────────────────────────────────────────────────
    {"name":"RIGHTS",     "R":{"sh":{"x":-0.85,"y":0,"z":-0.30},"el":{"x":-0.50,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"fist_S"},"L":"idle"},
    {"name":"LAW",        "R":{"sh":{"x":-0.55,"y":0,"z":-0.35},"el":{"x":-0.60,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"},
                          "L":{"sh":{"x":-0.55,"y":0,"z": 0.35},"el":{"x":-0.60,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"flat"}},
    {"name":"EQUAL",      "R":{"sh":{"x":-0.45,"y":0,"z":-0.25},"el":{"x":-0.85,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"uhand"},
                          "L":{"sh":{"x":-0.45,"y":0,"z": 0.25},"el":{"x":-0.85,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"uhand"}},
    {"name":"LISTEN",     "R":{"sh":{"x":-1.45,"y":0,"z":-0.08},"el":{"x":-0.15,"y":0,"z":0},"wr":{"x":0,"y":0,"z":0},"h":"chand"},  "L":"idle"},
]

# ─── FORWARD KINEMATICS ───────────────────────────────────────────────────────

def _rot(rx, ry=0.0, rz=0.0):
    """Euler XYZ → 3×3 rotation matrix."""
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float32)
    return Rz @ Ry @ Rx


# Skeleton constants (from avatar.js buildAvatarSkeleton)
_SHOULDER_R = np.array([-0.34, 0.16, 0.0], dtype=np.float32)
_SHOULDER_L = np.array([ 0.34, 0.16, 0.0], dtype=np.float32)
_UPPER_ARM  = 0.36
_FOREARM    = 0.32
_PALM_LEN   = 0.10
_SEG_LENS   = [0.036, 0.030, 0.026]  # MCP→PIP, PIP→DIP, DIP→tip
_DOWN       = np.array([0.0, -1.0, 0.0], dtype=np.float32)

# Finger X offsets in palm local frame (from avatar.js buildFingers)
_FINGER_XOFFS_R = {"t": -0.062, "i": -0.030, "m": 0.001, "r": 0.032, "p": 0.062}
_FINGER_XOFFS_L = {"t":  0.062, "i":  0.030, "m":-0.001, "r":-0.032, "p":-0.062}
# MediaPipe point start index per finger
_MP_START = {"t": 1, "i": 5, "m": 9, "r": 13, "p": 17}


def arm_to_landmarks(shoulder_pos, sh, el, wr, hand_shape, side="R"):
    """
    Compute 21 MediaPipe-format 3D landmark positions for one arm.

    Returns (21, 3) float32 array.
    """
    sh_r = _rot(sh["x"], sh.get("y", 0.0), sh["z"])
    el_r = _rot(el["x"], el.get("y", 0.0), el.get("z", 0.0))
    wr_r = _rot(wr["x"], wr.get("y", 0.0), wr.get("z", 0.0))

    elbow  = shoulder_pos + sh_r @ (_DOWN * _UPPER_ARM)
    R_arm  = sh_r @ el_r
    wrist  = elbow + R_arm @ (_DOWN * _FOREARM)
    R_full = R_arm @ wr_r

    # Palm base (a little past the wrist)
    palm_base = wrist + R_full @ (_DOWN * 0.06)

    # Side vector of the hand (perpendicular to palm direction)
    palm_dir  = R_full @ _DOWN
    up        = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    side_vec  = np.cross(palm_dir, up)
    norm      = np.linalg.norm(side_vec)
    side_vec  = side_vec / norm if norm > 1e-4 else R_full @ np.array([1.0, 0.0, 0.0])

    xoffs = _FINGER_XOFFS_R if side == "R" else _FINGER_XOFFS_L

    pts = np.zeros((21, 3), dtype=np.float32)
    pts[0] = wrist

    for fkey in ("t", "i", "m", "r", "p"):
        curls = list(hand_shape.get(fkey, [0.15, 0.10, 0.08]))
        while len(curls) < 3:
            curls.append(0.0)

        start_idx = _MP_START[fkey]
        knuckle   = palm_base + side_vec * xoffs[fkey]
        pts[start_idx] = knuckle

        R_seg = R_full.copy()
        pos   = knuckle.copy()
        for seg in range(3):
            R_seg = R_seg @ _rot(float(curls[seg]))
            nxt   = pos + R_seg @ (_DOWN * _SEG_LENS[seg])
            pts[start_idx + seg + 1] = nxt
            pos = nxt

    return pts


def sign_to_frame(sign_def, noise_scale=0.0, rng=None):
    """
    Convert one sign definition → (42, 2) landmark frame.
    Hands 0-20 = left hand (HARPS format), 21-41 = right hand.
    """
    if rng is None:
        rng = np.random.default_rng(0)

    frame = np.zeros((42, 2), dtype=np.float32)

    # ── RIGHT arm ──────────────────────────────────────────────────────────
    rd = sign_def["R"]
    r_hs  = HS.get(rd["h"], HS["rest"])
    r_pts = arm_to_landmarks(_SHOULDER_R, rd["sh"], rd["el"], rd["wr"], r_hs, side="R")

    # ── LEFT arm ───────────────────────────────────────────────────────────
    ld = sign_def.get("L", "idle")
    if ld == "idle":
        l_arm = IDLE_L
        l_hs  = HS["rest"]
    else:
        l_arm = ld
        l_hs  = HS.get(ld["h"], HS["rest"])
    l_pts = arm_to_landmarks(_SHOULDER_L, l_arm["sh"], l_arm["el"], l_arm["wr"], l_hs, side="L")

    # Store X,Y (orthographic projection, camera looks from +Z)
    # Left hand → joints 0-20
    frame[:21, 0] = l_pts[:, 0]
    frame[:21, 1] = l_pts[:, 1]
    # Right hand → joints 21-41
    frame[21:, 0] = r_pts[:, 0]
    frame[21:, 1] = r_pts[:, 1]

    if noise_scale > 0:
        frame += rng.standard_normal(frame.shape).astype(np.float32) * noise_scale

    return frame


def lerp_frame(a, b, t):
    return a + (b - a) * t


def make_sign_sequence(sign_def, T=10, n_per_class=30, rng=None):
    """
    Generate n_per_class temporal sequences (each T frames) for one sign.
    Returns list of {"X": (T,42,2), "y": class_idx}.
    """
    if rng is None:
        rng = np.random.default_rng(0)

    # Base pose (target) with no noise
    idle_def = {
        "R": {**IDLE_R, "h": "rest"},
        "L": "idle",
    }
    idle_frame  = sign_to_frame(idle_def, noise_scale=0.0, rng=rng)
    sign_frame  = sign_to_frame(sign_def, noise_scale=0.0, rng=rng)

    samples = []
    for _ in range(n_per_class):
        seq = np.zeros((T, 42, 2), dtype=np.float32)

        # Phase 1 — transition: idle → sign (first half of frames)
        half = T // 2
        for t in range(half):
            alpha = (t + 1) / half
            # Cubic ease-in: matches TransitionEngine
            alpha_c = alpha * alpha * (3 - 2 * alpha)
            seq[t] = lerp_frame(idle_frame, sign_frame, alpha_c)

        # Phase 2 — hold with slight jitter (second half)
        for t in range(half, T):
            noise_scale = 0.004 + rng.uniform(0, 0.006)
            seq[t] = sign_to_frame(sign_def, noise_scale=noise_scale, rng=rng)

        # Normalise: person-centric (matches mediapipe_bridge.normalize_frame)
        for t in range(T):
            mean  = seq[t].mean(axis=0, keepdims=True)
            seq[t] -= mean
            scale  = np.abs(seq[t]).max()
            if scale > 0:
                seq[t] /= scale

        samples.append(seq)

    return samples


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="Generate HARPS training data from signs_library.js")
    p.add_argument("--epochs",      type=int, default=400)
    p.add_argument("--hidden_dim",  type=int, default=128)
    p.add_argument("--n_per_class", type=int, default=60,
                   help="Training frames per sign (more = better generalization)")
    p.add_argument("--T",           type=int, default=10,
                   help="Frames per sequence (must match HARPS_WINDOW)")
    p.add_argument("--seed",        type=int, default=42)
    p.add_argument("--device",      default="cpu")
    return p.parse_args()


def main():
    args = parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rng         = np.random.default_rng(args.seed)
    class_names = [s["name"] for s in SIGNS]
    n_classes   = len(class_names)

    print(f"HARPS Training from signs_library.js")
    print(f"  {n_classes} SASL sign classes")
    print(f"  {args.n_per_class} sequences per class × {args.T} frames")
    print(f"  hidden_dim: {args.hidden_dim}, epochs: {args.epochs}")
    print()

    # ── 1. Generate temporal sequences ──────────────────────────────────────
    print("Running forward kinematics on signs_library.js data...")
    all_samples = []
    for cls_idx, sign_def in enumerate(SIGNS):
        seqs = make_sign_sequence(
            sign_def, T=args.T, n_per_class=args.n_per_class, rng=rng
        )
        for seq in seqs:
            all_samples.append({"X": seq, "y": cls_idx})

    rng.shuffle(all_samples)
    print(f"  {len(all_samples)} total training sequences generated")

    # ── 2. Flatten to (N, D) feature array (SJ = simple flatten) ────────────
    print("Extracting SJ features (flatten)...")
    X_list, y_list = [], []
    for sample in all_samples:
        X_list.append(sample["X"].reshape(1, -1))
        y_list.append(sample["y"])

    X = np.vstack(X_list).astype(np.float32)
    y = np.array(y_list, dtype=np.int64)
    print(f"  Feature matrix: {X.shape}")

    # ── 3. Train / val split ─────────────────────────────────────────────────
    idx   = rng.permutation(len(y))
    split = int(0.85 * len(y))
    X_tr, y_tr = X[idx[:split]], y[idx[:split]]
    X_va, y_va = X[idx[split:]], y[idx[split:]]

    # ── 4. Scale ─────────────────────────────────────────────────────────────
    from backend.harps.utils import FeatureScaler
    scaler = FeatureScaler(mode="maxabs")
    X_tr   = scaler.fit_transform(X_tr)
    X_va   = scaler.transform(X_va)

    # ── 5. Train MLP ─────────────────────────────────────────────────────────
    from backend.harps.models import MLPClassifier
    from backend.harps.train  import MLPTrainer, TrainConfigMLP

    input_dim = X_tr.shape[1]
    model = MLPClassifier(
        input_dim   = input_dim,
        hidden_dim  = args.hidden_dim,
        num_classes = n_classes,
    )
    cfg = TrainConfigMLP(epochs=args.epochs, seed=args.seed, device=args.device)
    trainer = MLPTrainer(model, cfg)

    print(f"Training MLP ({input_dim} → {args.hidden_dim} → {n_classes})...")
    result = trainer.fit(
        X_tr, y_tr, X_va, y_va,
        checkpoint_path=str(OUTPUT_DIR / "model.pth"),
    )

    # ── 6. Evaluate ──────────────────────────────────────────────────────────
    from backend.harps.utils import compute_metrics
    y_pred  = trainer.predict(X_va)
    metrics = compute_metrics(y_va, y_pred)

    print(f"  train_acc  : {result['train_acc']:.4f}")
    print(f"  val_acc    : {metrics['accuracy']:.4f}")
    print(f"  f1_weighted: {metrics['f1_weighted']:.4f}")

    # ── 7. Save artefacts ────────────────────────────────────────────────────
    meta = {
        "class_names": class_names,
        "input_dim":   input_dim,
        "hidden_dim":  args.hidden_dim,
        "num_classes": n_classes,
        "feature_set": "SJ",
        "m_frames":    args.T,
        "scaler_mode": "maxabs",
        "train_acc":   result["train_acc"],
        "val_acc":     metrics["accuracy"],
        "accuracy":    metrics["accuracy"],
        "f1_weighted": metrics["f1_weighted"],
        "source":      "signs_library_fk",
    }
    with (OUTPUT_DIR / "meta.json").open("w") as f:
        json.dump(meta, f, indent=2)
    with (OUTPUT_DIR / "scaler.json").open("w") as f:
        json.dump(scaler.to_dict(), f, indent=2)

    try:
        fig = trainer.tracker.plot_4panel(lambda_note="SJ_from_library")
        fig.savefig(str(OUTPUT_DIR / "convergence.png"), dpi=100)
        import matplotlib.pyplot as plt; plt.close(fig)
    except Exception:
        pass

    print()
    print(f"Model saved to {OUTPUT_DIR}/")
    print(f"Classes: {class_names[:8]}...")
    print("Restart the backend to load the new model.")


if __name__ == "__main__":
    main()