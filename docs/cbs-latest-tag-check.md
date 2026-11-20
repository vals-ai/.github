# CBS Latest Tag Check

Use `.github/workflows/validate-cbs-latest-tag.yaml` to fail CI when the locked `create-benchmark-service` package does not install as the latest tagged release.

It reads the source from `uv.lock`. A service installing from `vals-ai/Valkyrie` is checked against the latest `cbs-v*` tag there, and one still on `vals-ai/create-benchmark-service` against that repository's latest `v*` tag.

Add this workflow to a benchmark service:

```yaml
name: cbs-latest-check

on:
  pull_request:
  push:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  cbs:
    uses: vals-ai/.github/.github/workflows/validate-cbs-latest-tag.yaml@main
```
