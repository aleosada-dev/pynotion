import pytest
from datetime import datetime
from unittest.mock import patch, Mock
from requests import Response
from requests.exceptions import ConnectionError, Timeout, HTTPError
from typing import Any

from pynotion import (
    NotionPageProperty,
    SortDirection,
    build_single_sorter,
    build_update_properties,
    query_notion_database,
    update_notion_page,
    build_equal_filter,
)


@pytest.fixture(scope="module")
def query_response():
    response = Mock(Response)
    response.status_code = 200
    response.json.return_value = {}
    yield response


@pytest.fixture(scope="module")
def api_key():
    yield "test_key"


@pytest.fixture(scope="module")
def database_id():
    yield "test_key"


@pytest.fixture(scope="module")
def notion_version():
    yield "2022-06-28"


@pytest.fixture(scope="module")
def notion_api_version():
    yield "v1"


@pytest.fixture(scope="module")
def page_id():
    yield "f7b7c638-9bdb-4c34-b92d-ef40b58dd7fe"


@pytest.fixture(scope="module")
def notion_api_base_url():
    yield "https://api.notion.com"


@pytest.fixture(scope="module")
def query_database_url(notion_api_base_url, notion_api_version, database_id):
    yield (
        f"{notion_api_base_url}/{notion_api_version}/"
        f"databases/{database_id}/query"
    )


@pytest.fixture(scope="module")
def update_page_url(notion_api_base_url, notion_api_version, page_id):
    yield (f"{notion_api_base_url}/{notion_api_version}/" f"pages/{page_id}")


@pytest.fixture(scope="module")
def headers(api_key, notion_version):
    yield {
        "Authorization": f"Bearer {api_key}",
        "Notion-Version": notion_version,
        "Content-Type": "application/json",
    }


@pytest.fixture
def filter():
    yield {"filter": {"property": "Habit", "rich_text": {"equals": "teste"}}}


@pytest.fixture
def sorter():
    yield {"sorts": [{"property": "Date", "direction": "descending"}]}


@pytest.fixture(scope="module")
def update_one_property():
    yield [NotionPageProperty("name", "value")]


@patch("pynotion.requests.post")
@patch("pynotion.NOTION_VERSION", "2022-06-28")
@patch("pynotion.NOTION_API_BASE_URL", "https://api.notion.com")
@patch("pynotion.NOTION_API_KEY", "test_key")
@patch("pynotion.NOTION_API_VERSION", "v1")
def test_when_success_post_callled_with_right_arguments(
    post_request,
    query_response,
    database_id,
    query_database_url,
    headers,
    filter,
    sorter,
) -> None:
    # Arrange
    post_request.return_value = query_response
    data = filter | sorter

    # Act
    query_notion_database(database_id, filter, sorter)

    # Assert
    post_request.assert_called_once_with(
        query_database_url,
        json=data,
        headers=headers
    )


@patch("pynotion.requests.post")
def test_query_database_success(post_request, database_id):
    # Arrange
    query_response = Response()
    query_response.status_code = 200
    query_response._content = b"{}"
    post_request.return_value = query_response

    # Act
    res = query_notion_database(database_id)

    # Assert
    assert res.json() == {}
    assert res.status_code == 200


@patch("pynotion.requests.post")
@pytest.mark.parametrize("database_id", [(""), (None)])
def test_databaseid_not_empty(post_request, query_response, database_id):
    post_request.return_value = query_response
    with pytest.raises(ValueError):
        query_notion_database(database_id)


@patch("pynotion.requests.post")
def test_query_database_connection_error(post_request, database_id):
    post_request.side_effect = ConnectionError()
    with pytest.raises(ConnectionError):
        query_notion_database(database_id)


@patch("pynotion.requests.post")
def test_query_database_timeout_error(post_request, database_id):
    post_request.side_effect = Timeout()
    with pytest.raises(Timeout):
        query_notion_database(database_id)


@patch("pynotion.requests.post")
@pytest.mark.parametrize("status_code", [(400), (500)])
def test_query_database_http_error(post_request, database_id, status_code):
    query_response = Response()
    query_response.status_code = status_code
    post_request.return_value = query_response

    with pytest.raises(HTTPError):
        query_notion_database(database_id)


def test_build_date_equal_database_filter():
    property_name = "Date"
    date = datetime(2023, 4, 29)

    result = build_equal_filter(property_name, date)

    assert isinstance(result, dict)
    assert result["filter"]["property"] == property_name
    assert result["filter"]["date"]["equals"] == date.date().isoformat()


def test_build_str_equal_database_filter():
    property_name = "Habit"
    value = "No Suggar"

    result = build_equal_filter(property_name, value)

    assert isinstance(result, dict)
    assert result["filter"]["property"] == property_name
    assert result["filter"]["rich_text"]["equals"] == value


@pytest.mark.parametrize("value", [None, "", 0])
def test_build_equal_filter_empty_value(value: Any):
    property_name = "Propertie"

    with pytest.raises(ValueError):
        build_equal_filter(property_name, value)


@pytest.mark.parametrize("property_name", [None, "", 0])
def test_build_equal_filter_empty_property_name(property_name: Any):
    with pytest.raises(ValueError):
        build_equal_filter(property_name, "teste")


@pytest.mark.parametrize(
    "property_name, direction, expected_direction",
    [
        ("Name", SortDirection.ascending, "ascending"),
        ("Name", SortDirection.descending, "descending"),
    ],
)
def test_build_single_sorter(property_name, direction, expected_direction):
    sorter = build_single_sorter(property_name, direction)

    assert sorter["sorts"]
    assert len(sorter["sorts"]) == 1
    assert sorter["sorts"][0]["property"] == property_name
    assert sorter["sorts"][0]["direction"] == expected_direction


@pytest.mark.parametrize("direction", ["", None, 1, 3.3])
def test_build_single_sorter_direction_not_sortdirection(direction):
    with pytest.raises(TypeError):
        build_single_sorter("property", direction)


@pytest.mark.parametrize("property_name", [(0), (None), ("")])
def test_build_single_sorter_value_errors(property_name):
    with pytest.raises(ValueError):
        build_single_sorter(property_name, SortDirection.ascending)


def test_build_update_properties_length_zero():
    with pytest.raises(ValueError):
        build_update_properties([])


def test_build_update_properties_one_propertie():
    property_name = "Streak"
    property_value = 1
    properties = build_update_properties(
        [NotionPageProperty(property_name, property_value)]
    )

    assert isinstance(properties, dict)
    assert properties["properties"][property_name] == property_value


@patch("pynotion.requests.patch")
@patch("pynotion.NOTION_VERSION", "2022-06-28")
@patch("pynotion.NOTION_API_BASE_URL", "https://api.notion.com")
@patch("pynotion.NOTION_API_KEY", "test_key")
@patch("pynotion.NOTION_API_VERSION", "v1")
def test_update_database_page_patch_called_with_right_arguments(
    patch_request, page_id, headers, update_page_url
):
    patch_response = Response()
    patch_response.status_code = 200
    patch_request.return_value = patch_response
    properties = [NotionPageProperty("name", "value")]
    json = build_update_properties(properties)

    update_notion_page(page_id, properties)

    patch_request.assert_called_once_with(
        update_page_url,
        headers=headers,
        json=json
    )


@patch("pynotion.requests.patch")
@patch("pynotion.NOTION_VERSION", "2022-06-28")
@patch("pynotion.NOTION_API_BASE_URL", "https://api.notion.com")
@patch("pynotion.NOTION_API_KEY", "test_key")
@patch("pynotion.NOTION_API_VERSION", "v1")
def test_update_database_page_success(patch_request, page_id):
    patch_response = Response()
    patch_response.status_code = 200
    patch_request.return_value = patch_response
    properties = [NotionPageProperty("name", "value")]

    response = update_notion_page(page_id, properties)

    assert response.status_code == 200


@patch("pynotion.requests.patch")
def test_update_page_connection_error(
    patch_request,
    page_id,
    update_one_property
):
    patch_request.side_effect = ConnectionError()
    with pytest.raises(ConnectionError):
        update_notion_page(page_id, update_one_property)


@patch("pynotion.requests.patch")
def test_update_page_timeout_error(
    patch_request,
    page_id,
    update_one_property
):
    patch_request.side_effect = Timeout()
    with pytest.raises(Timeout):
        update_notion_page(page_id, update_one_property)


@patch("pynotion.requests.patch")
@pytest.mark.parametrize("status_code", [400, 404, 429, 500])
def test_update_page_http_error(
    patch_request, page_id, update_one_property, status_code
):
    query_response = Response()
    query_response.status_code = status_code
    patch_request.return_value = query_response

    with pytest.raises(HTTPError):
        update_notion_page(page_id, update_one_property)
