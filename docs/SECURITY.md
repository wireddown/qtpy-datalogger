---
icon: fontawesome/solid/shield-halved
tags:
  - Governance
  - Security
---

# Security

## No guarantees

This software disclaims any guarantees against security vulnerabilities.

### Known system impacts

This table lists the system impacts when using `qtpy-datalogger`.

| Component           | Note |
|---------------------|------|
| qtpy-datalogger     | Installation uses Python    |
| qtpy-datalogger     | Installation uses pypi.org  |
| qtpy-datalogger     | Cloning uses github.com     |
| QT Py device        | Connects to USB             |
| QT Py device        | Connects to WiFi            |
| MQTT broker service | Uses port `1883` on local subnet |
| MQTT broker service | Allows anonymous clients    |

## Reporting vulnerabilities

If you encounter a vulnerability or have questions, create a [new GitHub Issue].

[new GitHub issue]: https://github.com/wireddown/qtpy-datalogger/issues/new/choose
