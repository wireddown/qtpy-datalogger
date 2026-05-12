---
icon: lucide/radar
tags:
  - Help
  - Troubleshoot
---

# Troubleshoot

## Runtime environment

If you're using the package but something isn't working correctly, open a PowerShell window in the package's folder and run these commands to show information about its environment.

```pwsh title="PowerShell"
# Activate the package's environment
.\.venv\Scripts\activate.ps1

# Connect the QT Py with USB and confirm detection
qtpy-datalogger connect --discover-only

# Detect and show differences between the QT Py sensor node and the package
qtpy-datalogger equip --compare

# Confirm MQTT server readiness
qtpy-datalogger server

# Find and communicate with the QT Py sensor node over the network
qtpy-datalogger run scanner
```

## Development environment

If you're customizing or contributing, run these commands to show information about the tools' versions and configuration.

```pwsh title="PowerShell"
# What are the environment variables?
env

# Is a command callable? Where is it?
Get-Command uv

# Show details about uv
uv self version

# List the commands installed by uv
uv tool list

# Show installed and selectable versions of Python
uv python list --only-installed

# Show the active version of Python in this folder
uv python find --show-version

# Confirm dependencies are satisfied
uv sync --check

# Show the packages installed in this Python environment
uv tree

# Show VS Code extension information
code --list-extensions --show-versions
```
