"""Ollama client for AMANDLA text-to-signs mapping.

classify_text_to_signs(text) -> list[str]
  Tries the local 'amandla' Ollama model first, falls back to the
  rule-based word map in backend.main if Ollama is unavailable.
"""
import os
import re
import json
import logging

logger = logging.getLogger(__name__)

# ── rule-based fallback (mirrors _WORD_MAP / _PHRASE_MAP in main.py) ──────────
# NOTE: main.py holds the canonical, more complete copy. Keep these in sync.

_PHRASE_MAP = {
    "how are you":  ["HOW ARE YOU"],
    "i'm fine":     ["I'M FINE"],
    "im fine":      ["I'M FINE"],
    "i love you":   ["I LOVE YOU"],
    "thank you":    ["THANK YOU"],
    "good morning": ["GOOD", "MORNING"],
    "good night":   ["GOOD", "NIGHT"],
    "good bye":     ["GOODBYE"],
}

_WORD_MAP = {
    "hi": "HELLO", "hello": "HELLO", "hey": "HELLO", "greetings": "HELLO",
    "howzit": "HELLO",
    "bye": "GOODBYE", "goodbye": "GOODBYE", "farewell": "GOODBYE",
    "see you": "GOODBYE", "take care": "GOODBYE",
    "thanks": "THANK YOU", "thank": "THANK YOU", "cheers": "THANK YOU",
    "please": "PLEASE", "pls": "PLEASE",
    "yes": "YES", "ok": "YES", "okay": "YES", "yep": "YES", "yup": "YES",
    "correct": "YES", "affirmative": "YES",
    "no": "NO", "nope": "NO", "nah": "NO", "not": "NO",
    "sorry": "SORRY", "apologies": "SORRY",
    "help": "HELP", "assist": "HELP", "assistance": "HELP",
    "stop": "STOP", "halt": "STOP",
    "wait": "WAIT", "hold on": "WAIT",
    "repeat": "REPEAT", "again": "REPEAT",
    "understand": "UNDERSTAND", "understood": "UNDERSTAND", "got it": "UNDERSTAND",
    "water": "WATER", "drink": "DRINK", "drinking": "DRINK",
    "pain": "PAIN", "painful": "PAIN", "sore": "PAIN", "ache": "PAIN",
    "hurt": "HURT", "hurts": "HURT",
    "emergency": "EMERGENCY",
    "doctor": "DOCTOR", "dr": "DOCTOR", "physician": "DOCTOR",
    "nurse": "NURSE",
    "hospital": "HOSPITAL", "clinic": "HOSPITAL",
    "sick": "SICK", "ill": "SICK", "unwell": "SICK",
    "medicine": "MEDICINE", "medication": "MEDICINE", "pills": "MEDICINE",
    "ambulance": "AMBULANCE",
    "fire": "FIRE", "burning": "FIRE",
    "dangerous": "DANGEROUS", "danger": "DANGEROUS", "hazard": "DANGEROUS",
    "careful": "CAREFUL", "caution": "CAREFUL",
    "safe": "SAFE", "safety": "SAFE",
    "happy": "HAPPY", "joyful": "HAPPY", "glad": "HAPPY", "joy": "HAPPY",
    "sad": "SAD", "unhappy": "SAD", "upset": "SAD", "depressed": "SAD",
    "angry": "ANGRY", "mad": "ANGRY", "furious": "ANGRY",
    "scared": "SCARED", "afraid": "SCARED", "frightened": "SCARED",
    "love": "LOVE",
    "excited": "EXCITED",
    "tired": "TIRED", "exhausted": "TIRED", "sleepy": "TIRED",
    "hungry": "HUNGRY", "starving": "HUNGRY",
    "thirsty": "THIRSTY",
    "worried": "WORRIED", "anxious": "WORRIED", "nervous": "WORRIED",
    "confused": "CONFUSED",
    "who": "WHO", "what": "WHAT", "where": "WHERE", "when": "WHEN",
    "why": "WHY", "how": "HOW", "which": "WHICH",
    "i": "I", "me": "I", "my": "I",
    "you": "YOU", "your": "YOU",
    "we": "WE", "us": "WE",
    "they": "THEY", "them": "THEY",
    "come": "COME", "go": "GO",
    "listen": "LISTEN", "hear": "LISTEN",
    "look": "LOOK", "see": "LOOK",
    "know": "KNOW",
    "want": "WANT", "need": "WANT",
    "give": "GIVE",
    "eat": "EAT", "food": "FOOD",
    "sleep": "SLEEP",
    "sit": "SIT", "stand": "STAND",
    "walk": "WALK", "run": "RUN",
    "work": "WORK", "job": "WORK",
    "wash": "WASH",
    "write": "WRITE", "read": "READ",
    "open": "OPEN", "close": "CLOSE",
    "tell": "TELL", "say": "TELL", "speak": "TELL", "talk": "TELL",
    "laugh": "LAUGH", "cry": "CRY", "hug": "HUG",
    "sign": "SIGN", "signing": "SIGN",
    "good": "GOOD", "great": "GOOD", "nice": "GOOD", "fine": "GOOD",
    "bad": "BAD", "wrong": "BAD",
    "big": "BIG", "large": "BIG",
    "small": "SMALL", "little": "SMALL",
    "hot": "HOT", "warm": "HOT",
    "cold": "COLD", "cool": "COLD",
    "quiet": "QUIET", "silent": "QUIET",
    "fast": "FAST", "quick": "FAST",
    "slow": "SLOW",
    "home": "HOME", "house": "HOME",
    "school": "SCHOOL",
    "family": "FAMILY",
    "mom": "MOM", "mother": "MOM", "mum": "MOM",
    "dad": "DAD", "father": "DAD",
    "baby": "BABY",
    "friend": "FRIEND", "buddy": "FRIEND",
    "child": "CHILD", "kid": "CHILD",
    "person": "PERSON", "people": "PERSON",
    "money": "MONEY", "cash": "MONEY",
    "free": "FREE",
    "rights": "RIGHTS",
    "law": "LAW", "legal": "LAW",
    "equal": "EQUAL", "equality": "EQUAL",
    "car": "CAR", "drive": "CAR",
    "taxi": "TAXI",
    "bus": "BUS",
    "today": "TODAY", "now": "NOW",
    "morning": "MORNING", "night": "NIGHT",
}

_FILLER = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "for", "on", "with", "at", "by", "as", "it", "its",
    "this", "that", "these", "those", "and", "but", "or", "so", "if",
    "um", "uh", "ah", "oh", "hmm", "like", "just", "really", "very",
}


def _rule_based_signs(text: str) -> list:
    """Pure rule-based text → SASL sign name list (no network required)."""
    if not text:
        return []

    lower = text.lower().strip()

    # Phrase-level pass
    for phrase, signs in _PHRASE_MAP.items():
        if phrase in lower:
            return signs

    # Word-level pass
    words = re.sub(r"[^a-z0-9\s']", " ", lower).split()
    result = []
    i = 0
    while i < len(words):
        w = words[i]
        # Try 2-word phrase
        if i + 1 < len(words):
            two = w + " " + words[i + 1]
            if two in _PHRASE_MAP:
                result.extend(_PHRASE_MAP[two])
                i += 2
                continue
        if w in _FILLER:
            i += 1
            continue
        if w in _WORD_MAP:
            result.append(_WORD_MAP[w])
        else:
            # Fingerspell unknown word
            for ch in w.upper():
                if "A" <= ch <= "Z":
                    result.append(ch)
        i += 1

    return result


async def classify_text_to_signs(text: str) -> list:
    """Convert English text to an ordered list of SASL sign name strings.

    Fallback chain: Ollama (local AI) → Gemini (cloud AI) → rule-based word map.

    Args:
        text: Transcribed English sentence from hearing user.

    Returns:
        Ordered list of SASL sign name strings (e.g. ["HELLO", "HOW ARE YOU"]).
    """
    if not text:
        return []

    # 1. Try local Ollama model
    ollama_result = await _try_ollama(text)
    if ollama_result is not None:
        return ollama_result

    # 2. Try Gemini (cloud)
    try:
        from backend.services.gemini_service import classify_text_to_signs as gemini_signs
        gemini_result = await gemini_signs(text)
        if gemini_result is not None:
            return gemini_result
    except Exception as e:
        logger.debug(f"[OllamaClient] Gemini text-to-signs unavailable: {e}")

    # 3. Rule-based fallback
    return _rule_based_signs(text)


async def _try_ollama(text: str):
    """Call the local Ollama amandla model. Returns list or None on failure."""
    try:
        import httpx
        from dotenv import load_dotenv
        load_dotenv()

        base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        model = os.getenv("OLLAMA_MODEL", "amandla")

        prompt = (
            f'Convert this English sentence to SASL sign names.\n'
            f'Sentence: "{text}"\n'
            f'Reply ONLY with a JSON array of uppercase sign name strings.\n'
            f'Valid signs: HELLO, GOODBYE, PLEASE, THANK YOU, SORRY, YES, NO, HELP, '
            f'WAIT, STOP, REPEAT, UNDERSTAND, WATER, PAIN, HURT, DOCTOR, NURSE, '
            f'HOSPITAL, SICK, MEDICINE, AMBULANCE, EMERGENCY, HAPPY, SAD, ANGRY, '
            f'SCARED, LOVE, I LOVE YOU, TIRED, HUNGRY, THIRSTY, WORRIED, CONFUSED, '
            f'WHO, WHAT, WHERE, WHEN, WHY, HOW, I, YOU, WE, THEY, COME, GO, LISTEN, '
            f'LOOK, KNOW, WANT, GIVE, EAT, DRINK, SLEEP, SIT, STAND, WALK, RUN, WORK, '
            f'WASH, WRITE, READ, SIGN, TELL, LAUGH, CRY, HUG, OPEN, CLOSE, GOOD, BAD, '
            f'BIG, SMALL, HOT, COLD, QUIET, FAST, SLOW, HOME, SCHOOL, FAMILY, MOM, '
            f'DAD, BABY, FRIEND, CHILD, MONEY, FREE, RIGHTS, LAW, EQUAL, CAR, TAXI, '
            f'BUS, TODAY, NOW, MORNING, NIGHT.\n'
            f'Example: ["HELLO", "HOW ARE YOU"]'
        )

        async with httpx.AsyncClient(timeout=6.0) as client:
            r = await client.post(
                f"{base}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False, "temperature": 0.1}
            )
            if r.status_code != 200:
                return None

            raw = r.json().get("response", "").strip()

            start = raw.find("[")
            end = raw.rfind("]") + 1
            if start < 0 or end <= start:
                return None

            signs = json.loads(raw[start:end])
            if isinstance(signs, list) and all(isinstance(s, str) for s in signs):
                return [s.upper() for s in signs]

    except Exception as e:
        logger.debug(f"[OllamaClient] Ollama text-to-signs unavailable: {e}")

    return None