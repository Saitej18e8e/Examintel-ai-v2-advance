"""Thin wrapper around Google Gemini (google-genai SDK).

Three capabilities, each used by a different kind of agent:
  * text()        - free text
  * structured()  - JSON validated against a Pydantic model
  * run_tools()   - the model decides which Python tools to call (agentic loop)

Retries are applied only to rate-limit / overload errors, so a wrong API key
fails fast with a clear message instead of waiting.
"""
from __future__ import annotations

import time
from typing import Callable, List, Optional, Type, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

DEFAULT_MODEL = "gemini-2.5-flash"
RETRYABLE = ("429", "503", "500", "RESOURCE_EXHAUSTED", "UNAVAILABLE", "overloaded")


class LLMError(RuntimeError):
    """Raised when Gemini cannot produce a usable answer."""


def _with_retries(fn: Callable, retries: int = 4):
    last: Optional[Exception] = None
    for attempt in range(retries):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - SDK raises many error types
            last = exc
            if any(tag in str(exc) for tag in RETRYABLE) and attempt < retries - 1:
                time.sleep(2**attempt)  # 1s, 2s, 4s
                continue
            break
    raise LLMError(_friendly(last))


def _friendly(exc: Optional[Exception]) -> str:
    text = str(exc)
    if "API key" in text or "API_KEY_INVALID" in text or "403" in text:
        return "Gemini rejected the API key. Check API_KEY in .env or Streamlit Secrets."
    if "429" in text or "RESOURCE_EXHAUSTED" in text:
        return "Gemini rate limit reached. Wait a minute and try again."
    return f"Gemini request failed: {text[:300]}"


class GeminiLLM:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        if not api_key:
            raise LLMError("API_KEY is missing.")
        self.client = genai.Client(api_key=api_key)
        self.model = model

    # ---- plain text -------------------------------------------------
    def text(self, prompt: str, system: Optional[str] = None, temperature: float = 0.6) -> str:
        config = types.GenerateContentConfig(system_instruction=system, temperature=temperature)

        def call() -> str:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
            if not response.text:
                raise ValueError("empty response")
            return response.text

        return _with_retries(call)

    # ---- structured JSON -------------------------------------------
    def structured(
        self, prompt: str, schema: Type[T], system: Optional[str] = None, temperature: float = 0.4
    ) -> T:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        )

        def call() -> T:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
            parsed = getattr(response, "parsed", None)
            if isinstance(parsed, schema):
                return parsed
            return schema.model_validate_json(response.text)

        return _with_retries(call)

    # ---- agentic tool use ------------------------------------------
    def run_tools(self, prompt: str, tools: List[Callable], system: Optional[str] = None) -> str:
        """Let Gemini call the given Python functions until it can answer.

        The SDK runs the function-calling loop automatically: the model asks for
        a tool, the SDK executes it, and the result goes back to the model.
        """
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=0.3,
            tools=tools,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                maximum_remote_calls=6
            ),
        )

        def call() -> str:
            response = self.client.models.generate_content(
                model=self.model, contents=prompt, config=config
            )
            if not response.text:
                raise ValueError("empty response")
            return response.text

        return _with_retries(call)

    # ---- scanned PDFs ----------------------------------------------
    def transcribe_pdf(self, data: bytes) -> str:
        """Fallback for image-only PDFs: Gemini reads the PDF directly."""
        part = types.Part.from_bytes(data=data, mime_type="application/pdf")
        instruction = (
            "Transcribe all text in this exam paper exactly as written, keeping question "
            "numbers and marks. Return plain text only."
        )

        def call() -> str:
            response = self.client.models.generate_content(
                model=self.model, contents=[part, instruction]
            )
            return response.text or ""

        return _with_retries(call)
