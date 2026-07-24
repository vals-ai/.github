# CBS Latest Tag Check

Use `.github/workflows/validate-cbs-latest-tag.yaml` to fail CI when the installed `create-benchmark-service` package does not match the latest tagged release.

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
