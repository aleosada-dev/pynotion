"""Module that interacts with the notion API"""
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

import os
import requests
import logging

logger = logging.getLogger(__name__)


NOTION_VERSION = "2022-06-28"
NOTION_API_BASE_URL = "https://api.notion.com"
NOTION_API_VERSION = "v1"
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")


@dataclass(frozen=True, slots=True, eq=True)
class NotionPageProperty:
    """Class that represent a Notion page property"""

    name: str
    value: str | int | datetime | float


class SortDirection(Enum):
    "Enum that represents the direction to sort a query"
    ascending = ("ascending",)
    descending = "descending"

    def __str__(self) -> str:
        return super().__str__().split(".")[-1]


def build_single_sorter(
    property_name: str, direction: SortDirection = SortDirection.ascending
) -> dict:
    """Build a sorter object for a single property
    :param property_name: Name of the property to sort
    :param direction: Direction to sort (ascending - default | descending)
    :return: A dictionary formated for sorting a notion database query
    """

    logger.debug(
        f"Starting {build_single_sorter.__name__}",
        {"property_name": property_name, "direction": str(direction)},
    )

    if not isinstance(direction, SortDirection):
        raise TypeError("Direction must be an instance of SortDirection")

    if not property_name:
        raise ValueError("Property name can't be empty")

    direction = direction or SortDirection.ascending

    sorter = {"sorts": []}
    sorter["sorts"].append(
        {
            "property": property_name,
            "direction": str(direction),
        }
    )

    logger.debug(f"Ending {build_single_sorter.__name__}", {"sorter": sorter})
    return sorter


def build_equal_filter(property_name: str, value: Any) -> dict:
    """Build a filter for one property (date or str)
    :param property_name: Name of the property to filter
    :param value: Value of the property to filter
    :return: A dictionary formated for filtering a notion database query
    :raises: ValueError
    """
    # TODO: Fix datetime is not serializable
    # logger.debug(f"Starting {build_equal_filter.__name__}",
    #              {"property_name": property_name, "value": value})
    logger.debug(f"Starting {build_equal_filter.__name__}")

    if not property_name:
        raise ValueError("Property name can't be empty")

    if not value:
        raise ValueError("Value can't be empty")

    filter = {}
    filter["filter"] = {}
    filter["filter"]["property"] = property_name

    if isinstance(value, datetime):
        filter["filter"]["date"] = {}
        filter["filter"]["date"]["equals"] = value.date().isoformat()

    if isinstance(value, str):
        filter["filter"]["rich_text"] = {}
        filter["filter"]["rich_text"]["equals"] = value

    logger.debug(f"Ending {build_equal_filter.__name__}", {"filter": filter})

    return filter


def build_update_properties(properties: list[NotionPageProperty]) -> dict:
    """Build a dictionary from a list o properties to update in a notion
    database page
    :param properties: List of notion page properties to update
    :return: Dictionary formated for patching a notion database page
    :raises: ValueError
    """
    logger.debug(
        f"Starting {build_update_properties.__name__}",
        {"properties": list([{p.name: p.value} for p in properties])},
    )

    if not len(properties):
        raise ValueError("properties can't be empty")

    ret = {}
    ret["properties"] = {}

    for notion_propertie in properties:
        ret["properties"][notion_propertie.name] = notion_propertie.value

    logger.debug(f"Ending {build_update_properties.__name__}", {"return": ret})
    return ret


def _log_headers(headers: dict) -> dict:
    """[internal] Exclude Authorization Header for log
    :param headers: Original dict headers
    :return: Dict headers without Authorization key
    """
    return {key: value for key, value in headers.items() if key != "Authorization"}


def build_headers(api_key: str | None = None) -> dict:
    """Build basic headers for requests with api key
    :return: A dictionary for the headers authorization notion-version
    and content-type
    """
    logger.debug(f"Starting {build_headers.__name__}")

    headers = {
        "Authorization": f"Bearer {api_key or NOTION_API_KEY}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    logger.debug(f"Ending {build_headers.__name__}", {"headers": _log_headers(headers)})

    return headers


def build_url(route: str) -> str:
    """Build a url concatenating notion api base url + api version + a custom
    route
    :return: url encoded for the request

    """
    logger.debug(f"Starting {build_url.__name__}", {"route": route})

    url = "/".join([NOTION_API_BASE_URL, NOTION_API_VERSION, route])

    logger.debug(f"Ending {build_url.__name__}", {"return": url})

    return url


def query_notion_database(
    database_id: str, filter: dict = {}, sorter: dict = {}, api_key: str | None = None
) -> requests.Response:
    """Query a notion database
    :param database_id: Id of notion database
    :result: obj with database pages
    :raises: ConnectionError, Timeout, HTTPError
    """
    logger.debug(
        f"Starting {query_notion_database.__name__}", {"database_id": database_id}
    )

    if not database_id:
        raise ValueError(database_id)

    headers = build_headers(api_key)
    payload = filter | sorter
    databases_api_url = build_url(f"databases/{database_id}/query")

    logger.info(
        f"Calling (POST) {databases_api_url}",
        {"data": payload, "headers": _log_headers(headers)},
    )

    res = requests.post(databases_api_url, json=payload, headers=headers)

    logger.info(f"Status code {res.status_code}", {"status_code": res.status_code})

    res.raise_for_status()

    logger.debug(f"Ending {query_notion_database.__name__}", {"res": res.json()})
    return res


def update_notion_page(
    page_id: str, properties: list[NotionPageProperty], api_key: str | None = None
) -> requests.Response:
    """Update a page entry in notion
    :param page_id: Id of the page to update
    :param properties: A list of properties to update with name e value
    :return: A response object
    :raises: ConnectionError, Timeout, HTTPError
    """

    logger.debug(f"Starting {update_notion_page.__name__}", {"page_id": page_id})

    url = build_url(f"pages/{page_id}")
    payload = build_update_properties(properties)
    headers = build_headers(api_key)

    logger.info(
        f"Calling (PATCH) {url}", {"data": payload, "headers": _log_headers(headers)}
    )

    res = requests.patch(url, json=payload, headers=headers)

    logger.info(f"Status code {res.status_code}", {"status_code": res.status_code})

    res.raise_for_status()

    logger.debug(
        f"Ending {update_notion_page.__name__}",
        {"return": {"status_code": res.status_code}},
    )
    return res
