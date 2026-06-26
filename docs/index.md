---
icon: lucide/zap
---

# PWRD

`pwrd` is a Python package for working with open data from UK based
Distribution Network Operators (DNOs).

## Motivation

`pwrd` has been created to simplify access to open data resources for
researchers studying energy systems. It's goal is to remove the need
for "manual" downloads through a web browser, using API calls
to download data as needed. `pwrd` makes it easier to share scripts
between collaborators without needing to send over data files required
for them to run.

In addition to data access, `pwrd` implements some commonly used
methods for working with the types of data DNOs typically supply, and
an interface to ERA5 data.

## Getting started

In order to access a DNO's open data portal, you will first have to
create an account for it and setup an API key. Once setup, open data
can be queried using a `Client` instance. Each
DNO has its own `Client` that you interact
with. For example, to access UK Power Networks open data portal you
use the [`UKPNClient`][pwrd.dnos.UKPNClient].

```python
from pwrd.dnos import UKPNClient

client = UKPNClient()
```

`Client`s are available for the following DNOs:

- [x] UK Power Networks - [`UKPNClient`][pwrd.dnos.UKPNClient]
- [x] Electricity North West England - [`ENWClient`][pwrd.dnos.ENWClient]
- [x] Northern Power Grid - [`NPGClient`][pwrd.dnos.NPGClient]
- [x] Scottish Power Energy Networks - [`SPENClient`][pwrd.dnos.SPENClient]
- [x] National Grid DNO - [`NGEDClient`][pwrd.dnos.NGEDClient]
- [ ] Scottish & Southern Electricity Networks

All [`Client`][pwrd.dnos.base.Client] objects act like
[`Mapping`][collections.abc.Mapping] objects. Available data resources
can be queried using the [`client.keys()`][pwrd.dnos.base.Client.keys]
method, as one would query a dictionary.

The values of the [`Client`][pwrd.dnos.base.Client] objects are
[`Resource`][pwrd.dnos.base.Resource] objects. These act as a lightweight
bridge between the data catalogue and the actual datasets. For example

```python
resource = client["ukpn_primary_postcode_area"]
```

!!! note

    `pwrd` doesn't attempt to organise the resources any further
	than what is done in each of the DNOs open data portals e.g.
	`"ukpn_primary_postcode_area"` won't work across all clients

Metadata can be queried using the `.info` attribute. This returns data
available from each open data portal API. There is no guarantee that
the structure of this metadata is consistent across DNOs.

To perform file download, use the [`.file`][pwrd.dnos.base.Resource.file]
method on the
[`Resource`][pwrd.dnos.base.Resource]. [`.file`][pwrd.dnos.base.Resource.file]
returns a [`Path`][pathlib.Path] object to the resulting downloaded
file. If the file has been downloaded previously, no new download is
performed and the path to the file is returned instantly.

```python
file_path = resource.file("parquet")
```

This can then be opened for analysis as normal. For example with
[`geopandas`][geopandas]

```python
import geopandas as gpd

gdf = gpd.read_parquet(file_path)
```

[geopandas]: https://geopandas.org/en/stable/
