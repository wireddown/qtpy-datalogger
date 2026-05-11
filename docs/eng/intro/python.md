---
icon: fontawesome/brands/python
tags:
  - Develop
  - Introduction
  - Python
---

# Python

## Install

### Outline

!!! success "Order is important because each step relies on a previous one"

1. **Disable** the Python aliases included with Windows because they interfere with these tools
1. Install the tool **`uv`**. We selected it because it efficiently
    - installs and switches between any version of Python
    - manages dependencies for Python projects
    - installs Python tools as commands
1. Install **Python**

Further reading on this Python tooling, its uses, and how it works:

- [**uv**: A Complete Guide]
    - Explains the efficiencies and convenient workflows in `uv`
- [Python Virtual Environments: A Primer]
    - Explains what Python virtual environments are, why they are useful, and how they work


!!! info "Why we use `uv run ...`"
    - `uv` manages the virtual environment and its commands for the project **automatically**
    - `uv run ...` activates the environment for the command that follows
    - `uv` invokes these managed commands and won't use a system-wide tool of the same name by accident

### Disable Python aliases

1. Open the **Windows Settings** app and navigate to:

    - **:fontawesome-solid-gear:&nbsp; Settings :lucide-arrow-right: Apps :lucide-arrow-right: Advanced app settings :lucide-arrow-right: App execution aliases**

1. Scroll down the list and **disable** these two entries:

    | Name              | Detail        |
    |-------------------|---------------|
    | **App Installer** | `python.exe`  |
    | **App Installer** | `python3.exe` |

### Install uv

Open PowerShell in Windows Terminal and [install **uv**] with `winget`.

```pwsh
# Install with winget
winget install --exact --id=astral-sh.uv

# Confirm that uv has been installed
uv self version
```

### Install Python

Open PowerShell and [use **uv**] to install Python.

```pwsh
# Show the available versions of Python
uv python list

# Install the latest release of a Python version
uv python install 3.11

# Set the default version of Python
uv pin --global 3.11

# Get the active version of Python
uv python find --show-version

# Show all installed and selectable versions
uv python list --only-installed
```

## Testing code

This project focuses on writing and running tests that exercise either entire features or single functions.
As bugs are fixed, we add tests that confirm the bug remains fixed.

### Acceptance testing

Acceptance tests validate a use-case or workflow for a feature.
They determine whether a user would find the behavior of the code _acceptable_.

### Unit testing

Unit tests validate the outcome from running a function.
They determine whether the code returns the correct output for the specified input.
Input values in tests may be purposefully incorrect or inapplicable to validate that the code correctly handles error cases.

### pytest

We use the [tool **pytest**] to run all of the project's tests.

```pwsh
# Run the tests
uv run pytest

# Print more information about failures
uv run pytest --verbose
```

The Python extension in VS Code automatically [discovers the tests] for this project and lists them in the testing side panel.
In this view, you can also run tests and debug them.

## Analyzing code

This project focuses on writing readable and unsurprising code.
We run format, structure, and type analysis tools to identify code that doesn't match Python convention.

### ruff

We use the [tool **ruff**] to check and fix [format] and [structure] problems.

**Analyze**

```pwsh
# Find differences from Python convention
uv run ruff check

# Find white space and line length problems
uv run ruff format --diff

# Show an explanation and examples for a violation
uv run ruff rule Z123

# Pipe to the tool 'mdv' to format the explanation
# - Install it with 'uv tool install mdv'
uv run ruff rule Z123 | mdv -
```

**Fix**

```pwsh
# Fix differences from Python convention
uv run ruff check --fix

# Apply formatting rules
uv run ruff format
```

The Python extension in VS Code can identify these problems and often has suggested fixes.

### pyright

We use the [tool **pyright**] to check that functions accept and return [compatible types and variables].

**Analyze**

```pwsh
# Find incompatible or incorrect uses of variables and classes
uv run pyright
```

**Fix**

Fixes are made by hand because `pyright` does not have a fix option.
However, the Python extension in VS Code can identify these problems and often has suggested fixes.

## Poe runner

The [tool **poe**] makes running the tests and analyzers easier because we use [sequence tasks] that call `pytest`, `ruff`, and `pyright` with their parameters.


```pwsh
# Runs 'pytest'
uv run poe test

# Runs 'ruff check'  then  'ruff format --diff'  then  'pyright --dependencies'
uv run poe lint

# Runs 'ruff check --fix'  then  'ruff format'
uv run poe fix
```

[**uv**: A Complete Guide]: https://pydevtools.com/handbook/explanation/uv-complete-guide/
[Python Virtual Environments: A Primer]: https://realpython.com/python-virtual-environments-a-primer/

[install **uv**]: https://docs.astral.sh/uv/getting-started/installation/#winget
[use **uv**]: https://docs.astral.sh/uv/guides/install-python/#installing-a-specific-version

[tool **pytest**]: https://docs.pytest.org/en/stable/
[discovers the tests]: https://code.visualstudio.com/docs/python/testing#_test-discovery
[tool **ruff**]: https://docs.astral.sh/ruff/
[structure]: https://docs.astral.sh/ruff/linter/
[format]: https://docs.astral.sh/ruff/formatter/
[tool **pyright**]: https://microsoft.github.io/pyright/#/type-concepts
[compatible types and variables]: https://microsoft.github.io/pyright/#/features

[tool **poe**]: https://poethepoet.natn.io/index.html
[sequence tasks]: https://poethepoet.natn.io/tasks/task_types/sequence.html
