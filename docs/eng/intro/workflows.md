---
icon: lucide/rocket
tags:
  - Develop
  - Contribute
  - Workflows
---

# Workflows

We recommend these typical development recipes and loops.

## Create a branch

```pwsh title="Powershell"
# Get upstream changes
git switch main
git pull

# Create a new branch from main
git switch --create users/__YOU__/__NEW_TOPIC__

# Or update an existing branch
# 1. Switch to your branch
#    git switch users/__YOU__/__EXISTING_TOPIC__
# 2. Rebase or merge
#    A. Replay and resolve your changes on the latest main
#       git rebase --autostash origin/main
#    B. Merge and resolve your changes with the latest main
#       git merge origin/main

# Install dependency updates
uv sync

# Run the program
uv run qtpy-datalogger [OPTIONS]
```

## PC dev loop

??? info "Monitor the messages sent between sensor nodes and the host"
    ```pwsh
    uv run qtpy-datalogger server --observe
    ```

```pwsh title="Powershell"
# ✍️ Save source code changes

# Run the new code
uv run qtpy-datalogger [OPTIONS]

# Run the tests
uv run poe test

# Run the analyzers
uv run poe lint

# Apply the safe analyzer fixes
uv run poe fix
```

## QT Py dev loop

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py to your workstation with USB"

??? info "Monitor the messages sent between sensor nodes and the host"
    ```pwsh
    uv run qtpy-datalogger server --observe
    ```

??? info "Monitor the main run loop on the sensor node"
    ```pwsh
    uv run qtpy-datalogger connect --port COMxx
    ```

```pwsh title="Powershell"
# ✍️ Save source code changes

# Update the code on the QT Py
uv run qtpy-datalogger equip --newer-files-only

# When changes require new support libraries
uv run qtpy-datalogger equip [--force]

# Run new code
uv run qtpy-datalogger [OPTIONS]

# Run the tests
uv run poe test

# Run the analyzers
uv run poe lint

# Apply the safe analyzer fixes
uv run poe fix
```

## Documentation dev loop

```pwsh title="Powershell"
# Build the documentation site
uv run poe docs

# Locally serve the documentation site
uv run zensical serve

# Confirm and observe changes in the site
start http://localhost:8000

# ✍️ Save documentation changes
```
