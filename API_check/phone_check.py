import requests
import os
from dotenv import load_dotenv


class PhoneCheck:
    def __init__(self):
        load_dotenv()
        self.api_key_numverify = os.getenv("NUMVERIFY_PHONE_API_KEY")
        self.api_key_abstract = os.getenv("ABSTRACT_PHONE_API_KEY")
        self.api_key_trestle = os.getenv("TRESTLE_PHONE_API_KEY")

    def check_phone(self, phone_number=None):
        if not phone_number:
            return 0.0
        # Numverify API
        numverify_url = (
            f"https://apilayer.net/api/validate?access_key={self.api_key_numverify}"
        )
        query_numverify = {"number": phone_number}

        # Trestle API
        trestle_url = "https://api.trestleiq.com/3.2/phone"
        query_trestle = {"phone": phone_number}
        headers_trestle = {"x-api-key": self.api_key_trestle}

        # Abstract API
        abstract_url = f"https://phonevalidation.abstractapi.com/v1/?api_key={self.api_key_abstract}&phone={phone_number}"

        response_numverify = requests.get(numverify_url, params=query_numverify)
        response_trestle = requests.get(
            trestle_url, params=query_trestle, headers=headers_trestle
        )
        response_abstract = requests.request("GET", abstract_url)

        # Calculate the score
        score = 0
        if response_numverify.json()["valid"]:
            score += 1
        if response_trestle.json()["is_valid"]:
            score += 1
        if response_abstract.json()["valid"]:
            score += 1
        return score / 3


# Example usage:
# phone_checker = PhoneCheck()
# score = phone_checker.check_phone("14158586273")
# print(score)
