---
icon: fontawesome/brands/github
tags:
  - Develop
  - How-to
  - Manage
  - Version
  - Release
  - GitHub
  - Action
---

# How to manage the package

We use GitHub to host the source code, track bugs and requests, and run the build and release actions for `qtpy-datalogger`.

This page covers the last one: the governance actions performed by project administrators.
If you haven't used GitHub before, continue reading to learn how we administer a GitHub-hosted project.

## Change the version

We automatically change the project's patch version _immediately_ after each release.
For new features and API changes, we change the minor and major versions by hand.

### After every release

After releasing the package, our [publish GitHub action](#publish-release-on-pypi) automatically bumps the patch version, which assumes the next release fixes bugs.

Changing the version after releasing gives local clones of the repo a newer version in the `pyproject.toml` file.
This helps development workflows because new unreleased work appears as an upgrade to the QT Py sensor nodes.

### By hand

We change the version by hand when we make a notable behavior or API change as recommended by [Semantic versioning] with three version fields: `Major.Minor.Patch`.

- We increment the `Patch` number for **bug fixes**
- We increment the `Minor` number for **new features**
- We increment the `Major` number for **API changes**

!!! warning "Semantic versioning on hold until version 1.1.0"

    The **1.0.x** series **does not conform** to Semantic versioning.

    1. We're still defining what kinds of **API changes** in our package would cause us to bump the **major version**.
    We're considering selecting the shared MQTT topic format and message API as the conditions because sensor node controllers might be written in other languages.
    These "on the wire" topic and data structures are therefore the most important for same-major-version compatibility.
    If you have a use-case or input, please let us know in a [new issue].

    1. In addition, we have one deployed application still under long term testing.
    We're reworking its new capabilities into the main package as reusable APIs for other applications to use.
    We shall bump the **minor** version once the additions are complete and we publish that application with the main package.

    Until these two are resolved, we shall continue bumping the **1.0.x** patch version and may include API changes.

To change the version of `qtpy-datalogger`, use **[uv version]**.

```pwsh title="PowerShell"
# Show the current version
uv version

# Increment the version's patch number: 4.1.1 becomes 4.1.2
uv version --bump patch

# Increment the version's minor number: 4.1.1 becomes 4.2.0
uv version --bump minor

# Increment the version's major number: 4.1.1 becomes 5.0.0
uv version --bump major
```

## Release the package

We do not automate our releases.
Instead, we release by hand with the GitHub web interface.
Once we publish a GitHub release, our [publish GitHub action](#publish-release-on-pypi) publishes the package to [PyPI].

### Draft a release

We use the GitHub web interface to interactively draft and publish new releases.

1. From the [Releases] page, click the **Draft a new release** button
1. Set the git tag, target branch, and release title
    - Lookup the new version from **`pyproject.toml`** in the `main` branch
    - Create a new tag that matches the new version
    - Keep the release target on the `main` branch
    - Use the new version as the title for the release
1. Write the release notes
    - Keep the previous tag set to _Auto_
    - Click the **Generate release notes** button
    - Reformat the generated notes to match this template
    ```markdown title="Release announcement template"
    ## Highlight of the release

    Describe the highlights of the release

    ## What's Changed

    List the PRs that added features and fixed bugs

    ## Documentation

    List any PRs that updated documentation

    ## Dependencies and package

    Sort and list the PRs that updated dependencies and the `pyproject.toml` file
    ```
    - Click the **Save draft** button to retain the notes

### Publish a release

After drafting the release, there are few more steps to publish the new package.

1. Click the **Publish release** button
1. In response, two GitHub actions start
    - Our [publish GitHub action](#publish-release-on-pypi) publishes the package to PyPI and bumps the patch version in a follow-up pull request
    - Our [documentation GitHub action](#docs-build-and-publish) publishes the documentation to this website
1. Monitor both actions
    - Approve and complete the follow-up pull request that bumps the package's version

## Manage GitHub actions

We automate these tasks with GitHub actions.

- Continuous integration
    - Run the tests and analyzers for every supported version of Python
- Dependency management
    - Check for outdated dependencies and upgrade them
- Release
    - Build and publish the documentation to the website
    - Build and release the package to PyPI

### [CI: Tests and Analyzers]

This action **automatically runs** for every pull request creation, pull request update, and pull request merge.
Its purpose is to evaluate the quality of the changes by running the tests and analyzers with all supported versions of Python.

- As steps execute, they add information to the [job's run summary] by writing to the `$env:GITHUB_STEP_SUMMARY` variable
    - To safely add emojis to the summary, the steps use the [GitHub emoji aliases], where text like `:ok:` renders to 🆗
- The steps call the tests and analyzers with options so that they write results to JUnit XML formatted files
- When the analyzers find problems, the action adds remedy instructions to the run summary
- After the analyzers finish, the action generates a report from the JUnit results files using the [test-reporter action]
- Finally, the steps build both the distribution packages and the website documentation so that reviewers can download and inspect them

### [Dependabot Updates]

This action **automatically runs** for two reasons.

- A Python dependency has an update for a **security vulnerability**
- The **monthly scheduled run** executes and queries for new versions

Its purpose is to minimize `qtpy-datalogger`'s exposure to vulnerabilities, regularly keep its dependencies updated, and detect new incompatibilities.
When GitHub runs this action, the Dependabot account opens a [new pull request with the upgraded dependency version].

We [configure Dependabot] to use two package ecosystems

- `uv` to update our Python dependencies
- `github-actions` to update our GitHub action definitions

### [Docs: Build and Publish]

This action **automatically runs** when we publish a new GitHub release.
We can also run this **on-demand** to update the website _without publishing_ a new package.

Its sole purpose is to update the website.

- The action uses a fresh Python environment to avoid cache poisoning
- The action builds our HTML documentation with [Zensical]
- The action publishes it to the project's [GitHub Pages] environment

### [Publish: Release on PyPI]

This action **automatically runs** when we publish a new GitHub release.
We can also run this **on-demand** _without publishing_ to preview changes and debug problems in the action.

Its purpose is to publish the package to [PyPI] and then enable next-version development by bumping the project's patch version in a follow-up pull request.

- The action uses a fresh Python environment to avoid cache poisoning
- Before publishing to PyPI, the action confirms that
    - the releasing **tag version** matches the **package version**
    - the releasing version has **not** been previously published to PyPI
- After publishing to PyPI, the action
    - bumps the package's patch version number
    - creates a PR with the updated version using the [create-pull-request action]

### Creating a new action

We create new GitHub actions when we want to add a new automation to the project.

1. Create a branch
1. Create a new yml file in the `.github\workflows` folder
1. Define the action in the yml file
1. Publish your branch
1. Perform an action that triggers the action
    - For example, if the action uses `on: pull_request`, then create a pull request to cause GitHub to run the action

#### Resources

- [Events that trigger workflows]: run your action when specific activity on GitHub happens
- [Evaluate expressions in workflows and actions]: use variables and functions to make decisions
- [Workflow contexts]: use runtime information from the action's jobs, steps, and environments
- [Workflow syntax for GitHub Actions]: keywords and values for action definitions
- [Tutorials]: practice common action tasks and using their features
- [awesome-actions]: a curated list of awesome actions to use on GitHub
- [Troubleshooting]: tools and logging options you can use to identify problems

#### Practical exercises

- [Hello GitHub Actions]: Learn how to create action files, trigger actions, and find action logs
- [Test with Actions]: Learn how to create an action that runs tests and produces test reports
- [Secure your repository's supply chain]: Learn how to enable Dependabot


[new issue]: https://github.com/wireddown/qtpy-datalogger/issues/new?template=feature-request.md
[uv version]: https://docs.astral.sh/uv/guides/package/#updating-your-version
[Semantic versioning]: https://semver.org/

[PyPI]: https://pypi.org/project/qtpy-datalogger/
[Releases]: https://github.com/wireddown/qtpy-datalogger/releases

[CI: Tests and Analyzers]: https://github.com/wireddown/qtpy-datalogger/actions/workflows/ci.yml
[job's run summary]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands#adding-a-job-summary
[GitHub emoji aliases]: https://github.com/ikatyang/emoji-cheat-sheet/blob/master/README.md
[test-reporter action]: https://github.com/marketplace/actions/test-reporter

[Dependabot Updates]: https://github.com/wireddown/qtpy-datalogger/actions/workflows/dependabot/dependabot-updates
[new pull request with the upgraded dependency version]: https://docs.github.com/en/code-security/concepts/supply-chain-security/dependabot-version-updates
[configure Dependabot]: https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference

[Docs: Build and Publish]: https://github.com/wireddown/qtpy-datalogger/actions/workflows/docs.yml
[Zensical]: https://zensical.org/
[GitHub Pages]: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages

[Publish: Release on PyPI]: https://github.com/wireddown/qtpy-datalogger/actions/workflows/publish.yml
[create-pull-request action]: https://github.com/marketplace/actions/create-pull-request

[Events that trigger workflows]: https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows
[Evaluate expressions in workflows and actions]: https://docs.github.com/en/actions/reference/workflows-and-actions/expressions
[Workflow contexts]: https://docs.github.com/en/actions/reference/workflows-and-actions/contexts
[Workflow syntax for GitHub Actions]: https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
[Tutorials]: https://docs.github.com/en/actions/tutorials
[awesome-actions]: https://github.com/sdras/awesome-actions/blob/main/README.md
[Troubleshooting]: https://docs.github.com/en/actions/how-tos/troubleshoot-workflows

[Hello GitHub Actions]: https://github.com/skills/hello-github-actions
[Test with Actions]: https://github.com/skills/test-with-actions
[Secure your repository's supply chain]: https://github.com/skills/secure-repository-supply-chain
