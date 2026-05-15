from __future__ import annotations

from pathlib import Path

from .config import AppConfig


def read_required(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required prompt file does not exist: {path}")
    return path.read_text(encoding="utf-8")


def build_cloud_prompt(
    *,
    config: AppConfig,
    portal_number: int,
    instructions_path: Path,
    branch_name: str,
) -> str:
    implementation_guide = read_required(
        config.portal_prompts_dir / "agent_implementation_prompt_basic.md"
    )
    review_guide = read_required(config.portal_prompts_dir / "review.md")
    instructions = read_required(instructions_path)

    return f"""You are implementing a new Jimmy portal configuration in Cursor Cloud Agent.

Cloud workflow:
1. Read and follow AGENTS.md in the repository.
2. Use browser/Playwright/computer-use inspection when inspecting live pages or deriving XPaths.
3. During browser inspection, check whether stable same-domain API/XHR endpoints exist for listings, pagination, filters, or metadata. Use an API-backed METHOD when it is clearly more reliable than DOM scraping, but only after confirming the endpoint through browser/network inspection.
4. Do not implement custom METHOD code until you have checked whether BASIC config, built-in parse_pdf/parse_doc/parse_pdf_or_doc, or parse_pdf with need_prediction can solve it. If a custom METHOD is required, read .vscode/portal_prompts/agent_implementation_prompt_method.md before writing it and follow it strictly.
5. Use portal number {portal_number}.
6. Work on branch {branch_name}. If you rename the branch, use the repository convention <portal_name>_{portal_number}.
7. Implement the portal under jimmy_v4/portal_configurations/.
8. Before finishing, review your own implementation in full mode using the review guide below. Resolve every critical/runtime issue and fix non-critical correctness issues when practical.
9. Run relevant checks/tests after review fixes.
10. Commit all completed changes. Cursor Cloud should open the PR automatically.

Prompt sources embedded by the launcher:
1. agent_implementation_prompt_basic.md
2. portal_instructions_{portal_number}.md
3. review.md

--- IMPLEMENTATION GUIDE: agent_implementation_prompt_basic.md ---
{implementation_guide}

--- GENERATED PORTAL INSTRUCTIONS: portal_instructions_{portal_number}.md ---
{instructions}

--- REVIEW GUIDE: review.md ---
{review_guide}
"""
