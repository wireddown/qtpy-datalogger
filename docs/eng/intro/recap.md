---
icon: lucide/message-square-quote
tags:
  - Develop
  - Introduction
  - Recap
---

# Recap

All the steps for installing tools and initializing the environment are on this page.
Collected from the [Guides](eng/intro/tools) and [Develop](develop) pages, these terminal commands prepare a **new** workstation for development.

For [Workflows](develop/#workflows) and [References](develop/#references), visit the **Develop** page.

## Recipe

```pwsh
# Install VS Code
winget install --exact --id=Microsoft.VisualStudioCode
winget install --exact --id=Microsoft.VisualStudioCode.CLI

# Install VS Code extensions
code --install-extension  bierner.github-markdown-preview
code --install-extension  charliermarsh.ruff
code --install-extension  donjayamanne.git-extension-pack
code --install-extension  ms-python.python
code --install-extension  ms-toolsai.jupyter
code --install-extension  tamasfe.even-better-toml

# Install Windows Terminal
winget install --exact --id=Microsoft.WindowsTerminal

# Install PowerShell
winget install --exact --id=Microsoft.PowerShell

# Install ScreeToGif
winget install --exact --id=NickeManarin.ScreenToGif

# Install git
winget install --exact --id=Git.Git

# Install GitHub Desktop
winget install --exact --id=GitHub.GitHubDesktop

# Disable the Windows Python aliases
rm "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\python.exe"
rm "$env:USERPROFILE\AppData\Local\Microsoft\WindowsApps\python3.exe"

# Install uv
winget install --exact --id=astral-sh.uv

# Install the latest release of a Python version
uv python install 3.11

# Set the default version of Python
uv pin --global 3.11

# Clone from GitHub
git clone https://github.com/wireddown/qtpy-datalogger.git
cd qtpy-datalogger

# Install the package's dependencies
uv sync

# Confirm GUI component readiness
uv run qtpy-datalogger run data-viewer

# Install an MQTT broker
winget install --exact --id=EclipseFoundation.Mosquitto
```

!!! failure "Before continuing, [configure](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-5-MQTT) the MQTT broker"

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py device to your workstation with USB"

```pwsh
# Confirm MQTT server readiness
uv run qtpy-datalogger server

# Confirm QT Py detection
uv run qtpy-datalogger connect --discover-only

# Install and configure the sensor node runtime
uv run qtpy-datalogger equip --secrets -

# Confirm node readiness
uv run qtpy-datalogger equip --compare

# Send a message to the QT Py over WiFi
uv run qtpy-datalogger run scanner
```
