from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from typing import Protocol, cast

import pytest


class DiffModule(Protocol):
    def read_diff(self, repository: Path, base: str, head: str) -> str: ...


def implementation() -> DiffModule:
    path = Path(__file__).parents[1] / ".github/security-review/local_diff.py"
    assert path.exists(), "Local Git diff implementation is missing"
    specification = importlib.util.spec_from_file_location("local_diff", path)
    assert specification and specification.loader
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return cast(DiffModule, cast(object, module))


def git(repository: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(repository), *arguments], text=True).strip()


@pytest.fixture
def repository(tmp_path: Path) -> tuple[Path, str, str]:
    git(tmp_path, "init", "--quiet", "--initial-branch=main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.invalid")
    (tmp_path / "original.py").write_text("before = 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "-m", "base")
    base = git(tmp_path, "rev-parse", "HEAD")
    git(tmp_path, "switch", "--quiet", "-c", "feature")
    for number in range(316):
        (tmp_path / f"change-{number:03}.py").write_text(f"value = {number}\n")
    git(tmp_path, "mv", "original.py", "renamed.py")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "--quiet", "-m", "large change")
    head = git(tmp_path, "rev-parse", "HEAD")
    return tmp_path, base, head


def test_all_files_beyond_api_limit_and_rename_are_present(repository: tuple[Path, str, str]):
    directory, base, head = repository
    difference = implementation().read_diff(directory, base, head)
    assert difference.count("diff --git ") == 317
    assert "+value = 315\n" in difference
    assert "rename from original.py\nrename to renamed.py" in difference


def test_uses_merge_base_without_base_only_changes(repository: tuple[Path, str, str]):
    directory, base, head = repository
    git(directory, "switch", "--quiet", "main")
    (directory / "base-only.py").write_text("not_in_pull_request = True\n")
    git(directory, "add", ".")
    git(directory, "commit", "--quiet", "-m", "base advanced")
    advanced_base = git(directory, "rev-parse", "HEAD")
    git(directory, "switch", "--quiet", "feature")
    assert implementation().read_diff(directory, advanced_base, head) == implementation().read_diff(
        directory, base, head
    )


def test_wrong_checkout_stops_review(repository: tuple[Path, str, str]):
    directory, base, head = repository
    git(directory, "checkout", "--quiet", base)
    with pytest.raises(ValueError, match="head"):
        implementation().read_diff(directory, base, head)


@pytest.mark.parametrize("revision", ["main", "--output=/tmp/unsafe", "0" * 40])
def test_invalid_or_missing_revision_stops_review(repository: tuple[Path, str, str], revision: str):
    directory, _, head = repository
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        implementation().read_diff(directory, revision, head)


def test_missing_history_stops_review(repository: tuple[Path, str, str], tmp_path: Path):
    directory, base, head = repository
    shallow = tmp_path / "shallow"
    subprocess.run(
        ["git", "clone", "--quiet", "--depth=1", directory.as_uri(), str(shallow)], check=True
    )
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        implementation().read_diff(shallow, base, head)


def test_dirty_tracked_source_stops_review(repository: tuple[Path, str, str]):
    directory, base, head = repository
    (directory / "change-000.py").write_text("modified_after_checkout = True\n")
    with pytest.raises((ValueError, subprocess.CalledProcessError)):
        implementation().read_diff(directory, base, head)


def test_disables_external_diff_command(repository: tuple[Path, str, str]):
    directory, base, head = repository
    git(directory, "config", "diff.external", "false")
    assert "+value = 315\n" in implementation().read_diff(directory, base, head)
