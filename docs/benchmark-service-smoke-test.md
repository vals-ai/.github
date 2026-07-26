# Benchmark Service Smoke Test

Benchmark service repositories can call `.github/workflows/benchmark-service-smoke.yaml` to build the service, expose it through ngrok, register the temporary URL with Valkyrie, and run one smoke task.

```yaml
name: valkyrie-smoke

on:
  push:
  workflow_dispatch:
    inputs:
      model:
        description: "Optional model override, e.g. openai/gpt-5.5"
        required: false
        type: string

permissions:
  contents: read
  id-token: write

jobs:
  smoke:
    uses: vals-ai/.github/.github/workflows/benchmark-service-smoke.yaml@main
    secrets:
      VALKYRIE_AWS_ROLE_ARN: ${{ secrets.VALKYRIE_AWS_ROLE_ARN }}
      NGROK_AUTHTOKEN: ${{ secrets.NGROK_AUTHTOKEN }}
      NGROK_URL: ${{ secrets.NGROK_URL }}
      SMOKE_DATASET: ${{ secrets.SMOKE_DATASET }}
      SMOKE_TASK_ID: ${{ secrets.SMOKE_TASK_ID }}
      SMOKE_AGENT: ${{ secrets.SMOKE_AGENT }}
      SMOKE_MODEL: ${{ github.event.inputs.model || secrets.SMOKE_MODEL }}
      BENCHMARK_SERVICE_ENV: ${{ secrets.BENCHMARK_SERVICE_ENV }}
      BENCHMARK_SERVICE_AWS_SECRET_REFS: ${{ secrets.BENCHMARK_SERVICE_AWS_SECRET_REFS }}
```

Optional inputs are available when the default repo-name behavior is not enough. Keep the regular required secrets from the example above, then add the extra values needed by that service:

```yaml
jobs:
  smoke:
    uses: vals-ai/.github/.github/workflows/benchmark-service-smoke.yaml@main
    with:
      benchmark_name: harvey
      docker_build_ssh: true
    secrets:
      SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}
```

`BENCHMARK_SERVICE_ENV` is newline-delimited Docker env-file content:

```dotenv
SWEBENCH_EVAL_STATE_BUCKET=agentic-harness-dev-533328366429
JUDGE_MODEL=openai/gpt-5.5
```

The workflow automatically passes `VALS_API_KEY` from the Valkyrie config secret to the service container. Set `VALS_API_KEY` in `BENCHMARK_SERVICE_ENV` only when a service needs to override that value.

When `service_auth_required: true`, the workflow allows the `valkyrie-ci` tenant by default for the configured smoke dataset. Use the `smoke_descope_tenant` input to test with a different tenant. Set `DESCOPE_TENANT_ALLOWLIST_JSON` in `BENCHMARK_SERVICE_ENV` only when a service needs a custom allowlist.

`BENCHMARK_SERVICE_AWS_SECRET_REFS` fetches service runtime secrets from AWS Secrets Manager after GitHub OIDC has assumed the benchmark smoke role. Use one line per env var:

```dotenv
OPENAI_API_KEY=prodBenchmarksInfraApiKeys#OPENAI_API_KEY
VALS_API_KEY=benchmark-services/vcb-vals-api-key
```

Pass repo-specific values through `secrets:` rather than `with:` when they come from GitHub Secrets.
