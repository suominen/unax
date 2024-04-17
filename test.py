import argparse
import requests
from bs4 import BeautifulSoup

def main(url):
    user_agent = {"User-agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=user_agent)
    except Exception as e:
        print("Error retrieving link title:", e)

    if not response.status_code == 200:
        print(f"{response.status_code} from {link}")
        return None

    #soup = BeautifulSoup(response.text, "lxml")
    soup = BeautifulSoup(response.text, "html.parser")
    #soup = BeautifulSoup(response.text, "html5lib")

    if not soup.title:
        return None

    return soup.title.text.strip()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch web page title.")
    parser.add_argument("link", help="Link URL")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    link_title = main(args.link)
    if link_title:
        print(f"Title: {link_title}")
