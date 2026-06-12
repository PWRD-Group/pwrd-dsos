"""A client for downloading datasets from a Huwise OpenData portal."""

import logging
import time
from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
from urllib.parse import quote, urlencode

import httpx

from pwrd.huwise import _get_api_key

logger = logging.getLogger(__name__)


class Resource:
    """A OpenData resource."""

    def __init__(self, client: "Client", info: dict) -> None:
        self.client = client
        self.info = info

    @property
    def name(self) -> str:
        """The dataset identifier."""
        return self.info["resource"]["name"]

    def __repr__(self) -> str:
        return f"<Resource name='{self.name}'>"

    def _export_paths(self) -> dict[str, str]:
        """A dictionary of allowed file types to export (download)."""
        info = self.info["resource"]
        return {info["format"].lower(): info["url"]}

    def file(self, ext: str | None = None) -> Path:
        """Get the local path to the file.

        If the file doesn't exist locally in the cache, then it is
        downloaded.
        """
        # If ext is not supplied then get it from the info
        ext = ext or self.info["resource"]["format"].lower()

        # First we should check if this exists
        href = self._export_paths().get(ext)
        if not href:
            msg = f"{self.name} can not be exported as {ext}"
            raise ValueError(msg)

        name = Path(href).name

        # TODO: Add some check for if the file has been modified
        # https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project/-/work_items/1
        cache_path = self.client.cache_path / name
        if cache_path.exists():
            return cache_path

        logger.info("%s doesn't exist in cache... downloading", cache_path)
        # Make the cache directory if it doesn't exist
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            cache_path.open("wb") as f,
            self.client.client.stream("GET", href) as r,
        ):
            for data in r.iter_raw():
                f.write(data)

        return cache_path


class Client(Mapping):
    """A client class for querying a Huwise (Opendatasoft) API."""

    name = "nged"

    def __init__(self) -> None:
        base_url = "https://connecteddata.nationalgrid.co.uk/api/3/action/"
        headers = {"Authorization": f"{_get_api_key(self.name)}"}
        self.client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
        self.cache_path = Path("./")

    def _api_call(
        self,
        api_url: str,
        *,
        limit: int = 20,
        sleep: float = 2.0,
        **kwargs,
    ) -> list[dict]:
        """Make a generic API call handling pagination."""
        # By setting limit = 0 we get no data, just how many entries
        # there are in the dataset
        params = kwargs | {"limit": 0}
        params = urlencode(params, safe="()", quote_via=quote)

        r = self.client.get(api_url, params=params)
        r.raise_for_status()
        # Assuming that all data follows a similar pattern of
        # total_count and results
        total_count = r.json()["total_count"]

        results = []

        for offset in range(0, total_count, limit):
            params = kwargs | {"limit": limit, "offset": offset}
            params = urlencode(params, safe="()", quote_via=quote)
            # Make request to API
            r = self.client.get(api_url, params=params)
            # Sleep for a bit so we don't make the API angry
            time.sleep(sleep)
            # Check that the status is good
            r.raise_for_status()
            # Add the results to results
            results += r.json()["results"]

        return results

    @cached_property
    def catalogue(self) -> dict[str, Resource]:
        """The available resources."""
        catalogue = {}
        endpoint = "current_package_list_with_resources"
        params = {"limit": 10, "offset": 0}
        # We will do this until we don't get as many results as we ask for
        while True:
            result = self.client.get(endpoint, params=params).json()

            if not result["success"]:
                msg = "Failed to get NGED package list"
                raise RuntimeError(msg)

            for group in result["result"]:
                group_data = {i: j for i, j in group.items() if i != "resources"}

                for resource in group["resources"]:
                    info = {
                        "resource": resource,
                        "group": group_data,
                    }
                    name = f"{group['name']}/{resource['name']}"
                    catalogue[name] = Resource(self, info)

            if len(result["result"]) != params["limit"]:
                break
            else:
                params["offset"] += params["limit"]
                # Small sleep to try and not abuse the API
                time.sleep(0.1)

        return catalogue

    def __getitem__(self, name: str) -> Resource:
        """Return the item as a Resource."""
        return self.catalogue[name]

    def keys(self):
        """All keys in the catalogue."""
        return self.catalogue.keys()

    def __len__(self) -> int:
        """The number of entries in the catalogue."""
        return len(self.catalogue)

    def __iter__(self):
        """Iterate through the keys in the catalogue."""
        yield from self.catalogue.keys()
