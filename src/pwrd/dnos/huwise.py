"""A client for downloading datasets from a Huwise OpenData portal."""

import logging
from functools import cached_property


from pwrd.dnos import base

logger = logging.getLogger(__name__)


class Resource(base.Resource):
    """A OpenData resource."""

    @property
    def name(self) -> str:
        """The dataset identifier."""
        return self.info["dataset_id"]

    def __len__(self) -> int:
        """The record count."""
        return int(self.info["metas"]["default"]["records_count"])

    def export_paths(self) -> dict[str, str]:
        r = self.client.client.get(f"/{self.name}/exports")
        r.raise_for_status()
        return {i["rel"]: i["href"] for i in r.json()["links"]}


class Client(base.Client):
    """A client class for querying a Huwise (Opendatasoft) API."""

    result_field = "results"

    @property
    def base_url(self):
        """The API base URL."""
        return (
            f"https://{self.name}.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
        )

    @property
    def auth(self):
        """The value of the Authorization field."""
        return f"Apikey {base._get_api_key(self.name)}"

    @cached_property
    def catalogue(self) -> dict[str, Resource]:
        """The available resources."""
        expected_size = 0
        catalogue = {}
        for results in self._api_call("/", limit=100, sleep=0.1):
            for i in results:
                catalogue[i["dataset_id"]] = Resource(self, i)
            expected_size += len(results)
        if len(catalogue) != expected_size:
            msg = "Repeated keys in data catalogue"
            raise ValueError(msg)
        return catalogue


class UKPNClient(Client):
    """Client for UK Power Networks API.

    Covers East England, London, and South East England.
    """

    name = "ukpowernetworks"


class ENWClient(Client):
    """Client for Electricity North West England API.

    Covers North West England.
    """

    name = "electricitynorthwest"


class SPENClient(Client):
    """Client for Scottish Power Energy Networks API.

    Covers South and Central Scotland, North Wales, Merseyside and
    Cheshire.
    """

    name = "spenergynetworks"


class NPGClient(Client):
    """Client for Northern Power Grid API.

    Covers Yorkshire and North East England.
    """

    name = "northernpowergrid"
