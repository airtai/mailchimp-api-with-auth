import os
import time
from typing import Any

import pandas as pd
from fastagency import UI
from fastagency.runtimes.autogen import AutoGenWorkflows

from .config import Config
from .constants import UPLOADED_FILES_DIR
from .processing.update_tags import update_tags

wf = AutoGenWorkflows()

FASTAPI_URL = os.getenv("FASTAPI_URL", "http://localhost:8008")


def _get_config() -> Config:
    api_key = os.getenv("MAILCHIMP_API_KEY")
    if not api_key:
        raise ValueError("MAILCHIMP_API_KEY not set")

    config = Config("us14", api_key)
    return config


config = _get_config()


def _wait_for_file(timestamp: str) -> pd.DataFrame:
    file_name = f"uploaded-file-{timestamp}.csv"
    file_path = UPLOADED_FILES_DIR / file_name
    while not file_path.exists():
        time.sleep(2)

    df = pd.read_csv(file_path)
    file_path.unlink()

    return df


@wf.register(name="mailchimp_chat", description="Mailchimp tags update chat")  # type: ignore[misc]
def mailchimp_chat(ui: UI, params: dict[str, Any]) -> str:
    timestamp = time.strftime("%Y-%m-%d-%H-%M-%S")
    body = f"""Please upload **.csv** file with the email addresses for which you want to update the tags.

<a href="{FASTAPI_URL}/upload-file?timestamp={timestamp}" target="_blank">Upload File</a>
"""
    ui.text_message(
        sender="Workflow",
        recipient="User",
        body=body,
    )

    df = _wait_for_file(timestamp)

    list_name = None
    while list_name is None:
        list_name = ui.text_input(
            sender="Workflow",
            recipient="User",
            prompt="Please enter Account Name for which you want to update the tags",
        )

    add_tag_members, _ = update_tags(
        crm_df=df, config=config, list_name=list_name.strip()
    )
    if not add_tag_members:
        return "No tags added"

    add_tag_members = dict(sorted(add_tag_members.items()))
    updates_per_tag = "\n".join(
        [f"- **{key}**: {len(value)}" for key, value in add_tag_members.items()]
    )
    body = f"""Number of updates per tag:

{updates_per_tag}

(It might take some time for updates to reflect in Mailchimp)
"""
    ui.text_message(
        sender="Workflow",
        recipient="User",
        body=body,
    )
    return "Task Completed"
