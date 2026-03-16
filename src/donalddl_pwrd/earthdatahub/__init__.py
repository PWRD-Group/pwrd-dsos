from pathlib import Path

from zarr.storage import LocalStore
from zarr.experimental.cache_store import CacheStore

class LocalCache:

    def __init__(self, path=None):
        path = path or Path.cwd()
        self.path = Path(path)

    def create_cache_store(self, fsspec_store):
        fname = Path(fsspec_store.path).name
        local_store = LocalStore(self.path / fname)
        return CacheStore(store=fsspec_store, cache_store=local_store)
