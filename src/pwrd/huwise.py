"""A client for downloading datasets from a Huwise OpenData portal."""

import logging
import time
from collections.abc import Mapping
from functools import cached_property
from pathlib import Path
from textwrap import dedent
from typing import ClassVar
from urllib.parse import quote, urlencode

import httpx

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path().home() / ".config" / "huwise.toml"


def _get_api_key(name: str, config_path: Path = DEFAULT_CONFIG_PATH) -> str:
    """Read the API key from a file in a .config directory."""
    if not config_path.exists():
        msg = dedent(f"""\
        No API key found.
        Create the file and put your token inside:
        {config_path}
        Example:
        echo 'YOUR_API_TOKEN' > {config_path}
        chmod 600 {config_path}
        """)
        raise FileNotFoundError(msg)

    with config_path.open("rb") as f:
        import tomllib

        api_key = tomllib.load(f)["credentials"][name].strip()

    return api_key


class Resource:
    """A OpenData resource."""

    def __init__(self, client: "Client", info: dict) -> None:
        self.client = client
        self.info = info

    @property
    def name(self) -> str:
        """The dataset identifier."""
        return self.info["dataset_id"]

    def __repr__(self) -> str:
        return f"<Resource name='{self.name}'>"

    def __len__(self) -> int:
        """The record count."""
        return int(self.info["metas"]["default"]["records_count"])

    def _export_paths(self) -> dict[str, str]:
        """A dictionary of allowed file types to export (download)."""
        r = self.client.client.get(f"/{self.name}/exports")
        r.raise_for_status()
        return {i["rel"]: i["href"] for i in r.json()["links"]}

    def file(self, ext: str) -> Path:
        """Get the local path to the file.

        If the file doesn't exist locally in the cache, then it is
        downloaded.
        """
        # TODO: Add some check for if the file has been modified
        # https://gitlab.bham.ac.uk/donalddl-pwrd/rsg-project/-/work_items/1
        cache_path = self.client.cache_path / f"{self.name}.{ext}"
        if cache_path.exists():
            return cache_path

        # Otherwise we need to download this file
        # First we should check if this exists
        href = self._export_paths().get(ext)
        if not href:
            msg = f"{self.name} can not be exported as {ext}"
            raise ValueError(msg)

        logger.info("%s doesn't exist in cache... downloading", cache_path)
        # Make the cache directory if it doesn't exist
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            cache_path.open("wb") as f,
            self.client.client.stream("GET", f"/{self.name}/exports/{ext}") as r,
        ):
            for data in r.iter_raw():
                f.write(data)

        return cache_path


class Client(Mapping):
    """A client class for querying a Huwise (Opendatasoft) API."""

    name: ClassVar[str]

    def __init__(self) -> None:
        base_url = (
            f"https://{self.name}.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
        )
        headers = {"Authorization": f"Apikey {_get_api_key(self.name)}"}
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
        cat_list = self._api_call("/", limit=100, sleep=0.1)
        catalogue = {i["dataset_id"]: Resource(self, i) for i in cat_list}
        if len(catalogue) != len(cat_list):
            msg = "Repeated keys in data catalogue"
            raise ValueError(msg)
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


class UKPNClient(Client):
    name = "ukpowernetworks"


class ENWClient(Client):
    name = "electricitynorthwest"


class SPENClient(Client):
    name = "spenergynetworks"


class NPGClient(Client):
    name = "northernpowergrid"
