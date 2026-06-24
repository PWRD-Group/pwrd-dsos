from unittest.mock import ANY
import pwrd

from pytest_httpx import HTTPXMock


def test_nged(httpx_mock: HTTPXMock):
    """Simple test that we can use the NGED Client."""
    client = pwrd.dnos.NGEDClient()
    assert client.name == "nged"

    resources = {
        "result": [
            {
                "name": "group1",
                "resources": [{"name": "resource1"}, {"name": "resource2"}],
            },
            {
                "name": "group2",
                "resources": [{"name": "resource1"}, {"name": "resource2"}],
            },
        ]
    }

    httpx_mock.add_response(
        url=client.base_url + "current_package_list_with_resources",
        match_params={"limit": ANY, "offset": ANY},
        json=resources,
    )

    # Check we can access the catalogue
    client.catalogue
