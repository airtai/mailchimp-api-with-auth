import json
from typing import Any, Literal

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Config


class MailchimpService:
    def __init__(self, config: Config) -> None:
        """Initialize the MailchimpService with a configuration.

        Args:
            config (Config): The configuration object containing API details.
        """
        self.config = config

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def _mailchim_request_get(self, url: str) -> dict[str, list[dict[str, str]]]:
        response = requests.get(url, headers=self.config.headers, timeout=10)

        if response.status_code < 200 or response.status_code >= 300:
            # This automatically raises an HTTPError with details
            response.raise_for_status()

        return response.json()  # type: ignore[no-any-return]

    def _mailchimp_request_post(self, url: str, body: dict[str, Any]) -> dict[str, Any]:
        response = requests.post(
            url, headers=self.config.headers, json=body, timeout=10
        )

        # Check if the response is not 200-299
        if response.status_code < 200 or response.status_code >= 300:
            # This automatically raises an HTTPError with details
            response.raise_for_status()

        return response.json()  # type: ignore[no-any-return]

    def get_account_lists(self) -> dict[str, list[dict[str, str]]]:
        """Get information about all lists in the account."""
        url = f"{self.config.base_url}/lists?fields=lists.id,lists.name"

        return self._mailchim_request_get(url)

    def get_members_with_tags(self, list_id: str) -> dict[str, Any]:
        url = f"{self.config.base_url}/lists/{list_id}/members?fields=members.id,members.email_address,members.tags"

        return self._mailchim_request_get(url)

    def get_members(self, list_id: str) -> dict[str, list[dict[str, str]]]:
        url = f"{self.config.base_url}/lists/{list_id}/members?fields=members.email_address,members.id"

        return self._mailchim_request_get(url)

    def get_tags(self, list_id: str, member_id: str) -> dict[str, list[dict[str, str]]]:
        url = f"{self.config.base_url}/lists/{list_id}/members/{member_id}/tags?fields=tags.name"

        return self._mailchim_request_get(url)

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10)
    )
    def _post_batch_update_members_tag(
        self,
        list_id: str,
        member_ids: list[str],
        tag_name: str,
        status: Literal["active", "inactive"],
    ) -> dict[str, str]:
        url = f"{self.config.base_url}/batches"
        body = {
            "operations": [
                {
                    "method": "POST",
                    "path": f"/lists/{list_id}/members/{member_id}/tags",
                    "body": json.dumps(
                        {"tags": [{"name": tag_name, "status": status}]}
                    ),
                }
                for member_id in member_ids
            ]
        }
        return self._mailchimp_request_post(url, body)

    def post_batch_update_members_tag(
        self,
        list_id: str,
        member_ids: list[str],
        tag_name: str,
        status: Literal["active", "inactive"] = "active",
    ) -> dict[str, str]:
        # Split member_ids into chunks of 200
        for i in range(0, len(member_ids), 200):
            self._post_batch_update_members_tag(
                list_id, member_ids[i : i + 200], tag_name, status
            )
        return {"status": "success"}
