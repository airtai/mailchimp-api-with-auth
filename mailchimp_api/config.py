class Config:
    def __init__(self, dc: str, api_key: str):
        """Initialize the Config object.

        Args:
            dc (str): The data center identifier for the Mailchimp API.
            api_key (str): The API key for accessing Mailchimp.
        """
        self.base_url = f"https://{dc}.api.mailchimp.com/3.0"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
        }
