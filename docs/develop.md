---
icon: lucide/keyboard
tags:
  - Develop
  - Contribute
---

# Develop

This is a crash course introducing the tools and libraries used in the project.

## Setup

??? question "New to git and Python?"

    If these tools and commands are not on your system, follow the introductory [Guide pages](eng/intro/tools).

### Requirements

- :fontawesome-brands-git-alt:{ .lg .middle }&nbsp; `git`
- :fontawesome-brands-python:{ .lg .middle }&nbsp; Python and `uv`
- :fontawesome-solid-wifi:{ .lg }&nbsp; MQTT broker

### Do once

**1. Get the source**

```pwsh
# Clone from GitHub
git clone https://github.com/wireddown/qtpy-datalogger.git
cd qtpy-datalogger
```

**2. Initialize the environment**

```pwsh
# Install the package's dependencies
uv sync
```

**3. Setup the MQTT broker**

```pwsh
# Install Mosquitto Broker
winget install --exact --id=EclipseFoundation.Mosquitto
```

Once installed, [configure](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-5-MQTT) the MQTT broker

**4. Initialize QT Py device**

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py device to your workstation with USB"

```pwsh
# Install and configure the sensor node runtime
uv run qtpy-datalogger equip --secrets -
```

### Ready check

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py device to your workstation with USB"

```pwsh
# Get latest from upstream
git switch main
git pull

# Install the dependencies
uv sync

# Confirm dependencies are satisfied
uv sync --check

# Confirm GUI component readiness
uv run qtpy-datalogger run data-viewer

# Confirm MQTT server readiness
uv run qtpy-datalogger server

# Confirm QT Py detection
uv run qtpy-datalogger connect --discover-only

# Confirm node readiness
uv run qtpy-datalogger equip --compare

# Send a message to the QT Py over WiFi
uv run qtpy-datalogger run scanner
```

## Workflows

### Create a branch

```pwsh
# Get upstream changes
git switch main
git pull

# Create a new branch from main
git switch --create users/__YOU__/__NEW_TOPIC__

# Or update an existing branch
# * Switch to your branch
#   git switch users/__YOU__/__EXISTING_TOPIC__
# * Rebase or merge
#   A: Replay and resolve your changes on the latest main
#      git rebase origin/main
#   B: Merge and resolve your changes with the latest main
#      git merge origin/main

# Install dependency updates
uv sync

# Run the program
uv run qtpy-datalogger [OPTIONS]
```

### PC dev loop

??? info "Monitor the messages sent between nodes and the host"
    ```pwsh
    uv run qtpy-datalogger server --observe
    ```

```pwsh
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

### QT Py dev loop

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py device to your workstation with USB"

??? info "Monitor the messages sent between nodes and the host"
    ```pwsh
    uv run qtpy-datalogger server --observe
    ```

??? info "Monitor the main run loop on the QT Py node"
    ```pwsh
    uv run qtpy-datalogger connect --port COMxx
    ```

```pwsh
# ✍️ Save source code changes

# Update the code on the QT Py device
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

### Documentation dev loop

```pwsh
# Build the documentation site
uv run poe docs

# Locally serve the documentation site
uv run zensical serve

# Confirm and observe changes in the site
start http://localhost:8000

# ✍️ Save documentation changes
```

## References

### For this project

Design documents for this project are in the wiki under the [**Design Doc X**](https://github.com/wireddown/qtpy-datalogger/wiki/Design-Doc-1-Overview) series.

### For support libraries

| Name            | Purpose                                                                        | Link |
|-----------------|--------------------------------------------------------------------------------|------|
|                 |                                                                                |      |
| **Host PC**     |                                                                                |      |
| Python          | :fontawesome-solid-worm:{ .lg .qtpy }&nbsp;                           Language | [python.org](https://docs.python.org/3.11/index.html) |
|                 | :lucide-book-open-text:{ .lg .middle }&nbsp;                Language reference | [python.org](https://docs.python.org/3.11/reference/index.html) |
|                 | :lucide-library-big:{ .lg }&nbsp;                             Standard library | [python.org](https://docs.python.org/3.11/library/index.html) |
| uv              | :fontawesome-solid-gear:{ .lg }&nbsp;                                Core tool | [astral.sh](https://docs.astral.sh/uv/) |
| poe             | :fontawesome-solid-gear:{ .lg }&nbsp;                                Core tool | [natn.io](https://poethepoet.natn.io/index.html) |
| ruff            | :fontawesome-solid-microscope:{ .lg }&nbsp;                      Code analyzer | [astral.sh](https://docs.astral.sh/ruff/) |
| pyright         | :fontawesome-solid-microscope:{ .lg }&nbsp;                      Code analyzer | [github.io](https://microsoft.github.io/pyright) |
| pytest          | :fontawesome-solid-flask:{ .lg }&nbsp;                             Test runner | [pytest.org](https://docs.pytest.org/en/stable/) |
| zensical        | :fontawesome-solid-book:{ .lg }&nbsp;                            Documentation | [zensical.org](https://zensical.org/docs/get-started/) |
| click           | :fontawesome-solid-terminal:{ .lg .middle }&nbsp;       Command line interface | [palletsprojects.com](https://click.palletsprojects.com/en/stable/) |
| pySerial        | :fontawesome-solid-square-binary:{ .lg .middle }&nbsp;          Serial port IO | [readthedocs.io](https://pyserial.readthedocs.io/en/stable/pyserial.html) |
| wmi             | :fontawesome-brands-windows:{ .lg }&nbsp;            Windows system inspection | [me.uk](https://timgolden.me.uk/python/wmi/contents.html) |
| psutil          | :fontawesome-solid-toolbox:{ .lg .middle }&nbsp;  System and process utilities | [readthedocs.io](https://psutil.readthedocs.io/en/stable/) |
| gmqtt           | :fontawesome-solid-envelope:{ .lg .middle }&nbsp;                  MQTT client | [github.com](https://github.com/wialon/gmqtt) |
| mosquitto       | :fontawesome-solid-satellite-dish:{ .lg }&nbsp;                    MQTT server | [mosquitto.org](https://mosquitto.org/) |
| ttkbootstrap    | &nbsp;:fontawesome-solid-arrow-pointer:&nbsp;                    GUI extension | [readthedocs.io](https://ttkbootstrap.readthedocs.io/en/latest/) |
| pandas          | :fontawesome-solid-table:{ .lg .middle }&nbsp;                 Data processing | [pydata.org](https://pandas.pydata.org/docs/) |
| matplotlib      | :fontawesome-solid-chart-line:{ .lg .middle }&nbsp;                   Plotting | [matplotlib.org](https://matplotlib.org/stable/) |
| circup          | :fontawesome-solid-microchip:{ .lg .middle }&nbsp;                  QT Py tool | [readthedocs.io](https://circup.readthedocs.io/en/stable/) |
|                 |                                                                                |      |
| **Sensor node** |                                                                                |      |
| MicroPython     | :fontawesome-solid-microchip:{ .lg .middle }&nbsp;                  Supervisor | [micropython.org](https://docs.micropython.org/en/v1.23.0/genrst/index.html) |
| CircuitPython   | :fontawesome-solid-worm:{ .lg .qtpy }&nbsp;                           Language | [adafruit.com](https://learn.adafruit.com/welcome-to-circuitpython/overview) |
|                 | :lucide-library-big:{ .lg }&nbsp;                             Standard library | [circuitpython.org](https://docs.circuitpython.org/en/stable/docs/library/index.html) |
|                 | :lucide-blocks:{ .lg }&nbsp;                                      Core modules | [circuitpython.org](https://docs.circuitpython.org/en/stable/shared-bindings/index.html) |
| Drivers         | :fontawesome-solid-stethoscope:{ .lg .middle }&nbsp;            Sensor support | [circuitpython.org](https://docs.circuitpython.org/projects/bundle/en/stable/drivers.html) |
| MiniMQTT        | :fontawesome-solid-envelope:{ .lg .middle }&nbsp;                  MQTT client | [circuitpython.org](https://docs.circuitpython.org/projects/minimqtt/en/stable/index.html) |
| ASCII           | :lucide-binary:{ .lg .middle }&nbsp;               Binary codes for characters | [ss64.com](https://ss64.com/ascii.html) |
| XTerm           | :fontawesome-solid-keyboard:{ .lg .middle }&nbsp; Code sequences for terminals | [invisible-island.net](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html) |

## Pull requests and Issues

See the sections under the [Project Workflows](https://github.com/wireddown/qtpy-datalogger/wiki/Project-Workflows) wiki page for outlines.
