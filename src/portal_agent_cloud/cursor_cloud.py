from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "https://api.cursor.com"


@dataclass(frozen=True)
class CloudAgentResult:
    agent_id: str
    run_id: str
    agent_url: str
    branch_name: str
    status: str


def _basic_auth(api_key: str) -> str:
    token = base64.b64encode(f"{api_key}:".encode("utf-8")).decode("ascii")
    return f"Basic {token}"


def create_cloud_agent(
    *,
    api_key: str,
    prompt: str,
    repo_url: str,
    starting_ref: str,
    branch_name: str,
    model_id: str,
    auto_create_pr: bool = True,
    timeout: int = 60,
) -> CloudAgentResult:
    payload = {
        "prompt": {"text": prompt},
        "model": {"id": model_id},
        "repos": [{"url": repo_url, "startingRef": starting_ref}],
        "branchName": branch_name,
        "autoCreatePR": auto_create_pr,
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        f"{API_BASE}/v1/agents",
        data=body,
        headers={
            "Authorization": _basic_auth(api_key),
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(
            f"Cursor Cloud request failed with HTTP {exc.code}: {error_body}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Cursor Cloud request failed: {exc}") from exc

    try:
        data = json.loads(response_body)
        agent = data["agent"]
        run = data["run"]
        return CloudAgentResult(
            agent_id=agent["id"],
            run_id=run["id"],
            agent_url=agent["url"],
            branch_name=agent.get("branchName", branch_name),
            status=run["status"],
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unexpected Cursor Cloud response: {response_body}") from exc
