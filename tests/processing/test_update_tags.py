import os
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from mailchimp_api.config import Config
from mailchimp_api.processing.update_tags import (
    _batch_update_tags,
    _create_add_and_remove_tags_dicts,
    update_tags,
)
from mailchimp_api.services.mailchimp_service import MailchimpService


class TestUpdateTags:
    @pytest.fixture(autouse=True)
    def _setup(self) -> None:
        self.config = Config(dc="us14", api_key="anystring")
        self.mailchimp_service = MailchimpService(config=self.config)
        return

    def _setup_mailchimp_request_method(
        self,
        mock_get: MagicMock,
        json_responses: list[Any],
        status_code: int = 200,
    ) -> None:
        side_effect = []
        for json_response in json_responses:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            mock_response.json.return_value = json_response
            side_effect.append(mock_response)

        mock_get.side_effect = side_effect

    def test_create_add_and_remove_tags_dicts(self) -> None:
        members_with_tags_df = pd.DataFrame(
            {
                "id": ["first_member_id", "second_member_id", "third_member_id"],
                "email_address": [
                    "email1@airt.ai",
                    "email2@airt.ai",
                    "email3@airt.ai",
                ],
                "tags": [
                    [
                        {"id": 1, "name": "Test API Tag"},
                        {"id": 2, "name": "M3"},
                    ],
                    [
                        {"id": 1, "name": "Test API Tag"},
                        {"id": 3, "name": "M1"},
                        {"id": 3, "name": "test-tag"},
                    ],
                    [
                        {"id": 1, "name": "Test API Tag"},
                        {"id": 2, "name": "M2"},
                    ],
                ],
            }
        )

        add_tag_members, remove_tag_members = _create_add_and_remove_tags_dicts(
            members_with_tags_df=members_with_tags_df,
        )
        assert add_tag_members == {
            "M2": ["second_member_id"],
            "M3": ["third_member_id"],
        }
        assert remove_tag_members == {
            "M1": ["second_member_id"],
            "M2": ["third_member_id"],
        }

    @patch("mailchimp_api.processing.update_tags.datetime")
    @patch("mailchimp_api.services.mailchimp_service.requests.post")
    def test_batch_update_tags(
        self, mock_post: MagicMock, mock_datetime: MagicMock
    ) -> None:
        tag_members = {
            "M2": ["third_member_id"],
            "M3": ["third_member_id"],
        }
        mock_post.return_value.status_code = 200
        mock_datetime.now.return_value = datetime(2024, 11, 15, 10, 44, 16, 794923)

        _batch_update_tags(
            mailchimp_service=self.mailchimp_service,
            list_id="list_id",
            tag_members=tag_members,
            status="active",
        )

        assert mock_post.call_count == 4
        for tag in ["M2", "M2 - 15.11.2024.", "M3", "M3 - 15.11.2024."]:
            mock_post.assert_any_call(
                f"{self.config.base_url}/batches",
                headers=self.config.headers,
                json={
                    "operations": [
                        {
                            "method": "POST",
                            "path": "/lists/list_id/members/third_member_id/tags",
                            "body": f'{{"tags": [{{"name": "{tag}", "status": "active"}}]}}',
                        }
                    ]
                },
                timeout=10,
            )

    @patch("mailchimp_api.processing.update_tags.datetime")
    @patch("mailchimp_api.services.mailchimp_service.requests.post")
    @patch("mailchimp_api.services.mailchimp_service.requests.get")
    def test_update_tags(
        self, mock_get: MagicMock, mock_post: MagicMock, mock_datetime: MagicMock
    ) -> None:
        json_responses = [
            {"lists": [{"id": "list_id", "name": "airt"}]},
            {
                "members": [
                    {
                        "id": "first_member_id",
                        "email_address": "email1@airt.ai",
                        "tags": [
                            {"id": 1, "name": "Test API Tag"},
                            {"id": 2, "name": "M3"},
                        ],
                    },
                    {
                        "id": "second_member_id",
                        "email_address": "email2@gmail.com",
                        "tags": [
                            {"id": 1, "name": "Test API Tag"},
                            {"id": 2, "name": "M3"},
                            {"id": 3, "name": "test-tag"},
                        ],
                    },
                    {
                        "id": "third_member_id",
                        "email_address": "email2@airt.ai",
                        "tags": [
                            {"id": 1, "name": "Test API Tag"},
                            {"id": 2, "name": "M2"},
                        ],
                    },
                ]
            },
        ]
        crm_df = pd.DataFrame(
            {
                "email": [
                    "email1@airt.ai",
                    "email2@airt.ai",
                ]
            }
        )
        self._setup_mailchimp_request_method(mock_get, json_responses=json_responses)
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"id": "batch_id"}
        mock_datetime.now.return_value = datetime(2024, 11, 15, 10, 44, 16, 794923)
        add_tag_members, remove_tag_members = update_tags(
            crm_df=crm_df, config=self.config, list_name="airt"
        )

        assert mock_get.call_count == 2
        for url in [
            f"{self.config.base_url}/lists?fields=lists.id,lists.name",
            f"{self.config.base_url}/lists/list_id/members?fields=members.id,members.email_address,members.tags",
        ]:
            mock_get.assert_any_call(
                url,
                headers=self.config.headers,
                timeout=10,
            )

        assert mock_post.call_count == 3
        for status, tag in zip(
            ["active", "active", "inactive"], ["M3", "M3 - 15.11.2024.", "M2"]
        ):
            mock_post.assert_any_call(
                f"{self.config.base_url}/batches",
                headers=self.config.headers,
                json={
                    "operations": [
                        {
                            "method": "POST",
                            "path": "/lists/list_id/members/third_member_id/tags",
                            "body": f'{{"tags": [{{"name": "{tag}", "status": "{status}"}}]}}',
                        }
                    ]
                },
                timeout=10,
            )
        assert add_tag_members == {
            "M3": ["third_member_id"],
        }
        assert remove_tag_members == {
            "M2": ["third_member_id"],
        }

    @pytest.mark.skip(reason="real api call")
    def test_real_update_tags(self) -> None:
        crm_df = pd.DataFrame(
            {
                "email": [
                    "robert.jambrecic@gmail.com",
                    "robert@airt.ai",
                ]
            }
        )
        self.config = Config(dc="us14", api_key=os.getenv("MAILCHIMP_API_KEY"))  # type: ignore[arg-type]
        update_tags(crm_df=crm_df, config=self.config, list_name="airt")
