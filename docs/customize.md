---
icon: lucide/drill
tags:
  - Setup
  - Customize
---

# Customize

Once you've [gotten started](get-started.md), use these simple demos as branching points to extend the system to your use case.

## Analog Plotter

A custom host-side app that plots analog data using the built-in sensor node app `qtpycmd`.

- :lucide-audio-waveform:{ .lg .middle .qtpy }&nbsp; **Analog input**
- :lucide-wifi:{ .lg .middle .qtpy }&nbsp; **Network / MQTT**
- :lucide-cable:{ .lg .middle .qtpy }&nbsp; **Serial / UART**

![Screenshot of Analog Plotter demo app](gallery/ex-analog-plotter.png)

1. **Copy** the app's source file `analog_plotter.py` to your `qtpy-preview` folder
    - [View] it in your browser
    - [Save-As] to download it directly
1. **Run** it with
    ```pwsh title="PowerShell"
    python analog_plotter.py
    ```
1. **Edit** the [variables at the top] of `get_and_plot_data()` to exercise the features
    - Note that this example only enables UART communication to start
    - If you setup [MQTT](eng/intro/mqtt.md) to use WiFi, change **`use_mqtt`** to **`True`**
    ```python title="get_and_plot_data()"
      # Customize
      use_uart = True
      use_mqtt = False
      minimum_mqtt_node_count = 1
      channel_cmd_string = "A0 A3"
      mqtt_group = datatypes.Default.MqttGroup
      max_adc_voltage = 3.3
      max_adc_code = 2**16
    ```

## Full-stack app

!!! example "Still cooking..."

## Ready for more?

See [Develop](develop.md) and choose:

- Add `qtpy-datalogger` to your project
- Or fork-and-branch

Go get logging!


[View]: https://github.com/wireddown/qtpy-datalogger/blob/main/examples/analog_plotter/analog_plotter.py
[Save-as]: https://raw.githubusercontent.com/wireddown/qtpy-datalogger/refs/heads/main/examples/analog_plotter/analog_plotter.py
[variables at the top]: https://github.com/wireddown/qtpy-datalogger/blob/main/examples/analog_plotter/analog_plotter.py#L154
