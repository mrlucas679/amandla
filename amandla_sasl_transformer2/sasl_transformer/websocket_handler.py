"""
WebSocket handler for real-time SASL translation.

This integrates with your existing Amandla WebSocket setup to provide
live translation as Whisper produces speech-to-text output.

Flow:
    1. Frontend sends English text via WebSocket (from Whisper STT)
    2. This handler translates it to SASL gloss
    3. Sends back the translation via WebSocket
    4. Frontend feeds tokens to the avatar animation queue
    5. Frontend displays the SASL gloss text on screen

Integration with your existing WebSocket:
    Add the handler to your existing WebSocket endpoint:

    from sasl_transformer.websocket_handler import SASLWebSocketHandler

    sasl_handler = SASLWebSocketHandler()

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "translate":
                await sasl_handler.handle_translation(websocket, data)
"""

import json
import logging
from typing import Optional

from fastapi import WebSocket

from sasl_transformer.models import TranslationRequest
from sasl_transformer.transformer import SASLTransformer

logger = logging.getLogger(__name__)


class SASLWebSocketHandler:
    """
    Handles WebSocket messages for real-time SASL translation.

    This sits alongside your existing WebSocket handlers for
    Whisper STT and avatar control.

    Message format (incoming):
    {
        "type": "translate",
        "english_text": "I went to the store",
        "include_non_manual": true,
        "context": ""  // optional: previous sentence
    }

    Message format (outgoing):
    {
        "type": "sasl_translation",
        "original_english": "I went to the store",
        "gloss_text": "STORE I GO FINISH",
        "tokens": [...],
        "non_manual_markers": [...],
        "unknown_words": [...]
    }
    """

    def __init__(self, transformer: Optional[SASLTransformer] = None):
        """
        Initialise the WebSocket handler.

        Args:
            transformer: An existing SASLTransformer instance.
                If None, creates a new one.
        """
        self._transformer = transformer or SASLTransformer()

    async def handle_translation(self, websocket: WebSocket, data: dict) -> None:
        """
        Handle a translation request received via WebSocket.

        Translates the English text and sends back the SASL gloss
        in real time. The frontend can immediately start:
        1. Feeding tokens to the avatar animation queue
        2. Displaying the gloss text on screen

        Args:
            websocket: The active WebSocket connection.
            data: The incoming message data containing english_text.
        """
        english_text = data.get("english_text", "").strip()

        if not english_text:
            await websocket.send_json({
                "type": "sasl_translation",
                "error": "No text provided",
            })
            return

        try:
            # Build the request
            request = TranslationRequest(
                english_text=english_text,
                include_non_manual=data.get("include_non_manual", True),
                context=data.get("context", ""),
            )

            # Translate
            response = await self._transformer.translate(request)

            # Send the translation back via WebSocket
            await websocket.send_json({
                "type": "sasl_translation",
                "original_english": response.original_english,
                "gloss_text": response.gloss_text,
                "tokens": [token.model_dump() for token in response.tokens],
                "non_manual_markers": response.non_manual_markers,
                "unknown_words": response.unknown_words,
                "translation_notes": response.translation_notes,
            })

            logger.info(
                "WebSocket translation: '%s' → '%s'",
                english_text[:50],
                response.gloss_text,
            )

        except Exception as e:
            logger.error("WebSocket translation error: %s", e, exc_info=True)
            await websocket.send_json({
                "type": "sasl_translation",
                "error": f"Translation failed: {str(e)}",
                "original_english": english_text,
            })

    async def handle_message(self, websocket: WebSocket, raw_data: str) -> bool:
        """
        Check if a raw WebSocket message is a SASL translation request
        and handle it if so.

        This method is designed to fit into your existing WebSocket
        message routing. Call it first; if it returns False, pass
        the message to your other handlers.

        Args:
            websocket: The active WebSocket connection.
            raw_data: The raw JSON string received.

        Returns:
            True if this message was a SASL translation request
            (and was handled). False if it should be passed to
            other handlers.

        Example integration:
            async for message in websocket.iter_text():
                data = json.loads(message)

                # Try SASL handler first
                if await sasl_handler.handle_message(websocket, message):
                    continue

                # Otherwise, pass to your existing handlers
                if data["type"] == "audio":
                    await handle_audio(websocket, data)
                elif data["type"] == "avatar_command":
                    await handle_avatar(websocket, data)
        """
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError:
            return False

        if data.get("type") != "translate":
            return False

        await self.handle_translation(websocket, data)
        return True
