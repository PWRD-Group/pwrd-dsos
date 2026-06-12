"""A client for downloading datasets from a Huwise OpenData portal."""

import logging
import time
from functools import cached_property
from pathlib import Path

import httpx

from pwrd.huwise import _get_api_key, Resource as HuwiseResource, Client as HuwiseClient

logger = logging.getLogger(__name__)


class Resource(HuwiseResource):
    """An NGED resource."""

    @property
    def name(self) -> str:
        """The dataset identifier."""
        # There is self.info["resource"]["name"] but using the URL
        # stem works a bit better for compatibility
        return str(Path(self.info["resource"]["url"]).stem)

    # TODO: We need to do something about __len__

    def _export_paths(self) -> dict[str, str]:
        """A dictionary of allowed file types to export (download)."""
        info = self.info["resource"]
        return {info["format"].lower(): info["url"]}


class Client(HuwiseClient):
    """A client class for querying the National Grid connecteddata API."""

    name = "nged"

    def __init__(self) -> None:
        base_url = "https://connecteddata.nationalgrid.co.uk/api/3/action/"
        headers = {"Authorization": f"{_get_api_key(self.name)}"}
        self.client = httpx.Client(base_url=base_url, headers=headers, timeout=30.0)
        self.cache_path = Path("./")

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
