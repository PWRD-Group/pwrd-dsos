from pathlib import Path

from zarr.storage import LocalStore
from zarr.experimental.cache_store import CacheStore

def convert_longitude(ds):
    """Given an xarray dataset, converts longitude from 0->360 to -180->180.

    Usage:

    Given a dataset `ds` use as
    `ds = ds.assign_coords(longitude=convert_longitude)`
    """
    return ((ds.longitude + 180) % 360) - 180

class LocalCache:

    def __init__(self, path=None):
        path = path or Path.cwd()
        self.path = Path(path)

    def create_cache_store(self, fsspec_store):
        fname = Path(fsspec_store.path).name
        local_store = LocalStore(self.path / fname)
        return CacheStore(store=fsspec_store, cache_store=local_store)
