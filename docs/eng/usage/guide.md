---
icon: lucide/book-open
tags:
  - User guide
---

# User guide

## Use in your project

If you want to add this package to your own project and use it in your code, add `qtpy-datalogger` using your project's dependency manager.

=== "uv"

    ```pwsh title="Powershell"
    uv add qtpy-datalogger
    ```

=== "pdm"

    ```pwsh title="Powershell"
    pdm add qtpy-datalogger
    ```

=== "poetry"

    ```poetry title="Powershell"
    poetry add qtpy-datalogger
    ```

Then import the package like any other in your source code.

```py title="my_program.py"
from qtpy_datalogger import discovery, snsrkit
```
