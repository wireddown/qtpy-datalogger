---
icon: lucide/cloud
tags:
  - User guide
  - CLI
  - server
---

# `qtpy-datalogger server`

## CLI help

```
qtpy-datalogger server --help
```

```txt
Usage: qtpy-datalogger server [OPTIONS]

  Query and control the MQTT server.

Options:
  --describe               Behavior: [default] Show the current status of the
                           service.
  --observe                Behavior: Monitor the service and print published
                           messages, Ctrl-C to quit.
  --restart                Behavior: Restart the service, requires
                           Administrator privileges.
  --publish TOPIC MESSAGE  Send a MESSAGE to the service on the specified
                           TOPIC.
  --help                   Show this message and exit.

  Detailed help online

  https://wireddown.github.io/qtpy-datalogger/eng/intro/mqtt/
```
