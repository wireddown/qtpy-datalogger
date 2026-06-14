---
icon: lucide/terminal
tags:
  - User guide
  - CLI
---

# `qtpy-datalogger`

## CLI help

```
qtpy-datalogger --help
```

```txt
Usage: qtpy-datalogger [OPTIONS] COMMAND [ARGS]...

  QT Py datalogger control program.

Options:
  --generate-notice PATH          Generate notice.toml file at PATH.
  --list-builtin-modules BOARD_ID PATH
                                  Generate modules.toml file at PATH, where
                                  BOARD_ID is a board name from https://docs.c
                                  ircuitpython.org/en/stable/shared-
                                  bindings/support_matrix.html
  --help                          Show this message and exit.
  -q, --quiet                     Show only error messages.
  -v, --verbose                   Enable verbose messages.
  --version                       Show the version and exit.

Commands:
  connect  Connect to a serial port or MQTT sensor_node.
  equip    Install the QT Py Sensor Node runtime on a CircuitPython device.
  run      Run the APP_NAME app for QT Py datalogger.
  server   Query and control the MQTT server.

  Help and home page: https://downtothewire.io/qtpy-datalogger/
```
