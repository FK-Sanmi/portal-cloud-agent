from __future__ import annotations

from pathlib import Path

from google import genai
from google.genai import types


def extract_instructions(
    *,
    api_key: str,
    model: str,
    prompt: str,
    pdf_path: Path,
    timeout: int,
) -> str:
    client = genai.Client(
        api_key=api_key,
        http_options=types.HttpOptions(timeout=timeout * 1000),
    )
    uploaded_pdf = client.files.upload(file=str(pdf_path))
    response = client.models.generate_content(
        model=model,
        contents=[prompt, uploaded_pdf],
    )

    text = response.text
    if not text or not text.strip():
        raise RuntimeError(f"Gemini returned no text content: {response!r}")
    return text
