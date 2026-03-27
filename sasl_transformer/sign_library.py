"""
Sign Library Manager.

Loads your sign library and checks which SASL gloss words have
corresponding sign animations vs which need to be fingerspelled.

Your sign library JSON file should have this structure:
{
    "signs": {
        "HELLO": {
            "animation_id": "sign_hello",
            "category": "greetings",
            "variants": ["HI"]
        },
        "THANK-YOU": {
            "animation_id": "sign_thank_you",
            "category": "common",
            "variants": ["THANKS"]
        }
    }
}
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SignLibrary:
    """
    Manages the sign library — the collection of signs your avatar knows
    how to perform. Any word NOT in this library will be fingerspelled.

    Attributes:
        signs: Dict mapping gloss words to their animation data.
        variants: Dict mapping alternative gloss words to their canonical form.
    """

    def __init__(self, library_path: Optional[str] = None):
        """
        Load the sign library from a JSON file.

        Args:
            library_path: Path to the sign library JSON file.
                If None, starts with an empty library (all words fingerspelled).
        """
        self.signs: dict[str, dict] = {}
        self.variants: dict[str, str] = {}

        if library_path:
            self._load_from_file(library_path)

    def _load_from_file(self, path: str) -> None:
        """Load signs from a JSON file."""
        file_path = Path(path)

        if not file_path.exists():
            logger.warning(
                "Sign library file not found at %s — "
                "starting with empty library (all words will be fingerspelled)",
                path,
            )
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_signs = data.get("signs", {})

            for gloss_word, sign_data in raw_signs.items():
                canonical = gloss_word.upper()
                self.signs[canonical] = sign_data

                # Register any variant spellings
                for variant in sign_data.get("variants", []):
                    self.variants[variant.upper()] = canonical

            logger.info(
                "Loaded %d signs (%d variants) from %s",
                len(self.signs),
                len(self.variants),
                path,
            )
        except json.JSONDecodeError as e:
            logger.error("Failed to parse sign library JSON at %s: %s", path, e)
        except Exception as e:
            logger.error("Failed to load sign library from %s: %s", path, e)

    def has_sign(self, gloss_word: str) -> bool:
        """
        Check if a gloss word has a corresponding sign animation.

        Checks both the canonical sign and any registered variants.

        Args:
            gloss_word: The SASL gloss word to check (case-insensitive).

        Returns:
            True if the sign exists in the library.
        """
        upper = gloss_word.upper()
        return upper in self.signs or upper in self.variants

    def get_animation_id(self, gloss_word: str) -> Optional[str]:
        """
        Get the animation ID for a gloss word.

        Args:
            gloss_word: The SASL gloss word (case-insensitive).

        Returns:
            The animation_id string, or None if not in library.
        """
        upper = gloss_word.upper()

        # Check canonical first
        if upper in self.signs:
            return self.signs[upper].get("animation_id")

        # Check variants
        if upper in self.variants:
            canonical = self.variants[upper]
            return self.signs.get(canonical, {}).get("animation_id")

        return None

    def get_canonical(self, gloss_word: str) -> str:
        """
        Get the canonical form of a gloss word (resolves variants).

        Args:
            gloss_word: The gloss word to resolve.

        Returns:
            The canonical form, or the original word if not found.
        """
        upper = gloss_word.upper()

        if upper in self.variants:
            return self.variants[upper]

        return upper

    def get_unknown_words(self, gloss_words: list[str]) -> list[str]:
        """
        Given a list of gloss words, return which ones are NOT in the library.

        Args:
            gloss_words: List of SASL gloss words to check.

        Returns:
            List of words that will need to be fingerspelled.
        """
        return [word for word in gloss_words if not self.has_sign(word)]

    def add_sign(self, gloss_word: str, animation_id: str, category: str = "general", variants: list[str] | None = None) -> None:
        """
        Add a new sign to the library at runtime.

        This is useful for dynamically expanding the library
        as new sign animations are created.

        Args:
            gloss_word: The canonical gloss word.
            animation_id: The animation ID for the avatar.
            category: Category grouping for the sign.
            variants: Alternative gloss words that map to this sign.
        """
        canonical = gloss_word.upper()
        self.signs[canonical] = {
            "animation_id": animation_id,
            "category": category,
            "variants": variants or [],
        }

        for variant in (variants or []):
            self.variants[variant.upper()] = canonical

        logger.info("Added sign: %s (animation: %s)", canonical, animation_id)

    def save_to_file(self, path: str) -> None:
        """
        Save the current library to a JSON file.

        Args:
            path: File path to save to.
        """
        data = {"signs": self.signs}

        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        logger.info("Saved %d signs to %s", len(self.signs), path)

    @property
    def total_signs(self) -> int:
        """Total number of signs in the library."""
        return len(self.signs)

    def list_categories(self) -> list[str]:
        """List all unique categories in the library."""
        categories = set()
        for sign_data in self.signs.values():
            categories.add(sign_data.get("category", "general"))
        return sorted(categories)
