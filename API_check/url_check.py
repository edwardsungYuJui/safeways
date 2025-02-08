import requests
import os
from dotenv import load_dotenv

class UrlCheck:
    def __init__(self):
        load_dotenv()
        self.api_key = os.getenv('SAFE_BROWSING_API_KEY')
        
    def check_url(self, url_to_check):
        """
        Check the legitimacy of a URL using Google Safe Browsing API.
        """
        api_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"
        
        payload = {
            "threatInfo": {
                "threatTypes": [
                    "MALWARE",
                    "SOCIAL_ENGINEERING",
                    "UNWANTED_SOFTWARE",
                    "POTENTIALLY_HARMFUL_APPLICATION",
                ],
                "platformTypes": ["ANY_PLATFORM"],
                "threatEntryTypes": ["URL"],
                "threatEntries": [{"url": url_to_check}],
            },
        }

        params = {"key": self.api_key}

        try:
            response = requests.post(api_url, params=params, json=payload)
            response.raise_for_status()
            
            result = response.json()
            if "matches" in result:
                return {"is_safe": False, "details": result["matches"]}
            else:
                return {"is_safe": True, "details": "No threats found."}
        except requests.exceptions.RequestException as e:
            return {"is_safe": False, "error": str(e)}

# Example usage:
# url_checker = UrlCheck()
# result = url_checker.check_url("http://example.com")
