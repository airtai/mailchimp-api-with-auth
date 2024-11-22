from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from mailchimp_api.config import Config
from mailchimp_api.services.mailchimp_service import MailchimpService


class TestMailchimpService:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.config = Config(dc="us14", api_key="anystring")
        self.mailchimp_service = MailchimpService(config=self.config)
        return

    def _setup_mailchimp_request_method(
        self,
        mock_get: MagicMock,
        status_code: int = 200,
        json_response: Optional[dict[str, str]] = None,
    ) -> None:
        if json_response is None:
            json_response = {"status": "success"}
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = json_response
        mock_get.return_value = mock_response

    @patch("mailchimp_api.services.mailchimp_service.requests.get")
    def test_mailchimp_request_get(self, mock_get: MagicMock) -> None:
        self._setup_mailchimp_request_method(mock_get)
        self.mailchimp_service._mailchim_request_get(url="http://test123.com")

        mock_get.assert_called_once_with(
            "http://test123.com",
            headers=self.config.headers,
            timeout=10,
        )

    @patch("mailchimp_api.services.mailchimp_service.requests.get")
    def test_get_account_lists(self, mock_get: MagicMock) -> None:
        self._setup_mailchimp_request_method(mock_get)
        self.mailchimp_service.get_account_lists()

        mock_get.assert_called_once_with(
            f"{self.config.base_url}/lists?fields=lists.id,lists.name",
            headers=self.config.headers,
            timeout=10,
        )

    @patch("mailchimp_api.services.mailchimp_service.requests.get")
    def test_get_account_lists_with_error(self, mock_get: MagicMock) -> None:
        mock_get.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            MagicMock(status_code=200, json=lambda: {"status": "success"}),
        ]
        self.mailchimp_service.get_account_lists()
        assert mock_get.call_count == 3

    @patch("mailchimp_api.services.mailchimp_service.requests.get")
    def test_get_members(self, mock_get: MagicMock) -> None:
        self._setup_mailchimp_request_method(mock_get)
        self.mailchimp_service.get_members(list_id="123")

        mock_get.assert_called_once_with(
            f"{self.config.base_url}/lists/123/members?fields=members.email_address,members.id",
            headers=self.config.headers,
            timeout=10,
        )

    @patch("mailchimp_api.services.mailchimp_service.requests.get")
    def test_get_tags(self, mock_get: MagicMock) -> None:
        self._setup_mailchimp_request_method(mock_get)
        self.mailchimp_service.get_tags(list_id="123", member_id="456")

        mock_get.assert_called_once_with(
            f"{self.config.base_url}/lists/123/members/456/tags?fields=tags.name",
            headers=self.config.headers,
            timeout=10,
        )

    @patch("mailchimp_api.services.mailchimp_service.requests.post")
    def test_post_batch_update_members_tag_inner(self, mock_post: MagicMock) -> None:
        self._setup_mailchimp_request_method(mock_post)
        self.mailchimp_service._post_batch_update_members_tag(
            list_id="123",
            member_ids=["456", "789"],
            tag_name="tag1",
            status="active",
        )

        mock_post.assert_called_once_with(
            f"{self.config.base_url}/batches",
            headers=self.config.headers,
            json={
                "operations": [
                    {
                        "method": "POST",
                        "path": "/lists/123/members/456/tags",
                        "body": '{"tags": [{"name": "tag1", "status": "active"}]}',
                    },
                    {
                        "method": "POST",
                        "path": "/lists/123/members/789/tags",
                        "body": '{"tags": [{"name": "tag1", "status": "active"}]}',
                    },
                ]
            },
            timeout=10,
        )

    @patch("mailchimp_api.services.mailchimp_service.requests.post")
    def test_post_batch_update_members_tag(self, mock_post: MagicMock) -> None:
        self._setup_mailchimp_request_method(mock_post)
        # i need 500 member ids
        member_ids = [str(i) for i in range(500)]
        self.mailchimp_service.post_batch_update_members_tag(
            list_id="123",
            member_ids=member_ids,
            tag_name="tag1",
        )

        # mock should be called 3 times
        assert mock_post.call_count == 3
        for i in range(0, 500, 200):
            mock_post.assert_any_call(
                f"{self.config.base_url}/batches",
                headers=self.config.headers,
                json={
                    "operations": [
                        {
                            "method": "POST",
                            "path": f"/lists/123/members/{member_id}/tags",
                            "body": '{"tags": [{"name": "tag1", "status": "active"}]}',
                        }
                        for member_id in member_ids[i : i + 200]
                    ]
                },
                timeout=10,
            )
