# Claude security review

The vals-ai organization ruleset runs `.github/workflows/security-review-ruleset.yml` from this public repository at a pinned commit. No workflow files are required in target repositories. Keep the ruleset in **Evaluate** mode for advisory reviews without new merge or push restrictions.

## Setup

Set the vals-ai organization Actions secret `ANTHROPIC_SECURITY_REVIEW_API_KEY` to a dedicated Anthropic inference API key, with access to enrolled repositories. The retained backup is `management/claude-security-review` in vals-bench Secrets Manager (`us-east-1`), managed through shared-infra. Rotations must update both copies. Scanner jobs have no AWS permissions or application secrets.

Use an Anthropic workspace spending limit. The workflow's 30-minute job limit and 20-minute scanner timeout are not monetary caps. Reviewing sends repository code to Anthropic.

## Behavior

Review non-draft, same-repository PRs whose authors currently have repository write access. Forks, bots, and authors without write access skip. The gate checks current permissions because webhook author-association metadata can be stale. The upstream reviewer is not hardened against prompt injection; internal PRs containing copied external code still require human judgment.

Ruleset workflows run on opened, synchronized, and reopened PRs; GitHub ignores event-type filters, including `ready_for_review`. After marking a draft ready, push a commit or reopen the PR to trigger review. Cancel obsolete runs and review every revision; upstream otherwise scans only once per PR. Missing credentials emit an explicit skipped-review warning. Missing, malformed, error, and explicitly incomplete scanner results fail the job rather than reporting a clean review.

The workflow uses GitHub-hosted runners, read-only contents access, PR-comment permission, and checkout without persisted credentials. Findings and debug artifacts are retained for seven days. Review Actions log/artifact access accordingly.

## Maintenance

The reusable workflow, upstream action, and checkout are pinned to commits. Upstream still installs floating Python dependencies and the latest Claude Code CLI; the action pin does not pin those dependencies. Review central changes and update the organization ruleset workflow pin deliberately.

Target all repositories through the organization ruleset so future repositories are included automatically. Target all branches only while using Evaluate mode. Active mode would enforce completion and block direct pushes; do not enable it without narrowing branch targets and deciding the desired merge policy. Exclude repositories through ruleset targeting to disable review. Actions must be enabled and the organization secret must be accessible to each target repository. Changing ruleset targets does not retroactively scan existing PRs; their next synchronize or reopen event triggers review.

The pilot detected command injection and left the argument-list control unflagged. Upstream currently validates its optional false-positive filter against a retired Haiku model, so that filter disables itself and retains findings. Primary Claude analysis and hard exclusions still run; expect more false positives until upstream fixes its validation call.
