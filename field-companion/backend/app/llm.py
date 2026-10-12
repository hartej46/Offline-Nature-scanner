"""
OpenAI-compatible LLM client wrapper.
Talks to Ollama (or any OpenAI-compatible endpoint) via env vars.
Model-swappable: changing LLM_BASE_URL and LLM_MODEL needs zero code changes.
"""

import os
import base64
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4:e2b")

# Ollama ignores API keys but the openai client requires one.
# Timeout set to 60s to prevent backend requests from hanging if model fails to load.
_client = OpenAI(
    base_url=LLM_BASE_URL,
    api_key=os.getenv("LLM_API_KEY", "unused"),
    timeout=60.0,
)


def chat(
    messages: list[dict],
    model: str = None,
    max_tokens: int = 512,
    temperature: float = 0.3,
    tools: list[dict] = None,
    tool_choice: str = "auto",
) -> dict:
    """
    Send a chat completion request.

    Args:
        messages: OpenAI-format message list
        model: Override the default model
        max_tokens: Max tokens in the response
        temperature: Sampling temperature (lower = more deterministic)
        tools: Optional list of tool definitions for function calling
        tool_choice: "auto", "none", or a specific tool name

    Returns:
        The full response object as a dict-like object.
    """
    kwargs = {
        "model": model or LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    response = _client.chat.completions.create(**kwargs)
    return response


def chat_text(
    user_message: str,
    system_prompt: str = None,
    model: str = None,
    max_tokens: int = 512,
) -> str:
    """Simple text-in, text-out convenience method."""
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_message})

    response = chat(messages, model=model, max_tokens=max_tokens)
    return response.choices[0].message.content or ""


def chat_with_image(
    user_message: str,
    image_path: str = None,
    image_base64: str = None,
    system_prompt: str = None,
    model: str = None,
    max_tokens: int = 512,
) -> str:
    """Send a message with an image attachment."""
    if image_path and not image_base64:
        with open(image_path, "rb") as f:
            image_base64 = base64.b64encode(f.read()).decode("utf-8")

    if not image_base64:
        raise ValueError("Either image_path or image_base64 must be provided")

    # Detect MIME type from base64 header or default to JPEG
    mime_type = "image/jpeg"
    if image_path:
        ext = os.path.splitext(image_path)[1].lower()
        mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                    ".gif": "image/gif", ".webp": "image/webp"}
        mime_type = mime_map.get(ext, "image/jpeg")

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    messages.append({
        "role": "user",
        "content": [
            {"type": "text", "text": user_message},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{image_base64}"},
            },
        ],
    })

    response = chat(messages, model=model, max_tokens=max_tokens)
    return response.choices[0].message.content or ""


def get_model_info() -> dict:
    """Return current LLM configuration."""
    return {
        "base_url": LLM_BASE_URL,
        "model": LLM_MODEL,
    }
