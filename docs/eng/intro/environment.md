---
icon: lucide/monitor-cog
tags:
  - Develop
  - Contribute
  - Environment
---

# Environment

This page is a crash course introducing the tools and libraries used in the project.
Continue reading if you want to contribute to or customize `qtpy-datalogger`.

## Software requirements

Before you can start developing, you need to download the source and install the software requirements on your workstation.

- :fontawesome-brands-windows:{ .lg .middle }&nbsp; Windows 11 or Windows 10
- :fontawesome-brands-git-alt:{ .lg .middle }&nbsp; `git`
- :fontawesome-brands-python:{ .lg .middle }&nbsp; Python and `uv`
- :fontawesome-solid-wifi:{ .lg }&nbsp; MQTT broker

??? question "New to git and Python?"

    If these tools and commands are not on your system, follow the **[Onboarding guides](tools/)**.

## 1. Get the source

```pwsh title="Powershell"
# Clone from GitHub
git clone https://github.com/wireddown/qtpy-datalogger.git
cd qtpy-datalogger
```

## 2. Initialize the environment

```pwsh title="Powershell"
# Install the package's dependencies
uv sync
```

## 3. Setup the MQTT broker

Run these commands to install and configure the Mosquitto MQTT broker.

!!! info "For details, see the [MQTT](mqtt/) page"

```pwsh title="Administrator Powershell"
# Install Mosquitto Broker
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
```

## 4. Initialize the QT Py

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py to your workstation with USB"

```pwsh title="Powershell"
# Install and configure the sensor node runtime
uv run qtpy-datalogger equip --secrets -
```

When prompted:

- set the WiFi SSID and password
- set the broker IP address

## 5. Ready check

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py to your workstation with USB"

Run these commands to confirm that your workstation is ready to develop.

```pwsh title="Powershell"
# Get latest source and dependencies from upstream
git switch main
git pull
uv sync

# Confirm dependencies are satisfied
uv sync --check

# Confirm GUI component readiness
uv run qtpy-datalogger run data-viewer

# Confirm MQTT server readiness
uv run qtpy-datalogger server

# Confirm QT Py detection
uv run qtpy-datalogger connect --discover-only

# Confirm sensor node readiness
uv run qtpy-datalogger equip --compare

# Send a message to the QT Py sensor node over WiFi
uv run qtpy-datalogger run scanner
```
