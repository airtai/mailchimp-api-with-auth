from fastagency.adapters.fastapi import FastAPIAdapter
from fastagency.app import FastAgency
from fastagency.ui.mesop import MesopUI
from fastagency.ui.mesop.auth.basic_auth import BasicAuth

fastapi_url = "http://localhost:8008"

provider = FastAPIAdapter.create_provider(
    fastapi_url=fastapi_url,
)
auth = BasicAuth(
    # bcrypt-hashed passwords. One way to generate bcrypt-hashed passwords
    # is by using online tools such as https://bcrypt.online
    allowed_users={
        "robert@airt.ai": "$2y$10$zmsptxWMVGs8aTPxRiMArO23anNZLxL4l5w71S7yvMpxCG4gJTZWS",  # nosemgrep: generic.secrets.security.detected-bcrypt-hash.detected-bcrypt-hash
    },
)

ui = MesopUI(auth=auth)


app = FastAgency(
    provider=provider,
    ui=ui,
    title="Mailchimp App",
)

# start the provider with the following command
# gunicorn mailchimp_api.deployment.main_2_mesop:app -b 0.0.0.0:8888 --reload
