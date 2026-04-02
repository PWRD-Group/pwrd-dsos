# PWRD

[![pipeline status](https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project/badges/main/pipeline.svg)](https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project/-/commits/main)
[![coverage report](https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project/badges/main/coverage.svg)](https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project/-/commits/main)

## Getting started

### Installing

There are two ways to install the package, depending on whether or not
you want access to the notebooks. If you just want the `pwrd` package,
then you can use `pip install`. If you want the notebooks, or to
develop then follow the `git clone` route.

Regardless of which route you choose, you will need to follow the
[Setup instructions](#setup).

#### `pip install`

It is possible to `pip install` the `pwrd` package directly with
`pip`. Note that if you are installing the package this way you will
not get the notebooks but you could download them individually to test
things out.

It is recommended to use a virtual environment when installing the
package so you don't mess up any other projects accidentally.  See
[here](https://docs.python.org/3/library/venv.html#how-venvs-work) for
setup instructions if not using `PowerShell` on Windows or `bash/zsh`
on Linux/MacOS.

You will probably be required to enter your gitlab username and
password. If you have setup 2FA your password will be a personal
access token rather than your standard password.

##### Windows

> [!caution]
> This has not been tested. Please let me know if you try this and it works or not!

```
python -m venv C:\path\to\new\virtual\environment
C:\path\to\new\virtual\environment\Scripts\Activate.ps1
python -m pip install git+https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project.git
```

##### Linux/MacOS

```
python -m venv /path/to/new/virtual/environment
source /path/to/new/virtual/environment/bin/activate
python -m pip install git+https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project.git
```

#### `git clone` and `uv`

If you are developing the package, or you would like to run the
notebooks, then I recommend installing `uv`. See
[here](https://docs.astral.sh/uv/) for installation instructions.

First clone the repo

```
git clone https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project.git
cd rsg-project/
uv sync --group marimo
```

You can now run `marimo` to view the notebooks

```
uv run marimo edit
```

## RSG project notebooks

This repository contains [marimo](https://docs.marimo.io) notebooks
developed during the course of the RSG project: `fcod-donalddl-1`.
The notebooks are used in an exploratory manner to investigate the
kinds of analyses that are performed. The long term aim is to extract
common pieces of code into a maintainable package with tests,
documentation, etc.

## Setup

To use these notebooks you will need to setup the following accounts:

1. An account on <https://earthdatahub.destine.eu>. Follow the
   instructions
   [here](https://earthdatahub.destine.eu/getting-started#configuring-netrc)
   to configure a `netrc` file containing your credentials.
2. An account on e.g. <https://ukpowernetworks.opendatasoft.com>. Once you
   have an account generate an API key and place it in the file
   `~/.config/huwise.toml` (making the directories if they don't
   already exist), like so
   ```toml
   [credentials]
   ukpowernetworks = "long-api-key"
   ```
   You can use connect to any of the DNOs that use `huwise/opendatasoft`. 
   The "name" part of the configuration should always be the first part of the 
   URL, so another example would be `electricitynorthwest`.
   
   If running on linux/mac, be sure to change the visibility of that
   file so that only you can read/write to it with `chmod 600
   ~/.config/huwise.toml`
