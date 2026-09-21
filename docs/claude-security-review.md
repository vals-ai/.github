# Claude security review

The reusable `.github/workflows/claude-security-review.yml` runs Anthropic's security reviewer on pull request changes. Repository callers pin this workflow to a reviewed commit and pass only `ANTHROPIC_SECURITY_REVIEW_API_KEY`. Existing tests and branch protection remain unchanged; findings are advisory.

## Coverage and trust

Callers trigger on opened, synchronized, reopened, and ready-for-review pull requests. Only non-draft, same-repository PRs authored by users with current repository write access run. Forks, authors without write access, and bots skip. The gate queries current collaborator permissions because webhook author-association metadata can be stale. An internal PR containing copied external code still needs human judgment: the upstream action is not hardened against prompt injection.

Use GitHub-hosted ephemeral runners, read-only contents access, PR-comment permission, no persisted checkout credential, no AWS role, and no application secrets. Do not change this to `pull_request_target` or enable fork secrets. A dedicated, budget-limited Anthropic workspace/key confines exposure to review usage. Reviewing sends repository code to Anthropic.

The workflow cancels obsolete runs through each caller's concurrency group and scans every new revision. The upstream default scans only once per PR, which would miss fixes and later changes. A run has a 30-minute job limit and 20-minute scanner timeout. This is not a monetary spending cap: enforce a workspace budget in Anthropic.

## Credential setup

The source credential is `management/claude-security-review` in the vals-bench AWS Secrets Manager account, region `us-east-1`, managed in shared-infra. Store a dedicated Anthropic inference API key as its raw SecretString, separately from CloudFormation. The secret is retained and administrator-readable only. This is an inference key, not an Anthropic Admin API key.

Mirror it into the vals-ai organization Actions secret `ANTHROPIC_SECURITY_REVIEW_API_KEY`, selecting enrolled repositories (including public repositories when intended). Use the AWS CLI and `gh secret set` through a pipe or in-memory subprocess input; never put the value in a command argument, committed file, log, or PR. Updating AWS alone does not rotate the GitHub copy. The setup operator needs GitHub organization secret administration access.

Until configured, eligible jobs emit a warning and a summary explicitly stating that the review was skipped. A successful skipped job is not evidence of a completed security review. Do not make this check required while provisioning it.

## Operation

The action and checkout use immutable commit pins. The upstream action still installs the latest Claude Code CLI and floating Python dependencies; the action pin does not pin those transitive dependencies. Its default model comes from that pinned action. Upgrade the central workflow deliberately and update caller pins together.

The wrapper rejects missing, malformed, explicit-error, and explicitly incomplete scanner results, because upstream can otherwise exit successfully on a scanner error. Findings and debug output remain in the upstream artifact for seven days. Review access to Actions logs and artifacts accordingly.

To disable scanning for a repository, remove its caller workflow or its access to the dedicated secret. To rotate, replace the AWS value and then the GitHub Actions secret. Archived and empty repositories are excluded from the initial rollout; add a caller when an empty repository gets its first commit. Future repositories need the caller too; GitHub does not automatically inherit workflows from `.github`.
