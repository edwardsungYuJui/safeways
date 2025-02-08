import email
import requests
import os
from dotenv import load_dotenv


class EmailCheck:

    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv("EMAIL_API_KEY")

    def check_email(self, email=None):
        # STUB FOR TESTING
        # return 0.88
        # if not email:
        #     return 0.88
        url = f"https://emailvalidation.abstractapi.com/v1/?api_key={self.api_key}&email={email}"
        response = requests.get(url)
        return float(response.json()["quality_score"])
