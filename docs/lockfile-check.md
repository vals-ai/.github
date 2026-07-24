# Lockfile Check

Use `.github/workflows/validate-lockfile.yaml` to fail CI when `pyproject.toml` and `uv.lock` disagree. This catches dependency changes in `pyproject.toml` when `uv.lock` is still pinned to an older resolved commit, tag, or version.

Add this workflow to a service repo:

```yaml
name: lockfile-check

on:
  pull_request:
  push:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  validate:
    uses: vals-ai/.github/.github/workflows/validate-lockfile.yaml@main
    secrets:
      GH_PAT: ${{ secrets.GH_PAT }}
      SSH_PRIVATE_KEY: ${{ secrets.SUBMODULES_SSH_KEY }}
```

The shared workflow runs:

```bash
uv lock --check --project "$PROJECT_PATH"
```

For most repositories the default `project_path: "."` is enough. If the Python project lives under a subdirectory, pass it explicitly:

```yaml
jobs:
  validate:
    uses: vals-ai/.github/.github/workflows/validate-lockfile.yaml@main
    with:
      project_path: valkyrie_service
```

If the project has local path dependencies provided by git submodules, enable submodule checkout:

```yaml
jobs:
  validate:
    uses: vals-ai/.github/.github/workflows/validate-lockfile.yaml@main
    with:
      submodules: true
```

Pass `GH_PAT` only for repos with private `https://github.com/...` git dependencies. Pass `SSH_PRIVATE_KEY` only for repos with private `git+ssh://git@github.com/...` or `ssh://git@github.com/...` dependencies. Public-only services can omit `secrets:` entirely.
