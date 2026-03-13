# RSG project notebooks

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
2. An account on <https://ukpowernetworks.opendatasoft.com>. Once you
   have an account generate an API key and place it in the file
   `~/.config/huwise.toml` (making the directories if they don't
   already exist), like so
   ```toml
   [credentials]
   ukpowernetworks = "long-api-key"
   ```
   If running on linux/mac, be sure to change the visibility of that
   file so that only you can read/write to it with `chmod 600
   ~/.config/huwise.toml`
