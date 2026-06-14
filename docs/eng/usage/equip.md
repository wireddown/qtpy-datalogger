---
icon: lucide/file-down
tags:
  - User guide
  - CLI
  - equip
---

# `qtpy-datalogger equip`

## CLI help

```
qtpy-datalogger equip --help
```

```txt
Usage: qtpy-datalogger equip [OPTIONS]

  Install the QT Py Sensor Node runtime on a CircuitPython device.

Options:
  --upgrade             Behavior: [default] Install the sensor_node bundle
                        from this package onto a new device or upgrade an
                        existing version.
  --compare             Behavior: Show the version and date information
                        between this package and the sensor_node bundle on the
                        device and exit.
  --describe            Behavior: Show the contents and dependencies of the
                        sensor_node bundle in this package.
  --force               Behavior: Force the installation of the sensor_node
                        bundle on the device.
  --newer-files-only    Behavior: Only update sensor_node bundle files that
                        are newer, skip installing CircuitPython support
                        libraries.
  -r, --root FOLDER     Use FOLDER as the root.
  --secrets [FILE | -]  Update the secrets on the sensor_node from FILE or
                        stdin with '-'. Without FILE, show which are missing.
  --help                Show this message and exit.

  Help and home page: https://downtothewire.io/qtpy-datalogger/
```
