# pwrd-dsos Contributing Guide

## Welcome
Welcome to the pwrd-dsos Contributing Guide, and thank you for your interest in contributing!
All contributions, no matter how small, are valued. Whether you're fixing a typo, reporting a bug, or adding a new feature, we're glad you're here.

If you would like to contribute to a specific part of the project, check out the following list of contributions that we accept and their corresponding sections within this guide:

## Code

**Bug fixes** — if you've found something that isn't working as expected, please open an issue first and then submit a pull request with a fix.

**New features** — please open an issue to discuss your idea before writing code. This avoids duplicated effort and helps us agree on scope before you invest time in implementation.

**Tests** — improvements to test coverage are always welcome. We use `pytest`; please ensure any new code you contribute includes appropriate tests.

## Issues

**Bug reports** — if you encounter unexpected behaviour, please open a GitHub issue using the bug report template. Include a minimal reproducible example where possible.

**Feature requests** — open a GitHub issue with the label `enhancement` to propose new functionality. Describe the use case and expected behaviour clearly.

**Questions** — if you're unsure how to use the package, open a GitHub issue with the label `question`. We don't currently have a separate discussion forum.

## Documentation

Improvements to the documentation are very welcome — this includes fixing typos, clarifying existing explanations, improving docstrings, and adding usage examples. Documentation lives alongside the source code and is built with the same `uv sync` setup described below.

---

However, at this time, we do not accept the following contributions:

- **Contributions that only work on one operating system** — the package should work on Windows, macOS, and Linux.
- **Large-scale refactors without prior discussion** — please open an issue first so we can assess scope and priority together.
- **New dependencies** — we aim to keep the dependency footprint small. Any proposal to add a new dependency should be discussed in an issue first.

---

## pwrd-dsos overview
pwrd is a Python package for working with open data from UK based Distribution Network Operators (DNOs). For more information, please see the package [documentation](https://pwrd-group.github.io/pwrd-dsos/).

## Ground rules
Before contributing, read our [Code of Conduct](CODE_OF_CONDUCT.md) to learn more about our community guidelines and expectations.

## Share ideas
To share your new ideas for the project, please open a GitHub issue.

## Before you start
Before you start contributing, ensure you have the following:

- A [GitHub account](https://github.com/signup)
- An account on [https://earthdatahub.destine.eu/](https://earthdatahub.destine.eu/)

## Environment setup
To set up your environment, you will need to:

- Install Python version 3.13 or higher
- Create a venv and install the package as follows:

```
python -m venv /path/to/new/virtual/environment
source /path/to/new/virtual/environment/bin/activate
python -m pip install git+https://github.com/PWRD-Group/pwrd-dsos.git
```

- Install the project dependencies by cloning the GitHub repo and running `uv sync`:

```
git clone https://github.com/PWRD-Group/pwrd-dsos.git
cd pwrd-dsos/
uv sync --group marimo
```

## Troubleshoot
If you encounter issues as you set up your environment, refer to the following:

- **Windows:** Ensure you are using Git Bash or PowerShell with execution policies set to allow scripts. See the [Python on Windows setup guide](https://docs.python.org/3/using/windows.html) for common issues.
- **macOS:** If `python3` is not found, you may need to install it via Homebrew (`brew install python`). See the [Python on macOS setup guide](https://docs.python.org/3/using/mac.html).
- **Linux:** Ensure `python3-venv` is installed (`sudo apt install python3-venv` on Debian/Ubuntu). See the [Python on Unix setup guide](https://docs.python.org/3/using/unix.html).

## Best practices
Our project has adopted the following best practices for contributing:

Our project uses [Ruff's Python style guide](https://docs.astral.sh/ruff/formatter/#style-guide) as our parent guide for best practices. Reference the guide to familiarise yourself with the best practices we want contributors to follow.

---

## Contribution workflow

### Fork and clone the repository
1. Navigate to [https://github.com/PWRD-Group/pwrd-dsos](https://github.com/PWRD-Group/pwrd-dsos).
2. Click the **Fork** button in the top-right corner to create a copy under your own GitHub account.
3. Clone your fork locally:
   ```
   git clone https://github.com/YOUR-USERNAME/pwrd-dsos.git
   cd pwrd-dsos/
   ```
4. Add the original repository as an upstream remote so you can keep your fork up to date:
   ```
   git remote add upstream https://github.com/PWRD-Group/pwrd-dsos.git
   ```

For a detailed walkthrough, see [GitHub's forking guide](https://docs.github.com/en/get-started/exploring-projects-on-github/contributing-to-a-project).

### Report issues and bugs
Before opening a new issue, please search the [existing issues](https://github.com/PWRD-Group/pwrd-dsos/issues) to avoid duplicates. When filing a bug report, include:
- A short, descriptive title
- Steps to reproduce the problem
- What you expected to happen and what actually happened
- Your Python version and operating system

### Issue management
- Use the `bug`, `enhancement`, or `question` labels when opening an issue.
- If you intend to work on an issue yourself, please comment on it to let us know so we don't duplicate effort.
- We aim to respond to new issues within a week.

### Commit messages
Write short, descriptive commit messages in the imperative mood, for example:

```
Fix connection issue to external inventories
Add an example using north west electricity client
```

Avoid vague messages like `fix stuff` or `updates`. If a commit relates to an open issue, reference it: `Fix #42: add longer description about the resilience dataframe`.

### Branch creation
Create a new branch from `main` for each contribution. Name branches descriptively using lowercase and hyphens:

```
git checkout -b fix/forecast-threshold-bug
git checkout -b feature/add-dno-lookup
git checkout -b docs/improve-contributing-guide
```

Prefixes to use:
- `fix/` — bug fixes
- `feature/` — new functionality
- `docs/` — documentation only changes
- `test/` — test additions or corrections

### Pull requests
When your changes are ready:
When your changes are ready:

1. Push your branch to your fork:
   ```
   git push origin your-branch-name
   ```
2. Open a pull request against the `main` branch of the upstream repository.  
3. In your PR description, include:
   - A summary of the changes made
   - The issue number it addresses (e.g. `Closes #42`)
   - Any relevant context reviewers should know  
4. Confirm that all CI actions pass on your PR.  
5. If needed, address any formatter fails by using `ruff format` locally (see more about formatting [here](https://docs.astral.sh/ruff/formatter/) )  
6. Be responsive to review comments — we aim to review PRs within two weeks.  
7. Once approved, a maintainer will merge your PR.  

Please keep pull requests focused and reasonably small — one logical change per PR makes review much easier.

### Releases
This project uses [semantic versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`). Releases are made by the maintainers when there is a meaningful set of changes to publish. There is no fixed release cadence — we release when it makes sense. If you believe a fix is urgent, flag it in the relevant issue.

### Text formats
All documentation and prose files (including this one) are written in [Markdown](https://www.markdownguide.org/). Please use standard Markdown syntax. Docstrings in source code should follow the [Google docstring format](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings).

---

*Template from [The Good Docs Project](https://thegooddocsproject.dev/). Customised with the help of Claude Sonnet 4.6*