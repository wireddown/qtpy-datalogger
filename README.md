# QT Py S3 DAQ App

**`qtpy-datalogger`** -- A data acquisition application using the [Adafruit QT Py S3] and [CircuitPython].

## Status

[![CI: Tests and Analyzers](https://github.com/wireddown/qt-py-s3-daq-app/actions/workflows/ci.yml/badge.svg)](https://github.com/wireddown/qt-py-s3-daq-app/actions/workflows/ci.yml)
[![Dependabot Updates]](https://github.com/wireddown/qt-py-s3-daq-app/actions/workflows/dependabot/dependabot-updates)
[![Publish: Release on PyPI](https://github.com/wireddown/qt-py-s3-daq-app/actions/workflows/publish.yml/badge.svg)](https://github.com/wireddown/qt-py-s3-daq-app/actions/workflows/publish.yml)

## Structure

```mermaid
graph LR
    AP(🛜 Access Point)
    App(🐍 App)
    MQTT(📨 MQTT)
    QTPy(🐍 QT Py S3)

    subgraph "🌐 Network"
        AP
    end

    subgraph "💻 PC Host"
        App<-.->MQTT
        MQTT<-.->AP
    end

    subgraph "🧪 Test Zone"
        AP<-.->|🛜 WiFi|QTPy
    end
```

**Supported Python versions**
- Host
  - Python 3.11
  - Python 3.12
  - Python 3.13
- Node
  - CircuitPython 9.0

**Supported host platforms**
- Windows

**Supported connection types**
- Serial / UART
- Network / MQTT

**Entry points**
- Host program: [`qtpy_datalogger/console.py`](https://github.com/wireddown/qt-py-s3-daq-app/blob/main/src/qtpy_datalogger/console.py)
- QT Py program: [`qtpy_datalogger/sensor_node/code.py`](https://github.com/wireddown/qt-py-s3-daq-app/blob/main/src/qtpy_datalogger/sensor_node/code.py)

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
```

This preview does not demonstrate MQTT communication over WiFi
- Visit the wiki for [MQTT setup and commissioning] for more details

## Questions and help

Please go to the [wiki home page] for guidance.

## Contributing

This project manages its Python programs with `poetry`.

The environment setup instructions are in the wiki on the [Contributing] page.

The design documentation is in the wiki under the [Design Doc] pages.

## Legacy system

This project replaces a legacy system that uses Python and JeeNodes.

See the [summary and source code] in the `docs/legacy` folder for details.


[Dependabot Updates]: https://github.com/wireddown/qt-py-s3-daq-app/actions/workflows/dependabot/dependabot-updates/badge.svg

[Adafruit QT Py S3]: https://learn.adafruit.com/adafruit-qt-py-esp32-s3
[CircuitPython]: https://circuitpython.org/

[MQTT setup and commissioning]: https://github.com/wireddown/qt-py-s3-daq-app/wiki/Walkthrough-5-MQTT

[wiki home page]: https://github.com/wireddown/qt-py-s3-daq-app/wiki
[Contributing]: https://github.com/wireddown/qt-py-s3-daq-app/wiki/Contributing
[Design Doc]: https://github.com/wireddown/qt-py-s3-daq-app/wiki/Design-Doc-1-Overview
[summary and source code]: https://github.com/wireddown/qt-py-s3-daq-app/blob/main/docs/legacy/README.md
