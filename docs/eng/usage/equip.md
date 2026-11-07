---
icon: lucide/file-down
tags:
  - User guide
  - CLI
  - equip
  - upgrade
  - repair
  - secrets
  - troubleshoot
---

# `qtpy-datalogger equip`

Use the **`equip`** command to install the QT Py Datalogger runtime and custom runtime apps onto a CircuitPython device.

In addition to the runtime's Python source files, this command detects and installs the required CircuitPython modules for custom apps.

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; The **`equip`** command needs a USB connection"

## Capabilities

- Detect, upgrade, and repair
    - runtime versions
    - custom apps
    - CircuitPython modules
- Set deployment secrets like
    - WiFi credentials
    - MQTT broker
- Compare a device's runtime version with this package
- Force the installation of the runtime version

## Examples

### Install

Use the **`equip`** command to install, upgrade, or repair the QT Py Datalogger runtime on a CircuitPython device.

```pwsh title="PowerShell"
qtpy-datalogger equip
```

The command detects the device's hardware and CircuitPython version, and then installs the runtime and its supporting CircuitPython libraries.

### Install custom app

Use the **`--with-app FILE`** option to install a custom app on the device.

```pwsh title="PowerShell"
qtpy-datalogger equip --with-app custom_ble_app.py
```

- The command detects the app's imported modules and installs the supporting libraries
- If you want to install multiple apps together, repeat the option with each app

### Control secrets

Use the **`--secrets`** option to control [deployment **secrets**] on the device.

To check whether secrets have been set, use the option as a flag.

```pwsh title="PowerShell"
# Show missing secrets
qtpy-datalogger equip --secrets
```

- If a secret has been set, the output does **not** reveal the secret's value
- Instead, it prints **`ok`** when a secret has a value and prints **`MISSING`** otherwise

To set secrets on the device, you can either specify a file to copy or type them by hand.

```pwsh title="PowerShell"
# Copy a toml file to set device secrets
qtpy-datalogger equip --secrets path\to\file.toml

# Set the device secrets one by one interactively
qtpy-datalogger equip --secrets -
```

QT Py Datalogger stores the secrets on the device following the recommendation from CircuitPython to [separate passwords from source code] using a file named **settings.toml**.

### Troubleshoot

Use the **`--verbose`** option with **`--compare`** to show messages about detected files and modules on the device.

```pwsh title="PowerShell"
qtpy-datalogger --verbose equip --compare
```

Inspect the output for warnings or errors and address them.

If there are no obvious problems, try re-installing the runtime with the **`--force`** option.

```pwsh title="PowerShell"
qtpy-datalogger --verbose equip --force
```

If something still isn't working correctly, the [Troubleshoot] page has more checks to run.
Please create a [bug report] with any information you collect.

## CLI help

```pwsh title="PowerShell"
qtpy-datalogger equip --help
```

```txt
Usage: qtpy-datalogger equip [OPTIONS]

  Install the sensor_node runtime on a CircuitPython device.

Options:
  --upgrade             Behavior: [default] Install the sensor_node runtime
                        from this package onto a new device or upgrade an
                        existing version.
  --compare             Behavior: Show the version and date information
                        between this package and the sensor_node runtime on
                        the device and exit.
  --describe            Behavior: Show the contents and dependencies of the
                        sensor_node runtime in this package.
  --force               Behavior: Force the installation of the sensor_node
                        runtime on the device.
  --with-app FILE       Install the sensor_node app FILE, including its
                        CircuitPython dependencies, to the device. Accepted
                        multiple times.
  -r, --root FOLDER     Use FOLDER as the root.
  --secrets [FILE | -]  Update the secrets on the sensor_node from FILE or
                        stdin with '-'. Without FILE, show which are missing.
  --help                Show this message and exit.

  More: https://downtothewire.io/qtpy-datalogger/eng/usage/equip/
```


[deployment **secrets**]: ../intro/mqtt.md#4-qt-py-control
[separate passwords from source code]: https://docs.circuitpython.org/en/latest/docs/environment.html
[Troubleshoot]: ../../troubleshoot.md
[bug report]: https://github.com/wireddown/qtpy-datalogger/issues/new?template=bug-report.md
