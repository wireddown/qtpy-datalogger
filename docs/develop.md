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

    If these tools and commands are not on your system, go to the section [First time setup](#first-time-setup) at the bottom.

### Requirements

- :fontawesome-brands-git-alt:&nbsp; `git`
- :fontawesome-brands-python:&nbsp; Python and `uv`
- :fontawesome-solid-wifi:&nbsp; MQTT broker

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
# Install an MQTT broker
winget install --exact --id=EclipseFoundation.Mosquitto
```

Once installed, [configure](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-5-MQTT) the MQTT broker

**4. Initialize QT Py device**

!!! tip ":lucide-cable:&nbsp; Connect the QT Py device to your workstation with USB"

```pwsh
# Install and configure the sensor node runtime
uv run qtpy-datalogger equip --secrets -
```

### Ready check

!!! tip ":lucide-cable:&nbsp; Connect the QT Py device to your workstation with USB"

```pwsh
# Get latest from upstream
git switch main
git pull

# Install the dependencies
uv sync

# Confirm dependencies are satisfied
uv sync --check

# Confirm MQTT server readiness
uv run qtpy-datalogger server

# Confirm QT Py detection
uv run qtpy-datalogger connect --discover-only

# Confirm node readiness
uv run qtpy-datalogger equip --compare

# Install or upgrade node runtime
uv run qtpy-datalogger equip
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

!!! info "Use `qtpy-datalogger server --observe` to monitor the messages sent between nodes and the host"

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

!!! info "Use `qtpy-datalogger server --observe` to monitor the messages sent between nodes and the host"

!!! info "Use `qtpy-datalogger connect --port COMxx` to monitor the main run loop on the QT Py node"

!!! tip ":lucide-cable: Connect the QT Py device to your workstation with USB"

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

| Name            | Purpose                                                         | Link |
|-----------------|-----------------------------------------------------------------|------|
|                 |                                                                 |      |
| **Host PC**     |                                                                 |      |
| Python          | :fontawesome-solid-worm:{ .qtpy }&nbsp;                Language | [python.org](https://docs.python.org/3.11/index.html) |
|                 | :lucide-book-open-text:&nbsp;                Language reference | [python.org](https://docs.python.org/3.11/reference/index.html) |
|                 | :lucide-library-big:&nbsp;                     Standard library | [python.org](https://docs.python.org/3.11/library/index.html) |
| uv              | :fontawesome-solid-gear:&nbsp;                        Core tool | [astral.sh](https://docs.astral.sh/uv/) |
| poe             | :fontawesome-solid-gear:&nbsp;                        Core tool | [natn.io](https://poethepoet.natn.io/index.html) |
| ruff            | :fontawesome-solid-microscope:&nbsp;              Code analyzer | [astral.sh](https://docs.astral.sh/ruff/) |
| pyright         | :fontawesome-solid-microscope:&nbsp;              Code analyzer | [github.io](https://microsoft.github.io/pyright) |
| pytest          | :fontawesome-solid-flask:&nbsp;                     Test runner | [pytest.org](https://docs.pytest.org/en/stable/) |
| zensical        | :fontawesome-solid-book:&nbsp;                    Documentation | [zensical.org](https://zensical.org/docs/get-started/) |
| click           | :fontawesome-solid-terminal:&nbsp;       Command line interface | [palletsprojects.com](https://click.palletsprojects.com/en/stable/) |
| pySerial        | :fontawesome-solid-square-binary:&nbsp;          Serial port IO | [readthedocs.io](https://pyserial.readthedocs.io/en/stable/pyserial.html) |
| wmi             | :fontawesome-brands-windows:&nbsp;    Windows system inspection | [me.uk](https://timgolden.me.uk/python/wmi/contents.html) |
| psutil          | :fontawesome-solid-toolbox:&nbsp;  System and process utilities | [readthedocs.io](https://psutil.readthedocs.io/en/stable/) |
| gmqtt           | :fontawesome-solid-envelope:&nbsp;                  MQTT client | [github.com](https://github.com/wialon/gmqtt) |
| mosquitto       | :fontawesome-solid-satellite-dish:&nbsp;            MQTT server | [mosquitto.org](https://mosquitto.org/) |
| ttkbootstrap    | :fontawesome-solid-arrow-pointer:&nbsp;           GUI extension | [readthedocs.io](https://ttkbootstrap.readthedocs.io/en/latest/) |
| pandas          | :fontawesome-solid-table:&nbsp;                 Data processing | [pydata.org](https://pandas.pydata.org/docs/) |
| matplotlib      | :fontawesome-solid-chart-line:&nbsp;                   Plotting | [matplotlib.org](https://matplotlib.org/stable/) |
| circup          | :fontawesome-solid-microchip:&nbsp;                  QT Py tool | [readthedocs.io](https://circup.readthedocs.io/en/stable/) |
|                 |                                                                 |      |
| **Sensor node** |                                                                 |      |
| MicroPython     | :fontawesome-solid-microchip:&nbsp;                  Supervisor | [micropython.org](https://docs.micropython.org/en/v1.23.0/genrst/index.html) |
| CircuitPython   | :fontawesome-solid-worm:{ .qtpy }&nbsp;                Language | [adafruit.com](https://learn.adafruit.com/welcome-to-circuitpython/overview) |
|                 | :lucide-library-big:&nbsp;                     Standard library | [circuitpython.org](https://docs.circuitpython.org/en/stable/docs/library/index.html) |
|                 | :lucide-blocks:&nbsp;                              Core modules | [circuitpython.org](https://docs.circuitpython.org/en/stable/shared-bindings/index.html) |
| Drivers         | :fontawesome-solid-stethoscope:&nbsp;            Sensor support | [circuitpython.org](https://docs.circuitpython.org/projects/bundle/en/stable/drivers.html) |
| MiniMQTT        | :fontawesome-solid-envelope:&nbsp;                  MQTT client | [circuitpython.org](https://docs.circuitpython.org/projects/minimqtt/en/stable/index.html) |
| ASCII           | :lucide-binary:&nbsp;               Binary codes for characters | [ss64.com](https://ss64.com/ascii.html) |
| XTerm           | :fontawesome-solid-keyboard:&nbsp; Code sequences for terminals | [invisible-island.net](https://invisible-island.net/xterm/ctlseqs/ctlseqs.html) |

## Pull requests and Issues

See the sections under the [Project Workflows](https://github.com/wireddown/qtpy-datalogger/wiki/Project-Workflows) wiki page for outlines.

## First time setup

If the tools and commands referenced above are not on your system, follow the instructions in these walkthroughs to install and configure them.

1. [Tools](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-1-Tools)
1. [Git](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-2-Git)
1. [Python](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-3-Python)
1. [QT Py](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-4-QT-Py)
1. [MQTT](https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-5-MQTT)
