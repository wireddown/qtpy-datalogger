---
icon: fontawesome/solid/satellite-dish
tags:
  - Develop
  - Introduction
  - MQTT
---

# MQTT broker service

Network communication with QT Py devices requires an MQTT broker service available on the network.
If your facility does not have a service, you can install and host one on your workstation.

## Mosquitto

We recommend the [Mosquitto MQTT server] from the Eclipse Foundation.

1. Download the 64-bit binary exe installer for Windows
1. Run the installer and keep the default options

??? quote "Install with `winget`"
    ```pwsh
    winget install --exact --id=EclipseFoundation.Mosquitto
    ```

## Configure

### MQTT server

1. Confirm that the **MQTT Broker** service starts automatically
    - Open `services.msc` from the Windows run menu
    - Find the entry for `Mosquitto Broker`
    - Confirm the value in the `Startup Type` column shows `Automatic`
1. Update the server configuration to listen for connections on the conventional MQTT port
    - Open the [Mosquitto configuration file] in a text editor
        - `C:\Program Files\mosquitto\mosquitto.conf`
    - Add these lines to the bottom
        ```txt
        listener 1883
        allow_anonymous true
        ```
    - Use `services.msc` to restart the service so that it reloads its settings

    ??? info "Restore after upgrading"

        - When you upgrade the server, the installer **replaces** the configuration file with a **new** copy
        - Update the configuration file like before and **restart** the server

### System firewall

Before QT Py devices can connect to the MQTT server, the Windows firewall must allow external connections.
We optimize the firewall by constraining the new rule to match against the **local subnet** for the server's **_exact_ program** and **configured port**.

Run this command in an **Administrator** terminal to configure the firewall for the Mosquitto program
   ```pwsh
   netsh advfirewall firewall add rule name='Mosquitto MQTT: allow inbound on port 1883 from local subnet' program='C:\Program Files\mosquitto\mosquitto.exe' dir=in action=allow service=any description='This rule allows MQTT clients on the local subnet to connect to this host' profile=private localip=any remoteip=localsubnet localport=1883 remoteport=any protocol=tcp interfacetype=any
   ```

??? note "Option-by-option explanation for [**netsh advfirewall**]"
    ```pwsh
    # Add a new firewall rule
    netsh advfirewall firewall add rule

        # Free-text name
        name='Mosquitto MQTT: allow inbound on port 1883 from local subnet'

        # Which program to guard
        program='C:\Program Files\mosquitto\mosquitto.exe'

        # Which direction connections happen
        dir=in

        # Which action to take when a connection is requested
        action=allow

        # Which service instance to allow
        service=any

        # Free-text description
        description='This rule allows MQTT clients on the local subnet to connect to this host'

        # Which security zone
        profile=private

        # Which local addresses to match
        localip=any

        # Which external addresses to match
        remoteip=localsubnet

        # Which local port to use
        localport=1883

        # Which external port to use
        remoteport=any

        # Which network protocol to use
        protocol=tcp

        # Which network interface to use
        interfacetype=any
    ```

## Ready check

### Server

Use the command **`qtpy-datalogger server`** to confirm the readiness of the MQTT service.

???+ success "Running and ready"
    **`> qtpy-datalogger server`**
    ```
    INFO     Eclipse Mosquitto MQTT v5/v3.1.1 broker
    INFO            State  Running
    INFO           Status  OK
    INFO          Startup  Auto
    INFO       Executable  C:\Program Files\mosquitto\mosquitto.exe
    INFO           Server  Listening on port 1883
    INFO         Firewall  Open on port 1883
    ```

??? danger "Installed, but not configured"
    **`> qtpy-datalogger server`**
    ```
    INFO     Eclipse Mosquitto MQTT v5/v3.1.1 broker
    INFO            State  Running
    INFO           Status  OK
    INFO          Startup  Auto
    INFO       Executable  C:\Program Files\mosquitto\mosquitto.exe
    WARNING        Server  Unconfigured
    WARNING      Firewall  Unconfigured
    ```

### Client

Use the command **`qtpy-datalogger server --observe`** to confirm the MQTT service accepts client connections.

```pwsh
# Confirm whether the MQTT service accepts client connections
qtpy-datalogger server --observe
```

After successfully connecting, the command remains running as an observer and prints new MQTT messages as they arrive.
Use ++ctrl+c++ to disconnect and exit.

If there is a problem connecting, the command exits with a description of what it can detect.

## QT Py Control

In order to communicate on the WiFi network, the QT Py must have:

- the sensor node runtime installed
- the MQTT broker, WiFi, and node details

### Equip

!!! tip ":lucide-cable:{ .lg .middle }&nbsp; Connect the QT Py device to your workstation with USB"

1. Create a file named `settings.toml` in the **root folder** of the QT Py
    ```toml
    CIRCUITPY_WIFI_SSID="__YOUR_WIFI_NETWORK_NAME__"
    CIRCUITPY_WIFI_PASSWORD="__YOUR_WIFI_NETWORK_PASSWORD__"
    QTPY_BROKER_IP_ADDRESS="__YOUR_MQTT_BROKER_IP_ADDRESS__"
    QTPY_NODE_GROUP="zone1"
    ```
    - Set the WiFi SSID and password
    - Set the broker IP address
    ??? info "When using Mosquitto, the broker's IP address is the IP address of your workstation"
        ```pwsh
        # All active IPv4 addresses
        Get-NetIPAddress -AddressFamily IPv4 |
            Where-Object {$_.AddressState -eq "Preferred" -and $_.InterfaceAlias -notlike "Loopback"} |
            Select-Object InterfaceAlias, IPAddress
        ```
1. Install and confirm the sensor node runtime
    ```pwsh
    # Install the sensor node runtime and confirm settings.toml
    qtpy-datalogger equip --secrets
    ```

### Connect

Use the [**Scanner app**](../../gallery/#scanner) to confirm communication.

```pwsh
# Run the Scanner app
qtpy-datalogger run scanner
```


[Mosquitto MQTT server]: https://mosquitto.org/download/
[Mosquitto configuration file]: https://mosquitto.org/man/mosquitto-conf-5.html

[**netsh advfirewall**]: https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-server-2008-R2-and-2008/dd734783(v=ws.10)
