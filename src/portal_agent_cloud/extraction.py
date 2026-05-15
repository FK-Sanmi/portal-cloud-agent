from __future__ import annotations

import os
from pathlib import Path

from .config import AppConfig
from .gemini import extract_instructions


def instruction_path(config: AppConfig, portal_number: int) -> Path:
    return config.portal_prompts_dir / f"portal_instructions_{portal_number}.md"


def pdf_path(config: AppConfig, law_number: int) -> Path:
    return config.downloads_dir / f"LAW-{law_number}.pdf"


def prompt_path(config: AppConfig) -> Path:
    return config.portal_prompts_dir / "gemini_extraction_prompt.md"


def ensure_portal_instructions(
    *,
    config: AppConfig,
    law_number: int,
    portal_number: int,
    force: bool,
    dry_run: bool,
) -> Path:
    output_path = instruction_path(config, portal_number)
    if output_path.exists() and output_path.stat().st_size > 0 and not force:
        print(
            "Portal instructions already exist; skipping Gemini extraction.\n"
            f"Instructions: {output_path}\n"
        )
        return output_path

    pdf = pdf_path(config, law_number)
    prompt_file = prompt_path(config)
    if dry_run:
        print("Instruction extraction")
        print(f"PDF: {pdf}")
        print(f"Prompt: {prompt_file}")
        print(f"Model: {config.extraction_model}")
        print(f"Output: {output_path}")
        print("Dry run: Gemini extraction skipped.\n")
        return output_path

    if not pdf.exists():
        raise FileNotFoundError(f"PDF does not exist: {pdf}")
    if not prompt_file.exists():
        raise FileNotFoundError(f"Gemini extraction prompt does not exist: {prompt_file}")

    print("Instruction extraction")
    print(f"PDF: {pdf}")
    print(f"Prompt: {prompt_file}")
    print(f"Model: {config.extraction_model}")
    print(f"Output: {output_path}\n")

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    instructions = extract_instructions(
        api_key=api_key,
        model=config.extraction_model,
        prompt=prompt_file.read_text(encoding="utf-8"),
        pdf_path=pdf,
        timeout=config.extraction_timeout,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(instructions.rstrip() + "\n", encoding="utf-8")
    print(f"Wrote portal instructions: {output_path}\n")
    return output_path
