---
icon: lucide/arrow-right-left
tags:
  - User guide
  - CLI
  - connect
---

# `qtpy-datalogger connect`

## CLI help

```
qtpy-datalogger connect --help
```

```txt
Usage: qtpy-datalogger connect [OPTIONS]

  Connect to a serial port, preferring a CircuitPython device, or to an MQTT
  sensor_node on the network.

Options:
  --auto-connect        Behavior: [default] Find and open a session with a QT
                        Py device.
  --discover-only       Behavior: List discovered devices and exit.
  -g, --group GROUP-ID  MQTT group to use. Default: zone1
  -n, --node NODE-ID    MQTT node to use for connection.
  -p, --port COM#       Serial COM port to use for connection.
  --help                Show this message and exit.

  Help and home page: https://downtothewire.io/qtpy-datalogger/
```
