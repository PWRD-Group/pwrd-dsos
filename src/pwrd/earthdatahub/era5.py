"""ERA5 data stores from <https://earthdatahub.destine.eu>."""

import warnings
from netrc import netrc

from zarr.storage import FsspecStore


def _find_api_endpoint() -> str:
    """Find EarthDataHub API endpoint to use.

    EarthDataHub recently (Summer 2026) updated their API endpoint,
    and different tokens are used for each one. To allow for a smooth
    transition from one to the other we query the .netrc file, and
    will use the newer endpoint if available and the older if not.

    Returns
    -------
    str
        The url of the endpoint to use
    """
    endpoint = "api.earthdatahub.destine.eu"

    # If we don't have a netrc file then we will return the API
    # endpoint, which should postpone any errors to when a user tries
    # to download a file, at which point they should get 'Unauthorized'
    try:
        hosts = netrc().hosts
    except FileNotFoundError:
        return endpoint

    if endpoint in hosts:
        # "Standard API key exists - good!"
        return endpoint

    # Check if we have a Classic API key - fine if we do"
    endpoint = "data.earthdatahub.destine.eu"
    if endpoint in hosts:
        msg = (
            "EarthDataHub has introduced a new API endpoint that "
            "requires a new API token. Please see "
            "https://earthdatahub.destine.eu/account-settings "
            "for more information. pwrd will use your Classic API "
            "key but please consider obtaining a new key."
        )
        warnings.warn(msg)
        return endpoint

    # If we can't find anything then raise an exception
    msg = "Could not find earthdatahub API key in .netrc file"
    raise KeyError(msg)


BASE_URL = f"https://{_find_api_endpoint()}/era5"

ERA5_STORAGE_OPS = {"client_kwargs": {"trust_env": True}}

land_hourly_store = FsspecStore.from_url(
    f"{BASE_URL}/reanalysis-era5-land-no-antartica-v0.zarr",
    storage_options=ERA5_STORAGE_OPS,
)

hourly_single_levels_store = FsspecStore.from_url(
    f"{BASE_URL}/reanalysis-era5-single-levels-v0.zarr",
    storage_options=ERA5_STORAGE_OPS,
)
