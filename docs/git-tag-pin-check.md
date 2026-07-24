# Git Tag Pin Check

Use `.github/workflows/validate-git-tag-pin.yaml` to fail CI when a git dependency pin in `pyproject.toml` does not match the latest allowed tag in that dependency's repository.

Add this workflow to a repository:

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
    uses: vals-ai/.github/.github/workflows/validate-git-tag-pin.yaml@main
```

By default this checks `create-benchmark-service` against the latest `v*` tag in `https://github.com/vals-ai/create-benchmark-service.git`.

For another dependency, pass the dependency name, repository URL, and optional tag pattern:

```yaml
jobs:
  dependency:
    uses: vals-ai/.github/.github/workflows/validate-git-tag-pin.yaml@main
    with:
      dependency_name: example-package
      repository_url: https://github.com/example/example-package.git
      tag_pattern: refs/tags/v*
```
