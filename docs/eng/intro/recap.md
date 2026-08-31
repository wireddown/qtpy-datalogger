---
icon: lucide/message-square-code
tags:
  - Develop
  - Introduction
  - Recap
---

# Recap

All the steps for installing tools and initializing the environment are on this page.
Collected from our [Guides](tools/) and [Environment](environment/) pages, these terminal commands prepare a **new** workstation for development.

Visit our [Workflows](workflows/) and [References](references/) pages for more brief summaries.

## Recipe

```pwsh title="PowerShell"
# Install VS Code
winget install --exact --id=Microsoft.VisualStudioCode
winget install --exact --id=Microsoft.VisualStudioCode.CLI

# Install VS Code extensions
code --install-extension  astral-sh.ty
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

# Configure Mosquitto
$mqttSettings = @(
    "listener 1883"
    "allow_anonymous true"
)
Add-Content -Path "C:\Program Files\mosquitto\mosquitto.conf" -Value $mqttSettings

# Configure Windows firewall
netsh advfirewall firewall add rule `
  name='Mosquitto MQTT: allow inbound on port 1883 from local subnet' `
  program='C:\Program Files\mosquitto\mosquitto.exe' dir=in action=allow service=any `
  description='Allow MQTT clients on the local subnet to connect to this host' `
  profile=private localip=any remoteip=localsubnet `
  localport=1883 remoteport=any protocol=tcp interfacetype=any

# Confirm MQTT server readiness
uv run qtpy-datalogger server
```

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py to your workstation with USB"

```pwsh title="PowerShell"
# Confirm QT Py detection
uv run qtpy-datalogger connect --discover-only

# Install and configure the sensor node runtime
uv run qtpy-datalogger equip --secrets -

# Confirm sensor node readiness
uv run qtpy-datalogger equip --compare

# Send a message to the QT Py sensor node over WiFi
uv run qtpy-datalogger run scanner
```
