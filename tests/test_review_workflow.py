from pathlib import Path
from typing import Any, cast

import yaml


def test_scanner_and_helper_checkouts_are_pinned_outside_reviewed_tree():
    root = Path(__file__).parents[1]
    workflow = cast(
        dict[str, Any],
        yaml.safe_load((root / ".github/workflows/claude-security-review.yml").read_text()),
    )
    steps = cast(list[dict[str, Any]], workflow["jobs"]["review"]["steps"])
    source = next(step for step in steps if step.get("name") == "Check out the exact PR revision")
    assert source["with"]["path"] == "source"
    assert source["with"]["fetch-depth"] == 0
    assert source["with"]["persist-credentials"] is False
    checkouts = [step for step in steps if step.get("with", {}).get("repository")]
    assert {step["with"]["repository"] for step in checkouts} == {
        "vals-ai/.github",
        "anthropics/claude-code-security-review",
    }
    for checkout in checkouts:
        settings = checkout["with"]
        assert len(settings["ref"]) == 40
        assert settings["path"] in {".security-review-action", ".security-review-tools"}
        assert settings["persist-credentials"] is False
        assert checkout["if"] == "steps.credential.outputs.available == 'true'"
    review = next(step for step in steps if step.get("name") == "Review changes")
    assert review["uses"] == "./.security-review-action"
    assert review["env"]["SECURITY_REVIEW_REPO_PATH"] == "${{ github.workspace }}/source"
    assert review["env"]["SECURITY_REVIEW_HEAD_SHA"] == "${{ github.event.pull_request.head.sha }}"
    assert review["env"]["SECURITY_REVIEW_BASE_SHA"] == "${{ github.event.pull_request.base.sha }}"
    assert any(step.get("name") == "Verify the scanner completed" for step in steps)
