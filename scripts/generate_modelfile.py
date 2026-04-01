"""Generate an updated Modelfile for the amandla Ollama model.

Reads all unique sign names from backend/services/sign_maps.py (WORD_MAP
and PHRASE_MAP) and writes a new Modelfile that teaches the Ollama model
the full sign inventory.

Usage:
    python scripts/generate_modelfile.py

After running, rebuild the model with:
    ollama create amandla -f Modelfile
"""

import os
import sys

# Ensure the project root is on the path so we can import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.sign_maps import WORD_MAP, PHRASE_MAP

MODELFILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Modelfile",
)


def collect_sign_names() -> list[str]:
    """Extract and sort all unique sign names from WORD_MAP and PHRASE_MAP.

    Returns:
        Sorted list of unique SASL sign name strings (e.g. ['AMBULANCE', ...]).
    """
    names: set[str] = set()

    # WORD_MAP values are single sign name strings
    for sign_name in WORD_MAP.values():
        names.add(sign_name)

    # PHRASE_MAP values are lists of sign name strings
    for sign_list in PHRASE_MAP.values():
        for sign_name in sign_list:
            names.add(sign_name)

    return sorted(names)


def build_modelfile(sign_names: list[str]) -> str:
    """Render the Modelfile content with the full sign inventory.

    Args:
        sign_names: Sorted list of unique sign name strings.

    Returns:
        The complete Modelfile text as a string.
    """
    signs_line = ", ".join(sign_names)
    count = len(sign_names)

    return f'''FROM qwen2.5:3b

SYSTEM """
You are AMANDLA's sign language recognition engine.

Your job is to receive hand landmark data from MediaPipe and identify which South African Sign Language (SASL) sign is being made.

You will receive JSON data with 21 landmark points per hand. Each point has an id (0-20), x, y, z coordinates (0.0 to 1.0 normalised), and a name.

The 21 MediaPipe landmarks are:
0=WRIST, 1=THUMB_CMC, 2=THUMB_MCP, 3=THUMB_IP, 4=THUMB_TIP,
5=INDEX_FINGER_MCP, 6=INDEX_FINGER_PIP, 7=INDEX_FINGER_DIP, 8=INDEX_FINGER_TIP,
9=MIDDLE_FINGER_MCP, 10=MIDDLE_FINGER_PIP, 11=MIDDLE_FINGER_DIP, 12=MIDDLE_FINGER_TIP,
13=RING_FINGER_MCP, 14=RING_FINGER_PIP, 15=RING_FINGER_DIP, 16=RING_FINGER_TIP,
17=PINKY_MCP, 18=PINKY_PIP, 19=PINKY_DIP, 20=PINKY_TIP

When given landmark data, respond ONLY with a JSON object in this exact format:
{{"sign": "SIGN_NAME", "confidence": 0.85, "description": "one line description of the handshape"}}

The {count} signs you must recognise: {signs_line}

If you cannot identify the sign with confidence above 0.5, return:
{{"sign": "UNKNOWN", "confidence": 0.0, "description": "Sign not recognised"}}

Never add any text outside the JSON. Never explain. Never apologise. Only JSON.
"""

PARAMETER temperature 0.1
PARAMETER top_p 0.9
PARAMETER num_predict 100
'''


def main() -> None:
    """Read sign maps, generate Modelfile content, and write to disk."""
    sign_names = collect_sign_names()
    print(f"[generate_modelfile] Collected {len(sign_names)} unique sign names.")

    content = build_modelfile(sign_names)

    with open(MODELFILE_PATH, "w", encoding="utf-8") as fh:
        fh.write(content)

    print(f"[generate_modelfile] Written to: {MODELFILE_PATH}")
    print()
    print("Next step — rebuild the Ollama model:")
    print("    ollama create amandla -f Modelfile")


if __name__ == "__main__":
    main()