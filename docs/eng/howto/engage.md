---
icon: lucide/message-square-diff
tags:
  - Develop
  - How-to
  - Engage
---

# How to engage with the project

We use GitHub to host the source code, track bugs and requests, and run the build and release actions for `qtpy-datalogger`.

This page covers the first two: changing the source code and tracking issues.
If you haven't used GitHub before, continue reading to learn how we do these with a GitHub-hosted project.

If you want to learn about the build and release actions, go to our [Manage the package](manage.md) page.

## Use issues

We do not follow any automated or formal processes for handling issues, but as a baseline:

- We use labels to categorize issues
- We require code changes to reference an issue

These sections explain how we use GitHub issues in the project.

### Create an issue

Thank you for volunteering your time to describe a problem or ask for a new feature.

Please choose what best matches your topic.

<div class="grid cards" markdown>
- :lucide-bug:{ .lg .middle .qtpy }&nbsp; __[Bug report]__ :lucide-dot: _Create a new bug report_
</div>
<div class="grid cards" markdown>
- :lucide-star:{ .lg .middle .qtpy }&nbsp; __[Feature request]__ :lucide-dot: _Create a new feature request_
</div>
<div class="grid cards" markdown>
- :lucide-message-circle-question-mark:{ .lg .middle .qtpy }&nbsp; __[Help request]__ :lucide-dot: _Ask for help running the program or setting up your environment_
</div>
<div class="grid cards" markdown>
- :lucide-book-open-text:{ .lg .middle .qtpy }&nbsp; __[Website request]__ :lucide-dot: _Ask a question or add a suggestion about the website_
</div>

### Fix an issue

Thank you for volunteering your time to improve the code or documentation for `qtpy-datalogger`.

If you are new to coding, choose an issue from our [good first issue] list.
We also label issues with [help wanted] if they are good candidates for experienced coders new to this project.
However, you can choose any open issue that you want to fix.

When fixing an issue, follow the GitHub flow for [using issues].

1. Select an issue
    - Open the [issues list] and select an issue
    - Assign yourself to the issue
    - Add the **active** label to it
    - Ask questions in the issue if you want more information
1. Create a branch and make code changes
    - Ask questions in the issue as you encounter obstacles
    - Add notes to the issue as you make progress
1. Open a PR with the proposed fixes
    - Include this [keyword phrase] in the description, where `ID` is the issue's number
        ```
        Closes #ID
        ```
    - Respond to feedback
1. Close the issue
    - Complete the pull request
    - Remove the **active** label from the issue

For specific workflows about using git and running the tests and analyzers for `qtpy-datalogger`, go to our [Workflows](../intro/workflows.md) page.

### Triage new issues

When someone creates a new issue, GitHub adds an **inbox** label.
Depending on the type of the issue that they selected, GitHub adds additional labels.

Once we notice a new issue, we can help it get the right attention by categorizing them.

1. Filter for new bug reports and feature requests with the **[inbox]** label
1. Use the [full label list] to add and remove labels to match the issue's topic
1. Remove the **inbox** label to remove it from the triage list

### Labels

These are the most common labels that we use.

| Label | Description |
|------:|:------------|
| **[active]** | This item is in work |
| **[bug]** | Something isn't working |
| **[enhancement]** | New feature or request |
| **[inbox]** | This issue needs to be triaged |
| **[question]** | Questions or problems with qtpy-datalogger |

See the [full label list] for other views of this project's issues.

## Change source code

This project uses the same GitHub repository for its source code and website documentation.
Changes to either happen with pull requests.

Before opening a pull request, please select an issue from the [issues list] and assign it to yourself.

### Open a pull request

Once you own an issue, follow the GitHub flow for [collaborating with pull requests].

1. Create a branch
1. Commit changes to it
1. Publish your branch
1. Create a pull request
1. [Respond to feedback] and questions

For specific workflows about using git and running the tests and analyzers for `qtpy-datalogger`, go to our [Workflows](../intro/workflows.md) page.

### Review a pull request

We require one maintainer to approve the changes in pull requests.
Follow the GitHub flow for [reviewing pull requests].

1. Open the pull request page
1. Inspect the changed files
1. Add feedback or ask questions
1. [Approve the PR] when you're satisfied with the proposed changes


[Bug report]: https://github.com/wireddown/qtpy-datalogger/issues/new?template=bug-report.md
[Feature request]: https://github.com/wireddown/qtpy-datalogger/issues/new?template=feature-request.md
[Help request]: https://github.com/wireddown/qtpy-datalogger/issues/new?template=help-request.md
[Website request]: https://github.com/wireddown/qtpy-datalogger/issues/new?template=site-request.md

[good first issue]: https://github.com/wireddown/qtpy-datalogger/issues?q=state%3Aopen%20label%3A%22good%20first%20issue%22
[help wanted]: https://github.com/wireddown/qtpy-datalogger/issues?q=state%3Aopen%20label%3A%22help%20wanted%22
[using issues]:https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues
[issues list]: https://github.com/wireddown/qtpy-datalogger/issues
[keyword phrase]: https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue#linking-a-pull-request-to-an-issue-using-a-keyword
[inbox]: https://github.com/wireddown/qtpy-datalogger/labels/inbox?q=state%3Aopen%20label%3Ainbox
[full label list]: https://github.com/wireddown/qtpy-datalogger/labels
[active]: https://github.com/wireddown/qtpy-datalogger/issues?q=state%3Aopen%20label%3Aactive
[bug]: https://github.com/wireddown/qtpy-datalogger/issues?q=state%3Aopen%20label%3Abug
[enhancement]: https://github.com/wireddown/qtpy-datalogger/issues?q=state%3Aopen%20label%3Aenhancement
[question]: https://github.com/wireddown/qtpy-datalogger/issues?q=state%3Aopen%20label%3Aquestion

[collaborating with pull requests]: https://docs.github.com/en/pull-requests/how-tos/create-pull-requests
[Respond to feedback]: https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/incorporating-feedback-in-your-pull-request
[reviewing pull requests]: https://docs.github.com/en/pull-requests/how-tos/review-pull-requests
[Approve the PR]: https://docs.github.com/en/pull-requests/how-tos/review-pull-requests/approving-a-pull-request-with-required-reviews
