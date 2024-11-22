from collections import defaultdict
from datetime import datetime
from typing import Literal

import pandas as pd

from ..config import Config
from ..services.mailchimp_service import MailchimpService

next_tag_map = {
    "M1": "M2",
    "M2": "M3",
    "M3": None,
}


def _create_add_and_remove_tags_dicts(
    members_with_tags_df: pd.DataFrame,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    # keys are tags, values are list of member ids
    add_tag_members = defaultdict(list)
    remove_tag_members = defaultdict(list)

    for _, row in members_with_tags_df.iterrows():
        member_id = row["id"]
        tags = row["tags"]
        for tag in tags:
            tag_name = tag["name"]
            if tag_name not in next_tag_map:
                continue

            next_tag = next_tag_map[tag_name]
            if next_tag is None:
                continue

            add_tag_members[next_tag].append(member_id)
            remove_tag_members[tag_name].append(member_id)

    return add_tag_members, remove_tag_members


def _batch_update_tags(
    mailchimp_service: MailchimpService,
    list_id: str,
    tag_members: dict[str, list[str]],
    status: Literal["active", "inactive"],
) -> None:
    for tag_name, member_ids in tag_members.items():
        mailchimp_service.post_batch_update_members_tag(
            list_id=list_id,
            member_ids=member_ids,
            tag_name=tag_name,
            status=status,
        )
        if status == "active":
            # Add additional tag with the current date
            tag_name_with_date = f"{tag_name} - {datetime.now().strftime('%d.%m.%Y.')}"
            mailchimp_service.post_batch_update_members_tag(
                list_id=list_id,
                member_ids=member_ids,
                tag_name=tag_name_with_date,
                status=status,
            )


def _add_and_remove_tags(
    mailchimp_service: MailchimpService,
    list_id: str,
    members_with_tags_df: pd.DataFrame,
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    add_tag_members, remove_tag_members = _create_add_and_remove_tags_dicts(
        members_with_tags_df=members_with_tags_df,
    )

    _batch_update_tags(
        mailchimp_service=mailchimp_service,
        list_id=list_id,
        tag_members=add_tag_members,
        status="active",
    )

    _batch_update_tags(
        mailchimp_service=mailchimp_service,
        list_id=list_id,
        tag_members=remove_tag_members,
        status="inactive",
    )

    return add_tag_members, remove_tag_members


def update_tags(
    crm_df: pd.DataFrame, config: Config, list_name: str
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Update tags for members in the CRM."""
    # Create a Mailchimp service
    mailchimp_service = MailchimpService(config)

    # Get the list ID for the list name
    account_lists = mailchimp_service.get_account_lists()
    list_id = None
    for account_list in account_lists["lists"]:
        if account_list["name"] == list_name:
            list_id = account_list["id"]

    if list_id is None:
        raise ValueError(f"List {list_name} not found in account lists.")

    # Get the members with tags
    members_with_tags = mailchimp_service.get_members_with_tags(list_id)

    members_with_tags_df = pd.DataFrame(members_with_tags["members"])
    members_with_tags_df.rename(columns={"email_address": "email"}, inplace=True)

    # filter only emails that are in the CRM
    crm_emails = crm_df["email"].unique()
    members_with_tags_df = members_with_tags_df[
        members_with_tags_df["email"].isin(crm_emails)
    ]

    add_tag_members, remove_tag_members = _add_and_remove_tags(
        mailchimp_service=mailchimp_service,
        list_id=list_id,
        members_with_tags_df=members_with_tags_df,
    )

    return add_tag_members, remove_tag_members
