"""A client for downloading datasets from a Huwise OpenData portal."""

import logging
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
    result_field = "result"
    base_url = "https://connecteddata.nationalgrid.co.uk/api/3/action/"

    @property
    def auth(self) -> str:
        return f"{_get_api_key(self.name)}"

    @cached_property
    def catalogue(self) -> dict[str, Resource]:
        """The available resources."""
        catalogue = {}
        endpoint = "current_package_list_with_resources"

        for results in self._api_call(endpoint, sleep=0.1):
            for group in results:
                group_data = {i: j for i, j in group.items() if i != "resources"}
                for resource in group["resources"]:
                    info = {
                        "resource": resource,
                        "group": group_data,
                    }
                    name = f"{group['name']}/{resource['name']}"
                    catalogue[name] = Resource(self, info)

        return catalogue
