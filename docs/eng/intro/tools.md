---
icon: lucide/anvil
tags:
  - Develop
  - Introduction
  - Tools
---

# Core tools

If you haven't worked with code from GitHub, you might need to install some core tools on your workstation.

In addition to the **Git** source code management program, you need a **text editor** and a **command terminal**.
You are welcome to use your preferred programs to develop in the way you like.
These are our recommendations for new contributors.

- VS Code
- Windows Terminal
- PowerShell
- ScreenToGif

## Visual Studio Code

Install the [Visual Studio Code] text editor and review the [getting started tutorial]. There are also guides for [using git] and for [developing Python].

We recommend this because it is an excellent and mature general purpose programming application with syntax highlighting, debugging, and extensions.

??? quote "Install with `winget`"
    ```pwsh title="PowerShell"
    winget install --exact --id=Microsoft.VisualStudioCode
    winget install --exact --id=Microsoft.VisualStudioCode.CLI
    ```

### Recommended extensions

This table lists useful [VS Code extensions] for this project.

| Link                                  | Reason |
|---------------------------------------|--------|
| [donjayamanne.**git-extension-pack**] | :lucide-file-clock:{ .lg }&nbsp; View and search file history <br /> :lucide-folder-git-2:{ .lg }&nbsp; Adds project manager to left-side activity bar |
| [ms-python.**python**]                | :lucide-signpost:{ .lg }&nbsp; Adds navigation and API suggestions <br /> :lucide-bug-play:{ .lg .middle }&nbsp; Adds Python debugging and refactoring |
| [bierner.**github-markdown-preview**] | :lucide-text-initial:{ .lg .middle }&nbsp; Apply GitHub's style to your markdown files |
| [charliermarsh.**ruff**]              | :lucide-brush-cleaning:{ .lg }&nbsp; Lint and format Python code on file-save |
| [astral-sh.**ty**]                    | :lucide-search-code:{ .lg }&nbsp; Find and explain Python type mismatches |
| [tamasfe.**even-better-toml**]        | :lucide-list-check:{ .lg .middle }&nbsp; Syntax highlighting and validation for `toml` files |
| [ms-toolsai.**jupyter**]              | :lucide-chart-spline:{ .lg }&nbsp; Use your own venv as a Jupyter kernel |

### Recommended settings

Use the menu entry under **File :lucide-arrow-right: Preferences :lucide-arrow-right: Settings** or press ++ctrl+++**`,`** to open the settings dialog.
Filter for these settings to see and change them.

- Enable `editor.smoothScrolling`
- Enable `diffEditor.experimental.showMoves`
- Enable `diffEditor.experimental.useTrueInlineView`
- Enable `files.insertFinalNewline`
- Enable `files.trimFinalNewlines`
- Enable `files.trimTrailingWhitespace`
- Enable `workbench.list.smoothScrolling`
- Enable `terminal.integrated.copyOnSelection`
- Enable `terminal.integrated.smoothScrolling`
- Enable `terminal.integrated.stickyScroll.enabled`

## Windows Terminal

Install the [Windows Terminal] application and configure it for your preferences.

We recommend this because it hosts shells in tabs like a web browser and supports typical copy-paste actions.

??? quote "Install with `winget`"
    ```pwsh title="PowerShell"
    winget install --exact --id=Microsoft.WindowsTerminal
    ```

### Recommended settings

- Automatically [copy selection to clipboard]
- [CaskaydiaCove Nerd Font] font face

To use this font in VS Code:

- Set `terminal.integrated.fontFamily`
- to `CaskaydiaCove Nerd Font Mono`

## PowerShell

Optionally, install [PowerShell]. This new version is named `pwsh` and installs side-by-side with the system's `powershell` console.

We recommend this because it's the newest and fastest shell for Windows.

??? quote "Install with `winget`"
    ```pwsh title="PowerShell"
    winget install --exact --id=Microsoft.PowerShell
    ```

### Recommended modules

After installing these, apply their usage instructions to the file returned by `$profile`.

- [Oh My Posh]
- [Terminal Icons]

To use these modules in VS Code:

- Set `terminal.integrated.defaultProfile.windows`
- to `PowerShell`
- Apply the same changes to the VS Code profile returned by `$profile`

## ScreenToGif

Optionally, install the [ScreenToGif] application. This tool records both the screen and mouse clicks.

We recommend this because its recordings help demonstrate program behavior.

??? quote "Install with `winget`"
    ```pwsh title="PowerShell"
    winget install --exact --id=NickeManarin.ScreenToGif
    ```

## Git

Install [Git for Windows] and keep the default options in the installer dialog pages.

Optionally, install [GitHub Desktop] and [authenticate with GitHub].

We recommend GitHub Desktop because it is designed to be an application for git and GitHub actions.

??? quote "Install with `winget`"
    ```pwsh title="PowerShell"
    winget install --exact --id=Git.Git
    winget install --exact --id=GitHub.GitHubDesktop
    ```

### Practical exercises

1. Complete the full [pull request workflow tutorial] to create your own profile README from your browser.
1. Repeat the tutorial [using GitHub Desktop] and update your profile README page.
1. Repeat the tutorial [using Visual Studio Code] and update your profile README page.
1. Repeat the tutorial [using git commands] when possible and update your profile README page.
1. Choose another tutorial from [the GitHub skills] collection.


[Visual Studio Code]: https://code.visualstudio.com
[using git]: https://code.visualstudio.com/docs/sourcecontrol/overview
[developing Python]: https://code.visualstudio.com/docs/languages/python
[VS Code extensions]: https://marketplace.visualstudio.com
[donjayamanne.**git-extension-pack**]: https://marketplace.visualstudio.com/items?itemName=donjayamanne.git-extension-pack
[ms-python.**python**]: https://marketplace.visualstudio.com/items?itemName=ms-python.python
[bierner.**github-markdown-preview**]: https://marketplace.visualstudio.com/items?itemName=bierner.github-markdown-preview
[charliermarsh.**ruff**]: https://marketplace.visualstudio.com/items?itemName=charliermarsh.ruff
[astral-sh.**ty**]: https://marketplace.visualstudio.com/items?itemName=astral-sh.ty
[tamasfe.**even-better-toml**]: https://marketplace.visualstudio.com/items?itemName=tamasfe.even-better-toml
[ms-toolsai.**jupyter**]: https://marketplace.visualstudio.com/items?itemName=ms-toolsai.jupyter
[getting started tutorial]: https://code.visualstudio.com/docs/getstarted/getting-started

[Windows Terminal]: https://learn.microsoft.com/en-us/windows/terminal/install
[copy selection to clipboard]: https://learn.microsoft.com/en-us/windows/terminal/customize-settings/interaction#automatically-copy-selection-to-clipboard
[CaskaydiaCove Nerd Font]: https://learn.microsoft.com/en-us/windows/terminal/tutorials/custom-prompt-setup#install-a-nerd-font

[PowerShell]: https://learn.microsoft.com/en-us/powershell/scripting/install/installing-powershell-on-windows
[Oh My Posh]: https://learn.microsoft.com/en-us/windows/terminal/tutorials/custom-prompt-setup#customize-your-powershell-prompt-with-oh-my-posh
[Terminal Icons]: https://learn.microsoft.com/en-us/windows/terminal/tutorials/custom-prompt-setup#use-terminal-icons-to-add-missing-folder-or-file-icons

[ScreenToGif]: https://www.screentogif.com/downloads

[Git for Windows]: https://gitforwindows.org/
[GitHub Desktop]: https://desktop.github.com/download/
[authenticate with GitHub]: https://docs.github.com/en/desktop/overview/getting-started-with-github-desktop
[pull request workflow tutorial]: https://github.com/skills/introduction-to-github
[using GitHub Desktop]: https://docs.github.com/en/desktop/overview/getting-started-with-github-desktop#part-3-contributing-to-projects-with-github-desktop
[using Visual Studio Code]: https://code.visualstudio.com/docs/sourcecontrol/overview
[using git commands]: https://git-scm.com/book/en/v2/GitHub-Contributing-to-a-Project
[the GitHub skills]: https://skills.github.com/
