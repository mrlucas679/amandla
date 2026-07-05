"""Shared SASL word/phrase mappings for text → sign name conversion.

This is the SINGLE SOURCE OF TRUTH for word-level and phrase-level
English → SASL sign name mappings. Both backend.main and
backend.services.ollama_client import from here.

Do NOT duplicate these maps elsewhere. If you need to add a mapping,
add it here.
"""

import re

# ── Phrase-level mappings (checked before word tokenization) ──────────

PHRASE_MAP = {
    "how are you":  ["HOW ARE YOU"],
    "i'm fine":     ["I'M FINE"],
    "im fine":      ["I'M FINE"],
    "i love you":   ["I LOVE YOU"],
    "thank you":    ["THANK YOU"],
    "good morning": ["GOOD", "MORNING"],
    "good night":   ["GOOD", "NIGHT"],
    "good bye":     ["GOODBYE"],
    # Modal / obligation phrases — map to single SASL sign
    "have to":      ["MUST"],
    "need to":      ["MUST"],
    "ought to":     ["MUST"],
    "able to":      ["CAN"],
    "going to":     ["WILL"],
    # Ability negation
    "can not":      ["CAN NOT"],
    "can't":        ["CAN NOT"],
    "cannot":       ["CAN NOT"],
    # Disability / communication (Section 11 research)
    "hearing person": ["HEARING"],
    "sign language":  ["SIGN"],
    "stomach ache":   ["PAIN"],
    # South African dialect phrases (QUAL-5)
    "baie dankie":    ["THANK YOU"],
    "ag shame":       ["SORRY"],
    "just now":       ["WAIT"],
    "now now":        ["NOW"],
    "no ways":        ["NO"],
    "no way":         ["NO"],
    "for sure":       ["YES"],
    "eish no":        ["BAD", "NO"],
    # SA informal greetings
    "how's it":       ["HOW ARE YOU"],
    "howzit":         ["HOW ARE YOU"],
    "is it":          ["YES"],
    "sharp sharp":    ["GOOD"],

    # Extended greetings / social
    "how are you doing":   ["HOW ARE YOU"],
    "how is it going":     ["HOW ARE YOU"],
    "how do you do":       ["HOW ARE YOU"],
    "nice to meet you":    ["GOOD", "MEET", "YOU"],
    "see you later":       ["SEE", "LATER"],
    "good afternoon":      ["GOOD", "NOW"],
    "good evening":        ["GOOD", "NIGHT"],
    "excuse me":           ["SORRY"],
    "i am sorry":          ["SORRY"],

    # Common needs / requests
    "i need help":         ["I", "HELP", "WANT"],
    "i don't understand":  ["I", "UNDERSTAND", "NOT"],
    "i do not understand": ["I", "UNDERSTAND", "NOT"],
    "i don't know":        ["I", "KNOW", "NOT"],
    "i do not know":       ["I", "KNOW", "NOT"],
    "can you help me":     ["YOU", "CAN", "HELP"],
    "i want to go":        ["I", "GO", "WANT"],
    "i need to go":        ["I", "GO", "MUST"],
    "i am sick":           ["I", "SICK"],
    "i am hungry":         ["I", "HUNGRY"],
    "i am thirsty":        ["I", "THIRSTY"],
    "i am tired":          ["I", "TIRED"],
    "i am scared":         ["I", "SCARED"],
    "i am happy":          ["I", "HAPPY"],
    "i am sad":            ["I", "SAD"],
    "i am fine":           ["I'M FINE"],
    "i am okay":           ["I'M FINE"],

    # Medical emergencies
    "i am in pain":        ["I", "PAIN"],
    "call an ambulance":   ["AMBULANCE", "CALL"],
    "i need a doctor":     ["DOCTOR", "I", "WANT"],
    "i need medicine":     ["MEDICINE", "I", "WANT"],
    "call the police":     ["POLICE", "CALL"],
    "i need water":        ["WATER", "I", "WANT"],
    "i cannot breathe":    ["I", "SICK", "CAN NOT"],

    # Rights / legal
    "i have rights":       ["I", "RIGHTS", "HAVE"],
    "i need an interpreter": ["INTERPRETER", "I", "WANT"],
    "sign language interpreter": ["SIGN", "INTERPRETER"],
}

# ── Word-level mappings ──────────────────────────────────────────────

WORD_MAP = {
    # ── Greetings ──────────────────────────────────────────
    "hi": "HELLO", "hello": "HELLO", "hey": "HELLO", "greetings": "HELLO", "howzit": "HELLO",
    "bye": "GOODBYE", "goodbye": "GOODBYE", "farewell": "GOODBYE",
    "i'm fine": "I'M FINE", "im fine": "I'M FINE",
    "i love you": "I LOVE YOU",
    "thanks": "THANK YOU", "thank": "THANK YOU", "thank you": "THANK YOU", "cheers": "THANK YOU",
    "please": "PLEASE", "pls": "PLEASE",
    "sorry": "SORRY", "apologies": "SORRY", "my bad": "SORRY", "excuse": "SORRY",

    # ── Confirmation / Negation ──────────────────────────────
    "yes": "YES", "ok": "YES", "okay": "YES", "yep": "YES", "yup": "YES",
    "correct": "YES", "affirmative": "YES", "sure": "YES",
    "no": "NO", "nope": "NO", "nah": "NO",
    # "not" is the SASL negation marker — distinct from the answer "no"
    "not": "NOT", "never": "NOT",
    "nobody": "NO", "nothing": "NO", "none": "NO",
    "don't": "NOT", "dont": "NOT", "doesn't": "NOT", "doesnt": "NOT",
    "didn't": "NOT", "didnt": "NOT",
    "won't": "NOT", "wont": "NOT", "isn't": "NOT", "isnt": "NOT",
    "aren't": "NOT", "arent": "NOT", "wasn't": "NOT", "wasnt": "NOT",
    "weren't": "NOT", "werent": "NOT", "shouldn't": "NOT", "shouldnt": "NOT",
    "wouldn't": "NOT", "wouldnt": "NOT", "couldn't": "NOT", "couldnt": "NOT",

    # ── Instructions ────────────────────────────────────────
    "help": "HELP", "assist": "HELP", "assistance": "HELP", "helping": "HELP",
    "stop": "STOP", "halt": "STOP", "stopping": "STOP", "stopped": "STOP",
    "wait": "WAIT", "waiting": "WAIT", "hold on": "WAIT", "later": "WAIT",
    "repeat": "REPEAT", "again": "REPEAT", "say again": "REPEAT",
    "understand": "UNDERSTAND", "understood": "UNDERSTAND", "understanding": "UNDERSTAND",

    # ── Medical ─────────────────────────────────────────────
    "water": "WATER",
    "pain": "PAIN", "painful": "PAIN", "sore": "PAIN", "ache": "PAIN", "aching": "PAIN",
    "headache": "PAIN", "stomachache": "PAIN",
    "hurt": "HURT", "hurts": "HURT", "hurting": "HURT", "injured": "HURT",
    "emergency": "EMERGENCY",
    "doctor": "DOCTOR", "dr": "DOCTOR", "physician": "DOCTOR", "doc": "DOCTOR",
    "stethoscope": "DOCTOR",
    "nurse": "NURSE", "nurses": "NURSE",
    "hospital": "HOSPITAL", "clinic": "HOSPITAL", "hospitals": "HOSPITAL",
    "sick": "SICK", "ill": "SICK", "unwell": "SICK", "nauseous": "SICK", "nausea": "SICK",
    "fever": "SICK", "temperature": "SICK", "cough": "SICK", "coughing": "SICK",
    "allergy": "SICK", "allergic": "SICK", "rash": "SICK",
    "medicine": "MEDICINE", "medication": "MEDICINE", "pills": "MEDICINE",
    "tablet": "MEDICINE", "tablets": "MEDICINE", "drug": "MEDICINE", "drugs": "MEDICINE",
    "injection": "MEDICINE", "shot": "MEDICINE", "jab": "MEDICINE", "needle": "MEDICINE",
    "prescription": "MEDICINE", "dosage": "MEDICINE", "dose": "MEDICINE",
    "ambulance": "AMBULANCE",
    # ── Disability / communication (Section 11 research) ────
    "deaf": "DEAF", "deafness": "DEAF",
    "blind": "BLIND", "blindness": "BLIND", "visually impaired": "BLIND",
    "disability": "DISABILITY", "disabled": "DISABILITY", "wheelchair": "DISABILITY",
    "hearing person": "HEARING",
    "sign language": "SIGN", "interpreter": "SIGN", "sasl": "SIGN",
    "fire": "FIRE", "burning": "FIRE", "flames": "FIRE",
    "dangerous": "DANGEROUS", "danger": "DANGEROUS", "hazard": "DANGEROUS",
    "careful": "CAREFUL", "caution": "CAREFUL", "watch out": "CAREFUL",
    "safe": "SAFE", "safety": "SAFE",

    # ── Emotions ────────────────────────────────────────────
    "happy": "HAPPY", "joyful": "HAPPY", "glad": "HAPPY", "joy": "HAPPY",
    "cheerful": "HAPPY", "pleased": "HAPPY", "delighted": "HAPPY",
    "sad": "SAD", "unhappy": "SAD", "upset": "SAD", "depressed": "SAD",
    "miserable": "SAD", "gloomy": "SAD", "heartbroken": "SAD",
    "angry": "ANGRY", "mad": "ANGRY", "furious": "ANGRY",
    "annoyed": "ANGRY", "rage": "ANGRY", "irritated": "ANGRY",
    "scared": "SCARED", "afraid": "SCARED", "frightened": "SCARED",
    "fear": "SCARED", "terrified": "SCARED", "panic": "SCARED",
    "love": "LOVE", "loving": "LOVE",
    "excited": "EXCITED", "exciting": "EXCITED", "thrilled": "EXCITED",
    "tired": "TIRED", "exhausted": "TIRED", "sleepy": "TIRED",
    "fatigue": "TIRED", "weary": "TIRED",
    "hungry": "HUNGRY", "starving": "HUNGRY", "famished": "HUNGRY",
    "thirsty": "THIRSTY", "thirst": "THIRSTY",
    "worried": "WORRIED", "anxious": "WORRIED", "nervous": "WORRIED",
    "stressed": "WORRIED", "stress": "WORRIED", "worry": "WORRIED",
    "proud": "PROUD", "pride": "PROUD",
    "confused": "CONFUSED", "confusing": "CONFUSED",
    "puzzled": "CONFUSED", "baffled": "CONFUSED",

    # ── Question words ───────────────────────────────────────
    "who": "WHO", "what": "WHAT", "where": "WHERE", "when": "WHEN",
    "why": "WHY", "how": "HOW", "which": "WHICH",

    # ── Pronouns ────────────────────────────────────────────
    "i": "I", "me": "I", "my": "I", "mine": "I", "myself": "I",
    "you": "YOU", "your": "YOU", "yours": "YOU",
    "we": "WE", "us": "WE", "our": "WE",
    "they": "THEY", "them": "THEY", "their": "THEY",
    "he": "THEY", "she": "THEY", "his": "THEY", "her": "THEY",

    # ── Verbs (all common forms) ─────────────────────────────
    "come": "COME", "comes": "COME", "coming": "COME", "came": "COME",
    "bring": "COME", "brings": "COME", "brought": "COME",
    "go": "GO", "goes": "GO", "going": "GO", "went": "GO", "gone": "GO",
    "leave": "GO", "leaving": "GO", "left": "GO",
    "listen": "LISTEN", "listens": "LISTEN", "listening": "LISTEN", "listened": "LISTEN",
    "hear": "LISTEN", "hearing": "LISTEN", "heard": "LISTEN",
    "look": "LOOK", "looks": "LOOK", "looking": "LOOK", "looked": "LOOK",
    "see": "LOOK", "sees": "LOOK", "seeing": "LOOK", "saw": "LOOK", "seen": "LOOK",
    "watch": "LOOK", "watching": "LOOK", "watched": "LOOK",
    "find": "LOOK", "finding": "LOOK", "found": "LOOK",
    "show": "LOOK", "showing": "LOOK", "showed": "LOOK",
    "know": "KNOW", "knows": "KNOW", "knowing": "KNOW", "knew": "KNOW",
    "think": "KNOW", "thinks": "KNOW", "thinking": "KNOW", "thought": "KNOW",
    "believe": "KNOW", "believes": "KNOW", "believed": "KNOW",
    "understands": "UNDERSTAND",
    "want": "WANT", "wants": "WANT", "wanting": "WANT", "wanted": "WANT",
    "need": "WANT", "needs": "WANT", "needing": "WANT", "needed": "WANT",
    "require": "WANT", "requires": "WANT", "required": "WANT",
    "get": "WANT", "gets": "WANT",
    "take": "WANT", "takes": "WANT", "taking": "WANT", "took": "WANT",
    "give": "GIVE", "gives": "GIVE", "giving": "GIVE", "gave": "GIVE", "given": "GIVE",
    "eat": "EAT", "eats": "EAT", "eating": "EAT", "ate": "EAT", "eaten": "EAT",
    "drink": "DRINK", "drinks": "DRINK", "drinking": "DRINK",
    "drank": "DRINK", "drunk": "DRINK",
    "sleep": "SLEEP", "sleeps": "SLEEP", "sleeping": "SLEEP", "slept": "SLEEP",
    "rest": "SLEEP", "resting": "SLEEP",
    "sit": "SIT", "sits": "SIT", "sitting": "SIT", "sat": "SIT",
    "seat": "SIT", "seated": "SIT",
    "stand": "STAND", "stands": "STAND", "standing": "STAND", "stood": "STAND",
    "walk": "WALK", "walks": "WALK", "walking": "WALK", "walked": "WALK",
    "run": "RUN", "runs": "RUN", "running": "RUN", "ran": "RUN",
    "work": "WORK", "works": "WORK", "working": "WORK", "worked": "WORK",
    "job": "WORK", "jobs": "WORK", "labour": "WORK", "labor": "WORK",
    "wash": "WASH", "washes": "WASH", "washing": "WASH", "washed": "WASH",
    "clean": "WASH", "cleaning": "WASH", "cleaned": "WASH",
    "write": "WRITE", "writes": "WRITE", "writing": "WRITE",
    "wrote": "WRITE", "written": "WRITE",
    "read": "READ", "reads": "READ", "reading": "READ",
    "open": "OPEN", "opens": "OPEN", "opening": "OPEN", "opened": "OPEN",
    "close": "CLOSE", "closes": "CLOSE", "closing": "CLOSE",
    "closed": "CLOSE", "shut": "CLOSE",
    "tell": "TELL", "tells": "TELL", "telling": "TELL", "told": "TELL",
    "say": "TELL", "says": "TELL", "saying": "TELL", "said": "TELL",
    "speak": "TELL", "speaks": "TELL", "speaking": "TELL", "spoke": "TELL",
    "talk": "TELL", "talks": "TELL", "talking": "TELL", "talked": "TELL",
    "call": "TELL",
    "sign": "SIGN", "signs": "SIGN", "signing": "SIGN", "signed": "SIGN",
    "laugh": "LAUGH", "laughs": "LAUGH", "laughing": "LAUGH", "laughed": "LAUGH",
    "cry": "CRY", "cries": "CRY", "crying": "CRY", "cried": "CRY",
    "weep": "CRY", "weeping": "CRY", "wept": "CRY",
    "hug": "HUG", "hugs": "HUG", "hugging": "HUG", "hugged": "HUG",

    # ── Descriptions ────────────────────────────────────────
    "good": "GOOD", "great": "GOOD", "nice": "GOOD", "fine": "GOOD",
    "well": "GOOD", "wonderful": "GOOD", "excellent": "GOOD",
    "bad": "BAD", "terrible": "BAD", "awful": "BAD", "wrong": "BAD",
    "big": "BIG", "large": "BIG", "huge": "BIG", "giant": "BIG",
    "small": "SMALL", "little": "SMALL", "tiny": "SMALL",
    "hot": "HOT", "warm": "HOT", "boiling": "HOT",
    "cold": "COLD", "cool": "COLD", "freezing": "COLD", "chilly": "COLD",
    "quiet": "QUIET", "silent": "QUIET", "shh": "QUIET", "silence": "QUIET",
    "fast": "FAST", "quick": "FAST", "quickly": "FAST", "rapid": "FAST",
    "slow": "SLOW", "slowly": "SLOW",

    # ── People / family ─────────────────────────────────────
    "family": "FAMILY", "families": "FAMILY",
    "mom": "MOM", "mother": "MOM", "mum": "MOM", "mama": "MOM",
    "dad": "DAD", "father": "DAD", "papa": "DAD",
    "baby": "BABY", "infant": "BABY",
    "friend": "FRIEND", "friends": "FRIEND", "buddy": "FRIEND", "mate": "FRIEND",
    "child": "CHILD", "kid": "CHILD", "children": "CHILD", "kids": "CHILD",
    "person": "PERSON", "people": "PERSON", "man": "PERSON",
    "woman": "PERSON", "men": "PERSON", "women": "PERSON",
    "teacher": "TEACHER", "teachers": "TEACHER", "instructor": "TEACHER",

    # ── Places ──────────────────────────────────────────────
    "home": "HOME", "house": "HOME",
    "school": "SCHOOL", "class": "SCHOOL", "classroom": "SCHOOL",
    "church": "CHURCH",
    "police": "POLICE", "cop": "POLICE", "officer": "POLICE",

    # ── Money ───────────────────────────────────────────────
    "money": "MONEY", "cash": "MONEY", "rand": "MONEY",
    "pay": "MONEY", "paying": "MONEY", "paid": "MONEY",
    "cost": "EXPENSIVE", "expensive": "EXPENSIVE", "costly": "EXPENSIVE",
    "price": "EXPENSIVE",
    "free": "FREE", "no charge": "FREE",
    "share": "SHARE", "sharing": "SHARE", "shared": "SHARE",

    # ── Nature ──────────────────────────────────────────────
    "rain": "RAIN", "raining": "RAIN", "rainy": "RAIN",
    "sun": "SUN", "sunny": "SUN", "sunshine": "SUN",
    "wind": "WIND", "windy": "WIND",
    "tree": "TREE", "trees": "TREE",

    # ── Food ────────────────────────────────────────────────
    "food": "FOOD", "meal": "FOOD", "meals": "FOOD",
    "bread": "BREAD",

    # ── Transport ───────────────────────────────────────────
    "car": "CAR", "vehicle": "CAR", "drive": "CAR", "driving": "CAR",
    "taxi": "TAXI", "uber": "TAXI", "minibus": "TAXI",
    "bus": "BUS",

    # ── Rights ──────────────────────────────────────────────
    "rights": "RIGHTS", "right": "RIGHTS",
    "law": "LAW", "legal": "LAW", "legislation": "LAW",
    "equal": "EQUAL", "equality": "EQUAL", "fair": "EQUAL",

    # ── World / Global ──────────────────────────────────────
    "world": "WORLD", "global": "WORLD", "earth": "WORLD", "international": "WORLD",
    "worldwide": "WORLD", "globe": "WORLD",

    # ── Time ────────────────────────────────────────────────
    "year": "YEAR", "years": "YEAR", "annual": "YEAR", "annually": "YEAR", "yearly": "YEAR",
    "today": "TODAY", "now": "NOW", "currently": "NOW", "soon": "NOW",
    "morning": "MORNING",
    # Note: "afternoon" has no dedicated sign in the current library and is
    # intentionally omitted so it falls through to fingerspelling.
    "evening": "NIGHT", "night": "NIGHT", "tonight": "NIGHT",
    "yesterday": "YESTERDAY",
    "tomorrow": "TOMORROW",

    # ── South African English & Afrikaans dialect terms (QUAL-5) ────────
    # Common SA informal and Afrikaans words that hearing users may type.
    # Maps to the closest available SASL sign.
    "lekker": "GOOD",            # Afrikaans: nice/great/enjoyable
    "kiff": "GOOD",              # Cape slang: cool/great
    "sharp": "GOOD",             # SA: great/okay/agreed
    "eish": "BAD",               # SA expression of frustration/discomfort
    "ag": "SORRY",               # Afrikaans exclamation of mild annoyance/sympathy
    "joh": "SORRY",              # SA: expression of surprise/dismay
    "shame": "SORRY",            # SA empathy expression ("oh shame" = poor thing)
    "ag shame": "SORRY",         # Common combined form
    "robot": "STOP",             # SA English: traffic light (robot = traffic light in SA)
    "now now": "NOW",            # SA: very soon / immediately
    "just now": "WAIT",          # SA: in a little while (ambiguous — mapped to WAIT)
    "just": "WAIT",              # Often used in SA English for "just now" context
    "ja": "YES",                 # Afrikaans: yes
    "yebo": "YES",               # Zulu: yes
    "nee": "NO",                 # Afrikaans: no
    "hayi": "NO",                # Zulu: no
    "aikona": "NO",              # SA slang: definitely no
    "dankie": "THANK YOU",       # Afrikaans: thank you
    "baie dankie": "THANK YOU",  # Afrikaans: many thanks (phrase — also in PHRASE_MAP)
    "asseblief": "PLEASE",       # Afrikaans: please
    "asb": "PLEASE",             # Afrikaans abbreviation: please
    "bra": "FRIEND",             # SA slang: brother/friend
    "bru": "FRIEND",             # Cape Town: brother/mate
    "china": "FRIEND",           # SA slang: mate/friend
    "oke": "PERSON",             # SA slang: guy/person
    "ou": "PERSON",              # Afrikaans/SA: guy/bloke
    "laaitie": "CHILD",          # SA slang: young person/child
    "kak": "BAD",                # Afrikaans: bad/terrible (common SA usage)
    "moeg": "TIRED",             # Afrikaans: tired/exhausted
    "siff": "BAD",               # SA slang: disgusting/unpleasant
    "sosatie": "FOOD",           # SA food: spiced meat skewer (fingerspell fallback better, but FOOD is closest)
    "braai": "FOOD",             # SA barbecue — maps to FOOD (no dedicated sign)
    "township": "HOME",          # Maps to HOME as closest residential sign
    "rand": "MONEY",             # SA currency — already in WORD_MAP, explicit here

    # ── SASL Aspect / Tense Markers ─────────────────────────
    # FINISH marks a completed (past) action in SASL grammar.
    # WILL marks a future action.
    # These are critical grammar words — do NOT put them in FILLER.
    "finish": "FINISH", "finished": "FINISH", "done": "FINISH",
    "complete": "FINISH", "completed": "FINISH",
    "already": "FINISH",     # "I already ate" → FINISH EAT in SASL
    "will": "WILL", "shall": "WILL", "going to": "WILL",
    "would": "WILL",         # conditional future — closest SASL equivalent

    # ── SASL Modal / Ability Markers ────────────────────────
    # CAN marks ability; MUST marks obligation.
    # These had been silently dropped — they must produce a sign or be fingerspelled.
    "can": "CAN", "could": "CAN", "able": "CAN", "able to": "CAN",
    "cannot": "CAN NOT", "can't": "CAN NOT", "cant": "CAN NOT",
    "must": "MUST", "should": "MUST", "have to": "MUST",
    "need to": "MUST", "ought to": "MUST",
    "may": "CAN", "might": "CAN",     # possibility — maps to CAN in SASL

    # ── Intensifiers / Adverbs with SASL signs ───────────────
    "very": "VERY", "really": "VERY", "extremely": "VERY",
    "also": "ALSO", "too": "ALSO", "as well": "ALSO",

    # ── Body parts (Section 11 — SASL location reference) ────
    # Fingerspell if no dedicated sign, but common ones map to PAIN (location-generic)
    "head": "PAIN", "arm": "PAIN", "leg": "PAIN", "back": "PAIN",
    "stomach": "PAIN", "chest": "PAIN", "eye": "LOOK", "eyes": "LOOK",
    "ear": "LISTEN", "ears": "LISTEN",
    "tooth": "PAIN", "teeth": "PAIN", "dental": "PAIN",
    "hand": "HELP", "finger": "HELP",
    "throat": "PAIN", "neck": "PAIN", "knee": "PAIN", "shoulder": "PAIN",
    "heart": "PAIN", "lung": "SICK", "lungs": "SICK",

    # ── Symptoms (Section 11 — medical vocabulary) ────────────
    "bleeding": "HURT", "blood": "HURT",
    "vomit": "SICK", "vomiting": "SICK", "throw up": "SICK",
    "dizzy": "SICK", "dizziness": "SICK", "faint": "SICK",
    "breathless": "SICK", "breathe": "SICK", "breathing": "SICK",
    "swollen": "HURT", "swelling": "HURT",
    "bruise": "HURT", "bruised": "HURT",
    "unconscious": "SICK", "seizure": "EMERGENCY", "convulsion": "EMERGENCY",
}

# ── Filler words to skip (no sign equivalent) ────────────────────────
# IMPORTANT: Only put words here that have NO useful SASL equivalent.
# Modal verbs (will/must/can), aspect markers (finish/already), and
# intensifiers (very/also) are in WORD_MAP above — do NOT list them here.

FILLER = {
    # Articles / determiners
    "the", "a", "an", "some", "any", "every", "each", "both", "either",
    # Auxiliary verbs — only the ones with no direct SASL sign
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did",
    # Prepositions / conjunctions
    "of", "to", "in", "for", "on", "with", "at", "by", "as", "from",
    "about", "between", "through", "before", "after", "during", "into", "onto",
    "up", "down", "out", "off", "over", "under", "around", "toward",
    "and", "but", "or", "so", "if", "then", "because", "since", "although",
    "though", "however", "therefore", "yet", "nor",
    # Pronouns / determiners with no clear sign
    "it", "its", "itself", "this", "that", "these", "those",
    # Filler sounds and discourse particles
    "um", "uh", "ah", "oh", "hmm", "like",
    # Note: "just" is intentionally NOT here — it maps to WAIT in WORD_MAP (SA usage)
    # Adverbs that have no direct SASL sign equivalent
    "quite", "almost", "enough", "only", "other", "same", "another", "such",
    "even", "still", "often", "usually",
    # Subjective / stative verbs with no clear SASL sign
    "feel", "feels", "felt", "seem", "seems", "seemed",
    "become", "became", "becomes", "getting", "got",
    "next", "last", "first", "second", "third",
    "more", "most", "less", "least", "much", "many", "few", "several",
    "new", "old", "long", "short", "different",
    "here", "there", "everywhere", "somewhere", "anywhere", "nowhere",
}


def stem(word: str) -> str:
    """Reduce an inflected word to an approximate base form for lookup."""
    if word in WORD_MAP or word in FILLER:
        return word
    for suffix, replacement in [
        ("ness", ""), ("ment", ""), ("tion", ""), ("sion", ""),
        ("ings", ""), ("ing", ""), ("edly", "e"), ("ied", "y"),
        ("ies", "y"), ("ier", "y"), ("iest", "y"),
        ("ers", ""), ("er", ""), ("est", ""), ("ly", ""),
        ("ed", ""), ("es", ""), ("s", ""),
    ]:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[: -len(suffix)] + replacement
            if base in WORD_MAP:
                return base
    return word


def sentence_to_sign_names(text: str) -> list:
    """Convert an English sentence to an ordered list of SASL sign name strings."""
    if not text:
        return []

    lower = text.lower().strip()


    words = re.sub(r"[^a-z0-9\s']", " ", lower).split()
    result = []
    i = 0
    while i < len(words):
        w = words[i]

        # Try 3-word phrase
        if i + 3 <= len(words):
            three = w + " " + words[i + 1] + " " + words[i + 2]
            if three in PHRASE_MAP:
                result.extend(PHRASE_MAP[three])
                i += 3
                continue

        # Try 2-word phrase
        if i + 1 < len(words):
            two = w + " " + words[i + 1]
            if two in PHRASE_MAP:
                result.extend(PHRASE_MAP[two])
                i += 2
                continue
            if two in WORD_MAP:
                result.append(WORD_MAP[two])
                i += 2
                continue

        if w in FILLER:
            i += 1
            continue

        if w in WORD_MAP:
            result.append(WORD_MAP[w])
        else:
            stemmed = stem(w)
            if stemmed != w and stemmed in WORD_MAP:
                result.append(WORD_MAP[stemmed])
            elif w not in FILLER:
                # Fingerspell unknown word letter by letter
                for ch in w.upper():
                    if "A" <= ch <= "Z":
                        result.append(ch)
        i += 1

    return result

