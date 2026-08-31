---
icon: lucide/file-braces-corner
tags:
  - Develop
  - How-to
  - Code
  - Test
  - Debug
---

# How to work with the code

This page covers topics that help you explore and modify the code.
Continue reading if you want to customize the code or contribute to the project but you're new to programming.

## Debug code

The two most effective ways to understand and examine a program's behavior are

- Pausing the program and inspecting or changing live data
- Tracing the program's execution and tracking its function calls

### Pause and inspect

In VS Code, [debug settings] are configured in the `.vscode/launch.json` file.
Each new entry in this file adds an entry to the [Run and Debug] dropdown combobox.
In addition to the default entries, this project has one defined that launches `qtpy_datalogger` as a command line program.

1. To start debugging the **code**
    - Modify or add a new launch configuration
    - [Set breakpoints] where you want the debugger to pause the program
    - Select the launch configuration from the dropdown combobox
    - Press `F5` to launch into the debugger
1. To start debugging a **test**
    - Switch to the [Test Explorer view]
    - Set a breakpoint in the test code
    - Click the **Debug** button
1. Once the debugger reaches the breakpoint
    - [Use the debug actions] to execute the code line-by-line
    - Use the **Debug and Run** view to [inspect variables]
1. To experiment with live data while the program is paused
    - [Use the debug console] to create new variables and evaluate expressions

### Run and trace

Rather than running the program in the debugger, you can also run the program normally and enable `--verbose` messages.
With `--verbose` enabled, the logging subsystem prints both timing information and the `logger.debug()` messages in the code.

This approach is useful when you want to see which functions the code uses and which ones are slow.
Add more `logger.debug()` messages to show variable information or which code branches the program takes.

```pwsh title="PowerShell"
# Enable debug messages and timing information
qtpy-datalogger --verbose ...
```

### Debugging handbook

The [Python debugging handbook] covers both of these approaches in more detail.
It also explains common errors and their causes as well as how testing and linting help prevent surprising behavior from code that looks harmless.

## Write tests

When we add new features and fix bugs for the project, we also add new tests that exercise and validate them.
To learn more about the project's approach to testing, visit our [Python testing](../intro/python.md#testing-code) page.

Even if you're customizing the code for your own use cases, consider adding tests that validate your modifications.
The tests for your custom code can help you detect incompatibilities when you evaluate new releases of `qtpy-datalogger`.

### Add a test

This project uses `pytest` to discover, run, and report tests.
`pytest` discovers tests using file names and function names.
Any function in a file where **both** names start with `test_` is categorized as a test.

1. Create the test file and test function
    - Create a new file with a name that starts with `test_` in the **`tests`** folder
    - Define a new function with a name that starts with `test_` in the test file
    - Example: [tests\test_console.py]
    ```python title="tests\test_console.py"
    def test_generate_notice_option():
        ...
    ```
1. Write the test function using the ["Arrange, Act, Assert, Cleanup"] pattern
    - Arrange the inputs and program state such that the test case is testable
    - Call the code that needs to be tested
    - [Check the results] against the expected outcome with an `assert` statement
    - Undo any preparation from the first step

### Control the environment

The **Arrange** or **Act** steps of a test usually require controlled and repeatable input values or system state.
`pytest` offers a few ways to configure the environment for test cases.

- **[pytest parameters]**
    - Use **parameters** when you want to validate different combinations of inputs and expected values in the same test
    - Example: `test_verbosity_truth_table(...)` uses **parameters** in [tests\test_console.py] to validate every combination of the `--quiet` and `--verbose` CLI options
- **[pytest fixtures]**
    - Use a **fixture** when you want to define and reuse data or other context in the environment
    - Example: `capsys` is a **fixture** in `test_run_as_module(capsys)` in [tests\test_main.py] that records the output and error streams so that the test can inspect the program's messages
- **[pytest monkeypatches]**
    - Use a **monkeypatch** when you want to override _real_ code with code under _your_ control
    - Example: `test_windows_discovery()` replaces real functions with **mimics** in [tests\test_discovery.py] to return hardcoded results from unpredictable system resources

### Testing handbook

For more details and examples, see the `pytest` [How-to guides] and the [intro-to-pytest] GitHub tutorial series.

## Update dependencies

This project uses our [Dependabot Updates action](manage.md#dependabot-updates) to regularly update dependencies on a schedule.

To add or update dependencies on-demand, [use **uv add**].

```pwsh title="PowerShell"
# Add dependencies by name to use the latest version
uv add gmqtt

# Update dependencies by using the new desired version as the constraint
uv add "gmqtt>=0.7.0"
```

## Search code history

In VS Code, use these commands to trace file and line history.
Open the command input with ++control+shift+p++ and begin typing the command name you want to run.

- **Git: View History** -- show every commit for the entire repository
- **Git: View File History** -- show the commits that changed the selected file
- **Git: View Line History** -- show the commits that changed the selected line
- **GitLens: Show Commit Graph** -- show an illustration of the branches and their history

On the command line, [use **git log**] to search and show history.

```pwsh title="PowerShell"
# Show the five most recent commit messages
git log --oneline --max-count 5

# Search the commit messages for a string
git log --grep "search string"

# Show the line changes for the most recent commit
git log --patch --max-count 1

# Search the line changes for a string
git log -G "search string"
```


[debug settings]: https://code.visualstudio.com/docs/python/debugging#_set-configuration-options
[Run and Debug]: https://code.visualstudio.com/docs/debugtest/debugging-configuration#_start-a-debugging-session-with-a-launch-configuration
[Set breakpoints]: https://code.visualstudio.com/docs/debugtest/debugging#_breakpoints
[Test Explorer view]: https://code.visualstudio.com/docs/debugtest/testing#_automatic-test-discovery-in-testing-view
[Use the debug actions]: https://code.visualstudio.com/docs/debugtest/debugging#_debug-actions
[inspect variables]: https://code.visualstudio.com/docs/debugtest/debugging#_data-inspection
[Use the debug console]: https://code.visualstudio.com/docs/debugtest/debugging#_debug-console-repl
[Python debugging handbook]: https://www.freecodecamp.org/news/python-debugging-handbook/

[tests\test_console.py]: https://github.com/wireddown/qtpy-datalogger/blob/main/tests/test_console.py
["Arrange, Act, Assert, Cleanup"]: https://docs.pytest.org/en/stable/explanation/anatomy.html
[Check the results]: https://docs.pytest.org/en/stable/how-to/assert.html
[pytest fixtures]: https://docs.pytest.org/en/stable/how-to/fixtures.html
[tests\test_main.py]: https://github.com/wireddown/qtpy-datalogger/blob/main/tests/test_main.py
[pytest parameters]: https://docs.pytest.org/en/stable/how-to/parametrize.html
[pytest monkeypatches]: https://docs.pytest.org/en/stable/how-to/monkeypatch.html
[tests\test_discovery.py]: https://github.com/wireddown/qtpy-datalogger/blob/main/tests/test_discovery.py
[How-to guides]: https://docs.pytest.org/en/stable/how-to/index.html
[intro-to-pytest]: https://github.com/pluralsight/intro-to-pytest/blob/master/README.md

[use **uv add**]: https://docs.astral.sh/uv/concepts/projects/dependencies/#adding-dependencies

[use **git log**]: https://git-scm.com/docs/git-log
