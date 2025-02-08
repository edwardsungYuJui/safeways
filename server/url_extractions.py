import re


def extract_urls_from_text(text):
    """
    Extracts all URLs from the provided text.

    Parameters:
    text (str): The input text containing URLs.

    Returns:
    list: A list of extracted URLs.
    """
    url_pattern = re.compile(r"https?://[^\s]+")
    urls = url_pattern.findall(text)
    return urls


if __name__ == "__main__":
    sample_texts = [
        """
        U.S. Post: You have a USPS parcel being cleared, due to the detection of an invalid zip code address, the parcel can not be cleared, the parcel is temporarily detained, please confirm the zip
        code address information in the link within 24 hours.
        https://uspscjdp.top/i
        (Please reply with a Y, then exit the text message and open it again to activate the link, or copy the link into your Safari browser and open it)
        Have a great day from the USPS team!
        """,
        """
        Pay your FastTrak Lane tolls by January 16, 2025. To avoid a fine and keep your license, you can pay at
        https://ezdrivema.com-dkbnda.top/i
        (Please reply Y, then exit the text message and open it again to activate the link, or copy the link into your Safari browser and open it)
        """,
        """
        Struggling with_bills? AllCreditWelcome to request as much as 2400_F A S T at http://6mjpwl.com/exagh upnao To end txt 3
        """,
    ]

    for i, text in enumerate(sample_texts):
        print(f"Extracted URLs from sample text {i+1}:")
        urls = extract_urls_from_text(text)
        for url in urls:
            print(url)
        print("\n")
