from __future__ import annotations

import base64
import binascii
from typing import Any
from urllib.parse import unquote_to_bytes

from shared.schemas import OpenAIChatMessage, OpenAIImageURLContentPart, OpenAITextContentPart


def _decode_data_url(url: str) -> str:
    if not url.startswith("data:"):
        raise ValueError("Only data: image URLs are supported for multimodal requests")

    try:
        header, data = url.split(",", 1)
    except ValueError as exc:
        raise ValueError("Invalid data URL") from exc

    if ";base64" in header:
        try:
            raw = base64.b64decode(data, validate=True)
        except binascii.Error as exc:
            raise ValueError("Invalid base64 image payload") from exc
    else:
        raw = unquote_to_bytes(data)

    return base64.b64encode(raw).decode("ascii")


def openai_message_to_ollama_message(message: OpenAIChatMessage) -> dict[str, Any]:
    if isinstance(message.content, str):
        return {"role": message.role, "content": message.content}

    text_parts: list[str] = []
    images: list[str] = []

    for part in message.content:
        if isinstance(part, OpenAITextContentPart):
            text_parts.append(part.text)
            continue
        if isinstance(part, OpenAIImageURLContentPart):
            if message.role != "user":
                raise ValueError("Image content parts are only supported for user messages")
            images.append(_decode_data_url(part.image_url.url))
            continue
        raise ValueError(f"Unsupported content part type: {getattr(part, 'type', 'unknown')}")

    payload: dict[str, Any] = {
        "role": message.role,
        "content": "".join(text_parts),
    }
    if images:
        payload["images"] = images
    return payload


def openai_messages_to_ollama_messages(messages: list[OpenAIChatMessage]) -> list[dict[str, Any]]:
    return [openai_message_to_ollama_message(message) for message in messages]
