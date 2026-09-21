# Claude security review

Each repository calls the pinned reusable workflow in `.github/workflows/claude-security-review.yml`. Findings are advisory; existing CI and branch protection remain unchanged.

## Setup

Set the vals-ai organization Actions secret `ANTHROPIC_SECURITY_REVIEW_API_KEY` to a dedicated Anthropic inference API key, with access to enrolled repositories. The retained backup is `management/claude-security-review` in vals-bench Secrets Manager (`us-east-1`), managed through shared-infra. Rotations must update both copies. Scanner jobs have no AWS permissions or application secrets.

Use an Anthropic workspace spending limit. The workflow's 30-minute job limit and 20-minute scanner timeout are not monetary caps. Reviewing sends repository code to Anthropic.

## Behavior

Review non-draft, same-repository PRs whose authors currently have repository write access. Forks, bots, and authors without write access skip. The gate checks current permissions because webhook author-association metadata can be stale. The upstream reviewer is not hardened against prompt injection; internal PRs containing copied external code still require human judgment.

Run on opened, synchronized, reopened, and ready-for-review PRs. Cancel obsolete runs and review every revision; upstream otherwise scans only once per PR. Missing credentials emit an explicit skipped-review warning. Missing, malformed, error, and explicitly incomplete scanner results fail the job rather than reporting a clean review.

The workflow uses GitHub-hosted runners, read-only contents access, PR-comment permission, and checkout without persisted credentials. Findings and debug artifacts are retained for seven days. Review Actions log/artifact access accordingly.

## Maintenance

The reusable workflow, upstream action, and checkout are pinned to commits. Upstream still installs floating Python dependencies and the latest Claude Code CLI; the action pin does not pin those dependencies. Review central changes and update caller pins deliberately.

To disable a repository, remove its caller or secret access. New repositories need a caller; workflows are not automatically inherited from `.github`. Archived and uninitialized repositories are excluded from rollout.
