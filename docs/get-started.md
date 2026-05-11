---
icon: lucide/cable
tags:
  - Setup
  - Get started
---

# Get started

## Preview in 90 seconds

1. Connect your QT Py device with USB
    - _(Optional)_ Back up its `code.py` file
1. Preview the program in a deletable Python virtual environment

    ```pwsh
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

    # Install the node runtime on a device
    qtpy-datalogger equip

    # Open a serial connection, use Ctrl-] to quit
    qtpy-datalogger connect

    qtpycmd get_apps

    qtpycmd stats

    qtpycmd read A0 A1 A2 A3

    # Ctrl-] to quit
    ```

This preview does not demonstrate MQTT communication over WiFi

- Visit the wiki for [MQTT setup and commissioning] for more details

[MQTT setup and commissioning]: https://github.com/wireddown/qtpy-datalogger/wiki/Walkthrough-5-MQTT
