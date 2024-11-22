from fastagency import FastAgency
from fastagency.ui.mesop import MesopUI

from ..workflow import wf

app = FastAgency(
    provider=wf,
    ui=MesopUI(),
    title="Mailchimp App",
)

# start the fastagency app with the following command
# gunicorn mailchimp_api.local.main_mesop:app
