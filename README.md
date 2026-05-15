# Portal Agent Cloud

Small Python CLI for launching Cursor Cloud Agents to implement Jimmy portal configurations and open PRs automatically.

This project is the team-friendly cloud version of the local portal automation workflow. It does not create local git worktrees. It generates or reuses portal instructions locally, builds a full prompt from this repo's `portal_prompts/` directory, and creates a Cursor Cloud Agent through the Cloud Agents API with `autoCreatePR` enabled.

## Requirements

- Python 3.12+
- `uv`
- Cursor Cloud Agents enabled for your account/team
- Cursor GitHub app installed with write access to the target repository
- A Cloud Agent environment configured for the target repository
- `GEMINI_API_KEY` for instruction extraction through the official Gemini SDK
- `CURSOR_API_KEY` for Cursor Cloud Agents API

## Setup

Download the Jira ZIP file for the portal task first and put it in this repo's `downloads/` directory using this filename format:

```text
downloads/LAW-<law-number>.zip
```

For example, for law `1154`:

```text
downloads/LAW-1154.zip
```

The command will turn that ZIP into `downloads/LAW-<law-number>.pdf` automatically. If the ZIP contains one PDF, it copies that PDF. If the ZIP contains image pages, it converts the images into a PDF.

Then install dependencies and create your local `.env` file:

```bash
uv sync
cp .env.example .env
```

Fill in `.env`:

```bash
GEMINI_API_KEY=...
CURSOR_API_KEY=...
```

If you prefer another download location, override `PORTAL_AGENT_DOWNLOADS_DIR` / `downloads_dir`.

Optional config file:

```bash
mkdir -p ~/.config/portal-agent-cloud
cp config.example.toml ~/.config/portal-agent-cloud/config.toml
```

Environment variables override `config.toml`.

## Usage

General format:

```bash
uv run portal-cloud-agent --law <law-number> --portal <portal-number>
```

Dry-run first:

```bash
uv run portal-cloud-agent --law 1154 --portal 575 --dry-run
```

Launch a cloud agent and let Cursor open the PR:

```bash
uv run portal-cloud-agent --law 1154 --portal 575
```

Force regeneration of portal instructions:

```bash
uv run portal-cloud-agent --law 1154 --portal 575 --force-instructions
```

Use a custom branch name:

```bash
uv run portal-cloud-agent --law 1154 --portal 575 --branch portal_575_test
```

## What The Command Does

1. Loads config and `.env` values.
2. Reuses `portal_instructions_<portal>.md` if it already exists.
3. Otherwise creates `downloads/LAW-<law>.pdf` from `downloads/LAW-<law>.zip` when the PDF does not already exist.
4. Uploads `LAW-<law>.pdf` with the official Gemini SDK and sends it with `gemini_extraction_prompt.md` to Gemini.
5. Builds a Cursor Cloud prompt from:
   - `agent_implementation_prompt_basic.md`
   - `portal_instructions_<portal>.md`
   - `review.md`
6. Calls `POST https://api.cursor.com/v1/agents` with:
   - repository URL
   - base branch
   - branch name
   - Cursor model
   - `autoCreatePR: true`
7. Prints the Cloud Agent URL, branch, agent ID, and run ID.

## Defaults

```toml
downloads_dir = "./downloads"
jimmy_dir = "."
portal_prompts_dir = "./portal_prompts"
repo_url = "https://github.com/filerskeepers-main/jimmy-v4"
base_branch = "main"
extraction_model = "gemini-3.1-pro"
cursor_model = "gpt-5.5-high"
extraction_timeout = 240
```

Omit `portal_prompts_dir` to use this repo's bundled `portal_prompts/` directory. If you set it in `config.toml`, prefer an absolute path.
Omit `downloads_dir` and `jimmy_dir` to use this repo's bundled `downloads/` directory and project root.

## Notes

- The cloud agent checks out from GitHub, not your local worktree.
- Prompt templates live in this repo under `portal_prompts/` and are embedded into the API request.
- Generated `portal_instructions_<portal>.md` files are written to `portal_prompts/` by default.
- Generated `portal_instructions_*.md` files are ignored by git because they are run-specific artifacts.
- Downloaded ZIP files and generated PDFs in `downloads/` are ignored by git.
- The PDF itself is not uploaded to Cursor Cloud. Only generated portal instructions are embedded in the Cursor prompt.
- PR creation is handled by Cursor Cloud via `autoCreatePR: true`.
