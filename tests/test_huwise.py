from unittest.mock import ANY, Mock
from textwrap import dedent

import pytest
from pytest_httpx import IteratorStream


from pwrd import huwise


def test_get_api_key_not_exists(tmp_path):
    with pytest.raises(FileNotFoundError):
        huwise._get_api_key(
            "string",
            config_path=tmp_path / "doesnt_exist",
        )


def test_get_api_key_exists(tmp_path):
    dummy_api_key = "XYZ123"
    dummy_data = dedent(f"""\
    [credentials]
    test = '{dummy_api_key}'
    """)

    config_toml = tmp_path / "config.toml"
    config_toml.write_text(dummy_data, encoding="utf-8")
    assert huwise._get_api_key("test", config_toml) == dummy_api_key


def test_client(httpx_mock):

    huwise._get_api_key = Mock(return_value="XYZ")

    # We use UKPNClient as an example, but we could use any of the
    # providers. Can potentially parametrize?
    client = huwise.UKPNClient()
    assert client.name == "ukpowernetworks"
    base_url = client.client.base_url

    httpx_mock.add_response(
        url=base_url, match_params={"limit": "0"}, json={"total_count": 5}
    )

    resources_data = {"results": [{"dataset_id": 1}, {"dataset_id": 2}]}

    httpx_mock.add_response(
        url=base_url,
        match_params={"limit": ANY, "offset": ANY},
        json=resources_data,
    )

    # Keys should equal the list of dataset_ids
    assert list(client.keys()) == [
        j for k in resources_data["results"] for i, j in k.items()
    ]
    # Check iteration (we should have an entry for each key)
    count = 0
    for i in client:
        count += 1
    assert count == len(client)

    # __getitem__ should return a `huwise.Resource`
    assert isinstance(client[1], huwise.Resource)


def test_resource(httpx_mock, tmp_path):

    huwise._get_api_key = Mock(return_value="XYZ")
    client = huwise.UKPNClient()
    client.cache_path = tmp_path
    base_url = client.client.base_url

    # Resources should not be created directly, but obtained from the
    # client. Here we are creating a Resource directly for testing
    n_records = 9
    info = {
        "dataset_id": "example",
        "metas": {"default": {"records_count": str(n_records)}},
    }
    # Not actually a parquet file, just for testing
    file_ext = "parquet"

    # Test that after creating a resource, we can access various
    # properties
    resource = huwise.Resource(client=client, info=info)
    assert repr(resource) == f"<Resource name='{resource.name}'>"
    assert resource.name == "example"
    assert len(resource) == n_records

    # Adds a mocked response for calls to exports
    httpx_mock.add_response(
        url=f"{base_url}{resource.name}/exports",
        json={"links": [{"rel": file_ext, "href": "href"}]},
        is_reusable=True,  # We will call this more than once
    )

    # Add a mocked response for file download
    file_url = f"{base_url}{resource.name}/exports/{file_ext}"
    httpx_mock.add_response(
        url=file_url,
        stream=IteratorStream([b"part1", b"part2"]),
    )

    # "Download" the file
    path_to_file = resource.file(file_ext)
    # Check that a request has been made
    request = httpx_mock.get_request(url=file_url)
    assert request is not None
    assert path_to_file.parent == tmp_path
    assert path_to_file.stem == resource.name
    assert path_to_file.suffix == f".{file_ext}"

    # A second call to file should not make a new request, since the
    # file should now exist locally
    assert resource.file(file_ext) == path_to_file
    # get_request raises an AssertionError if more than one request
    # has been made to the url
    assert httpx_mock.get_request(url=file_url) == request

    # Trying to get a file type that doesn't exist will raise a ValueError
    with pytest.raises(ValueError):
        resource.file("invalid_file_type")
