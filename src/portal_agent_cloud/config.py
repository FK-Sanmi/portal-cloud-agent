from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CONFIG_PATH = Path.home() / ".config/portal-agent-cloud/config.toml"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROMPTS_DIR = PROJECT_ROOT / "portal_prompts"


@dataclass(frozen=True)
class AppConfig:
    downloads_dir: Path
    jimmy_dir: Path
    portal_prompts_dir: Path
    repo_url: str
    base_branch: str
    extraction_model: str
    cursor_model: str
    extraction_timeout: int


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def load_config(config_path: Path | None = None) -> AppConfig:
    config_file = config_path or DEFAULT_CONFIG_PATH
    data: dict = {}
    if config_file.exists():
        data = tomllib.loads(config_file.read_text(encoding="utf-8"))

    downloads_dir = _expand_path(
        os.environ.get(
            "PORTAL_AGENT_DOWNLOADS_DIR",
            data.get("downloads_dir", str(PROJECT_ROOT / "downloads")),
        )
    )
    jimmy_dir = _expand_path(
        os.environ.get(
            "PORTAL_AGENT_JIMMY_DIR",
            data.get("jimmy_dir", str(PROJECT_ROOT)),
        )
    )
    portal_prompts_dir = _expand_path(
        os.environ.get(
            "PORTAL_AGENT_PROMPTS_DIR",
            data.get(
                "portal_prompts_dir",
                str(DEFAULT_PROMPTS_DIR),
            ),
        )
    )

    return AppConfig(
        downloads_dir=downloads_dir,
        jimmy_dir=jimmy_dir,
        portal_prompts_dir=portal_prompts_dir,
        repo_url=os.environ.get(
            "PORTAL_AGENT_REPO_URL",
            data.get("repo_url", "https://github.com/filerskeepers-main/jimmy-v4"),
        ),
        base_branch=os.environ.get(
            "PORTAL_AGENT_BASE_BRANCH", data.get("base_branch", "main")
        ),
        extraction_model=os.environ.get(
            "PORTAL_AGENT_EXTRACTION_MODEL",
            data.get("extraction_model", "gemini-3.1-pro"),
        ),
        cursor_model=os.environ.get(
            "PORTAL_AGENT_CURSOR_MODEL", data.get("cursor_model", "gpt-5.5-high")
        ),
        extraction_timeout=int(
            os.environ.get(
                "PORTAL_AGENT_EXTRACTION_TIMEOUT",
                str(data.get("extraction_timeout", 240)),
            )
        ),
    )
