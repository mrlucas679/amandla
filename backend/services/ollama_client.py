"""Ollama client placeholder for AMANDLA.

In the full system this module would call the local Ollama server and run the 'amandla' model
to map text to a list of sign names or sign objects. For now this is a placeholder that returns
an empty result or defers to the server-side simple mapping.
"""

def classify_text_to_signs(text: str):
    # Placeholder — in production call local Ollama model 'amandla'
    print('[Ollama] classify_text_to_signs called — returning empty (mock)')
    return []

