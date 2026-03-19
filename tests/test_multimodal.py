from __future__ import annotations

import base64

import pytest

from shared.schemas import OpenAIChatMessage
from shared.multimodal import openai_message_to_ollama_message, openai_messages_to_ollama_messages


def test_text_only_message_passes_through():
    msg = OpenAIChatMessage(role="user", content="hello")

    out = openai_message_to_ollama_message(msg)

    assert out == {"role": "user", "content": "hello"}


def test_image_data_url_is_converted_to_base64():
    raw = b"hello-image"
    data_url = "data:image/png;base64," + base64.b64encode(raw).decode("ascii")
    msg = OpenAIChatMessage(
        role="user",
        content=[
            {"type": "text", "text": "look at this"},
            {"type": "image_url", "image_url": {"url": data_url}},
        ],
    )

    out = openai_message_to_ollama_message(msg)

    assert out["role"] == "user"
    assert out["content"] == "look at this"
    assert out["images"] == [base64.b64encode(raw).decode("ascii")]


def test_image_part_rejected_for_non_user_messages():
    msg = OpenAIChatMessage(
        role="assistant",
        content=[
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,aGVsbG8="}},
        ],
    )

    with pytest.raises(ValueError, match="Image content parts are only supported"):
        openai_message_to_ollama_message(msg)


def test_batch_conversion_preserves_order():
    messages = [
        OpenAIChatMessage(role="system", content="sys"),
        OpenAIChatMessage(role="user", content="hi"),
    ]

    out = openai_messages_to_ollama_messages(messages)

    assert out == [{"role": "system", "content": "sys"}, {"role": "user", "content": "hi"}]
