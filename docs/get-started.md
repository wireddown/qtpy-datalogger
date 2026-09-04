---
icon: lucide/cable
tags:
  - Setup
  - Get started
---

# Get started in 5 minutes

## :lucide-audio-waveform: Analog data in 90 seconds

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py to your workstation with USB"

- Back up the `code.py` file on the QT Py
- Preview the package in a deletable Python virtual environment

    ```pwsh title="PowerShell"
    # Create and enter a new Python virtual environment
    mkdir qtpy-preview
    cd qtpy-preview
    python -m venv --upgrade-deps .venv
    .\.venv\Scripts\activate.ps1

    # Install
    pip install qtpy-datalogger

    # Show the package help
    qtpy-datalogger --help

    # Search for devices
    qtpy-datalogger connect --discover-only

    # Install the sensor node runtime on the QT Py
    qtpy-datalogger equip

    # Open a serial connection, use Ctrl-] to quit
    qtpy-datalogger connect

    qtpycmd get_apps

    qtpycmd stats

    qtpycmd read A0 A1 A2 A3

    # Ctrl-] to quit
    ```

- Plot data in the [**Analog Plotter**](customize.md#analog-plotter) demo GUI app
    ![Screenshot of Analog Plotter demo app](gallery/ex-analog-plotter.png)
- Optionally, delete the folder `qtpy-preview` when you are done

## :lucide-wifi: WiFi control in 3 minutes

!!! info "This preview does not demonstrate communication over WiFi"

In order to communicate on the WiFi network, the QT Py sensor node must also have

- an MQTT broker
- WiFi credentials

Continue to the [MQTT](eng/intro/mqtt.md) page if you want to try [the demo apps](customize.md) over the network.
