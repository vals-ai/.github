from __future__ import annotations

import ast
import importlib.util
import json
import os
import re
import subprocess
import sys
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol, cast

import pytest
import requests

ROOT = Path(__file__).parents[1]
SCANNER_COMMIT = "0c6a49f1fa56a1d472575da86a94dbc1edb78eda"


class Client(Protocol):
    def get_pr_data(self, repo_name: str, pr_number: int) -> dict[str, Any]: ...
    def get_pr_diff(self, repo_name: str, pr_number: int) -> str: ...


@pytest.fixture(scope="session")
def original_source() -> str:
    cache = ROOT / ".cache" / SCANNER_COMMIT / "github_action_audit.py"
    if not cache.exists():
        cache.parent.mkdir(parents=True, exist_ok=True)
        url = (
            "https://raw.githubusercontent.com/anthropics/claude-code-security-review/"
            f"{SCANNER_COMMIT}/claudecode/github_action_audit.py"
        )
        with urllib.request.urlopen(url, timeout=30) as response:
            cache.write_bytes(response.read())
    return cache.read_text()


@pytest.fixture
def patched_client(tmp_path: Path, original_source: str, monkeypatch: pytest.MonkeyPatch) -> Client:
    patch = ROOT / ".github/security-review/local-diff.patch"
    assert patch.exists(), "Scanner patch is missing"
    target = tmp_path / "claudecode/github_action_audit.py"
    target.parent.mkdir(parents=True)
    target.write_text(original_source)
    action_cache = ROOT / ".cache" / SCANNER_COMMIT / "action.yml"
    if not action_cache.exists():
        with urllib.request.urlopen(
            "https://raw.githubusercontent.com/anthropics/claude-code-security-review/"
            f"{SCANNER_COMMIT}/action.yml",
            timeout=30,
        ) as response:
            action_cache.write_bytes(response.read())
    (tmp_path / "action.yml").write_text(action_cache.read_text())
    subprocess.run(["git", "apply", str(patch)], cwd=tmp_path, check=True)
    assert (
        'export REPO_PATH="${SECURITY_REVIEW_REPO_PATH:?Review source path is required}"'
        in (tmp_path / "action.yml").read_text()
    )
    parsed = ast.parse(target.read_text())
    client_class = next(
        item
        for item in parsed.body
        if isinstance(item, ast.ClassDef) and item.name == "GitHubActionClient"
    )
    specification = importlib.util.spec_from_file_location(
        "local_diff", ROOT / ".github/security-review/local_diff.py"
    )
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    monkeypatch.setitem(sys.modules, "local_diff", module)
    namespace: dict[str, Any] = {
        "os": os,
        "sys": sys,
        "re": re,
        "requests": requests,
        "Dict": dict,
        "Any": Any,
        "Path": Path,
    }
    exec(compile(ast.Module(body=[client_class], type_ignores=[]), str(target), "exec"), namespace)
    monkeypatch.setenv("GITHUB_TOKEN", "not-a-real-token")
    factory = cast(Callable[[], Client], namespace["GitHubActionClient"])
    return factory()


def response(payload: object, next_page: bool = False) -> requests.Response:
    value = requests.Response()
    value.status_code = 200
    value._content = json.dumps(payload).encode()  # pyright: ignore[reportPrivateUsage]
    if next_page:
        value.headers["Link"] = '<https://api.github.com/unused>; rel="next"'
    return value


def metadata(count: int, head: str = "1" * 40, base: str = "2" * 40) -> dict[str, object]:
    return {
        "number": 266,
        "title": "Large release",
        "body": "",
        "user": {"login": "operator"},
        "created_at": "",
        "updated_at": "",
        "state": "open",
        "additions": count,
        "deletions": 0,
        "changed_files": count,
        "head": {"ref": "dev", "sha": head, "repo": {"full_name": "vals-ai/valsmith"}},
        "base": {"ref": "prod", "sha": base},
    }


def file_rows(count: int) -> list[dict[str, object]]:
    return [
        {
            "filename": f"file-{number}.py",
            "status": "added",
            "additions": 1,
            "deletions": 0,
            "changes": 1,
            "patch": "+source",
        }
        for number in range(count)
    ]


def install_api(monkeypatch: pytest.MonkeyPatch, replies: list[requests.Response]) -> list[str]:
    addresses: list[str] = []
    iterator = iter(replies)

    def get(url: str, **_kwargs: object) -> requests.Response:
        addresses.append(url)
        return next(iterator)

    monkeypatch.setattr(requests, "get", get)
    monkeypatch.setenv("SECURITY_REVIEW_HEAD_SHA", "1" * 40)
    monkeypatch.setenv("SECURITY_REVIEW_BASE_SHA", "2" * 40)
    return addresses


def test_file_inventory_reads_every_page(patched_client: Client, monkeypatch: pytest.MonkeyPatch):
    files = file_rows(316)
    addresses = install_api(
        monkeypatch,
        [response(metadata(316))]
        + [
            response(files[start : start + 100], next_page=start < 300)
            for start in range(0, 316, 100)
        ],
    )
    data = patched_client.get_pr_data("vals-ai/valsmith", 266)
    assert len(data["files"]) == 316
    assert data["files"][-1]["filename"] == "file-315.py"
    assert addresses[-1].endswith("files?per_page=100&page=4")


def test_truncated_inventory_is_not_a_clean_review(
    patched_client: Client, monkeypatch: pytest.MonkeyPatch
):
    install_api(monkeypatch, [response(metadata(316)), response(file_rows(100))])
    with pytest.raises(ValueError, match="incomplete"):
        patched_client.get_pr_data("vals-ai/valsmith", 266)


def test_moved_head_is_rejected(patched_client: Client, monkeypatch: pytest.MonkeyPatch):
    install_api(monkeypatch, [response(metadata(1, head="3" * 40)), response(file_rows(1))])
    with pytest.raises(ValueError, match="revision"):
        patched_client.get_pr_data("vals-ai/valsmith", 266)


def test_moved_base_is_rejected(patched_client: Client, monkeypatch: pytest.MonkeyPatch):
    install_api(monkeypatch, [response(metadata(1, base="3" * 40)), response(file_rows(1))])
    with pytest.raises(ValueError, match="revision"):
        patched_client.get_pr_data("vals-ai/valsmith", 266)


def test_patched_client_reads_large_git_diff_without_diff_api(
    patched_client: Client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    directory = tmp_path / "source"
    directory.mkdir()

    def git(*arguments: str) -> str:
        return subprocess.check_output(["git", "-C", str(directory), *arguments], text=True).strip()

    git("init", "--quiet", "--initial-branch=main")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    git("commit", "--quiet", "--allow-empty", "-m", "base")
    base = git("rev-parse", "HEAD")
    for number in range(316):
        (directory / f"file-{number}.py").write_text(f"value = {number}\n")
    git("add", ".")
    git("commit", "--quiet", "-m", "head")
    head = git("rev-parse", "HEAD")
    files = file_rows(316)
    addresses = install_api(
        monkeypatch,
        [response(metadata(316, head, base))]
        + [
            response(files[start : start + 100], next_page=start < 300)
            for start in range(0, 316, 100)
        ]
        + [response(metadata(316, head, base))],
    )
    monkeypatch.setenv("SECURITY_REVIEW_HEAD_SHA", head)
    monkeypatch.setenv("SECURITY_REVIEW_BASE_SHA", base)
    monkeypatch.setenv("REPO_PATH", str(directory))
    assert len(patched_client.get_pr_data("vals-ai/valsmith", 266)["files"]) == 316
    difference = patched_client.get_pr_diff("vals-ai/valsmith", 266)
    assert difference.count("diff --git ") == 316
    assert "+value = 315\n" in difference
    assert len(addresses) == 6


def test_revision_change_after_inventory_stops_diff(
    patched_client: Client, monkeypatch: pytest.MonkeyPatch
):
    install_api(
        monkeypatch,
        [response(metadata(1)), response(file_rows(1)), response(metadata(1, head="3" * 40))],
    )
    patched_client.get_pr_data("vals-ai/valsmith", 266)
    with pytest.raises(ValueError, match="revision"):
        patched_client.get_pr_diff("vals-ai/valsmith", 266)
