from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Annotated

import typer

from .config import load_config, load_env_file
from .cursor_cloud import create_cloud_agent
from .extraction import ensure_portal_instructions
from .prompts import build_cloud_prompt


app = typer.Typer(
    help="Launch Cursor Cloud Agents for Jimmy portal implementations.",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    """Launch Cursor Cloud Agents for Jimmy portal implementations."""


@app.command(help="Generate instructions and launch a Cloud Agent.")
def cloud(
    law: Annotated[int, typer.Option("--law", min=1, help="LAW number, e.g. 1154")],
    portal: Annotated[
        int,
        typer.Option("--portal", min=1, help="Portal number, e.g. 575"),
    ],
    config_path: Annotated[
        Path | None,
        typer.Option("--config", help="Optional config.toml path"),
    ] = None,
    env_file: Annotated[
        Path | None,
        typer.Option("--env-file", help="Optional .env file path"),
    ] = None,
    force_instructions: Annotated[
        bool,
        typer.Option(
            "--force-instructions",
            help="Regenerate portal instructions even if cached instructions exist",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Print planned actions without calling Gemini or Cursor Cloud",
        ),
    ] = False,
    branch: Annotated[
        str | None,
        typer.Option(
            "--branch",
            help="Branch name for Cursor Cloud. Defaults to portal_<portal>_<timestamp>",
        ),
    ] = None,
) -> None:
    try:
        _run_cloud(
            law=law,
            portal=portal,
            config_path=config_path,
            env_file=env_file,
            force_instructions=force_instructions,
            dry_run=dry_run,
            branch=branch,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


def _run_cloud(
    *,
    law: int,
    portal: int,
    config_path: Path | None,
    env_file: Path | None,
    force_instructions: bool,
    dry_run: bool,
    branch: str | None,
) -> None:
    config = load_config(config_path)
    load_env_file(Path.cwd() / ".env")
    load_env_file(config.downloads_dir / ".env")
    if env_file:
        load_env_file(env_file.expanduser().resolve())

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    branch_name = branch or f"portal_{portal}_{timestamp}"

    print("Run configuration")
    print(f"LAW number: {law}")
    print(f"Portal number: {portal}")
    print(f"Repo URL: {config.repo_url}")
    print(f"Base branch: {config.base_branch}")
    print(f"Branch: {branch_name}")
    print(f"Extraction model: {config.extraction_model}")
    print(f"Cursor model: {config.cursor_model}")
    print(f"Downloads dir: {config.downloads_dir}")
    print(f"Prompt dir: {config.portal_prompts_dir}\n")

    instructions_path = ensure_portal_instructions(
        config=config,
        law_number=law,
        portal_number=portal,
        force=force_instructions,
        dry_run=dry_run,
    )
    if dry_run and not instructions_path.exists():
        print(
            "Dry run: portal instructions do not exist yet, so prompt assembly and "
            "Cursor Cloud creation were skipped.\n"
        )
        return

    prompt = build_cloud_prompt(
        config=config,
        portal_number=portal,
        instructions_path=instructions_path,
        branch_name=branch_name,
    )

    print("Cursor Cloud Agent")
    print(f"autoCreatePR: true")
    print(f"Prompt length: {len(prompt):,} characters\n")

    if dry_run:
        print("Dry run: Cursor Cloud Agent creation skipped.\n")
        return

    api_key = os.environ.get("CURSOR_API_KEY")
    if not api_key:
        raise RuntimeError("CURSOR_API_KEY is not set")

    result = create_cloud_agent(
        api_key=api_key,
        prompt=prompt,
        repo_url=config.repo_url,
        starting_ref=config.base_branch,
        branch_name=branch_name,
        model_id=config.cursor_model,
        auto_create_pr=True,
    )
    print("Cloud agent created")
    print(f"Agent URL: {result.agent_url}")
    print(f"Agent ID: {result.agent_id}")
    print(f"Run ID: {result.run_id}")
    print(f"Branch: {result.branch_name}")
    print(f"Run status: {result.status}\n")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
