# Claude security review

The reusable `.github/workflows/claude-security-review.yml` runs Anthropic's reviewer on PR changes. Repository callers pin this workflow to a reviewed commit. Findings are advisory; existing CI and branch protection remain unchanged.

## Coverage and trust

Callers trigger on opened, synchronized, reopened, and ready-for-review pull requests. Only non-draft, same-repository PRs authored by users with current repository write access run. Forks, authors without write access, and bots skip. The gate queries current collaborator permissions because webhook author-association metadata can be stale.

The upstream action is not hardened against prompt injection. Internal PRs containing copied external code still require human judgment. Reviewing sends repository code to Anthropic. Use a dedicated Anthropic inference key with a workspace spending limit, not an Anthropic Admin API key.

## AWS credential access

AWS Secrets Manager is the only persistent store for the key: `management/claude-security-review` in vals-bench, region `us-east-1`. Store the raw key in SecretString separately from CloudFormation. No GitHub API-key secret is needed, and rotating the AWS value takes effect on the next run.

After checking author permissions, the workflow uses GitHub OIDC to assume `shared-infra-claude-security-review` for 15 minutes. Its only permission is GetSecretValue on the dedicated secret. IAM trust requires the Vals organization ID, a PR subject, and the exact approved reusable-workflow commit. Existing repository OIDC subject settings are unchanged. Both legacy and immutable GitHub subject formats are accepted.

The key is fetched before checking out PR code, masked, and passed to the action. AWS credentials are scoped to the retrieval step, not exported to scanner processes. The key necessarily exists in the scanner process for the duration of the job. Retrieval, authentication, and scanner errors fail the job explicitly; an unavailable review is not a clean result.

The retained secret's resource policy permits reads by administrators and this reader role, while changes remain restricted to administrators and the shared-infra deployment executor. Other management secrets remain administrator-readable only. The infrastructure and approved workflow revision are maintained in shared-infra.

## Operation

Each caller cancels obsolete runs through concurrency and scans every new PR revision. The upstream default scans only once per PR and would miss later changes. A run has a 30-minute job limit and 20-minute scanner timeout. These are not monetary caps; enforce the budget in Anthropic.

The action and AWS/checkout dependencies use commit pins. The upstream action still installs the latest Claude Code CLI and floating Python dependencies; the action pin does not pin those transitive dependencies. Its model default comes from the pinned action.

The wrapper rejects missing, malformed, explicit-error, and explicitly incomplete scanner results, because upstream can otherwise exit successfully on scanner failure. Findings and debug logs remain in the upstream artifact for seven days; review Actions access accordingly.

For an upgrade, review and publish the new reusable-workflow commit, authorize its exact revision in the AWS role through shared-infra, and update caller pins. Keep the prior reviewed revision authorized during a staged upgrade, then remove it after all callers move. Never replace the exact workflow condition with a wildcard.

To disable a repository, remove its caller. To revoke all review access, remove the workflow revision from the role trust policy. Archived and uninitialized repositories are excluded from rollout. New repositories need the caller; GitHub does not automatically inherit workflows from `.github`.
