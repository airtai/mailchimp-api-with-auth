from unittest.mock import MagicMock, call, patch

import pandas as pd

from mailchimp_api.workflow import wf


def test_workflow() -> None:
    ui = MagicMock()
    ui.text_message.return_value = None
    ui.text_input.return_value = "test-list"

    with (
        patch(
            "mailchimp_api.workflow._wait_for_file",
            return_value=pd.DataFrame({"email": ["email1@gmail.com"]}),
        ) as mock_wait_for_file,
        patch("mailchimp_api.workflow.update_tags") as mock_update_tags,
    ):
        mock_update_tags.return_value = (
            {
                "M4": ["a", "b"],
                "M5": ["c", "d", "e"],
                "M3": ["f"],
            },
            {},
        )
        result = wf.run(
            name="mailchimp_chat",
            ui=ui,
        )

        mock_wait_for_file.assert_called_once()
        mock_update_tags.assert_called_once()

        expected_body = """Number of updates per tag:

- **M3**: 1
- **M4**: 2
- **M5**: 3

(It might take some time for updates to reflect in Mailchimp)
"""
        expected_call_args = call(
            sender="Workflow",
            recipient="User",
            body=expected_body,
        )

        assert ui.text_message.call_args_list[1] == expected_call_args

    assert result is not None
