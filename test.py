import argparse
import requests
from bs4 import BeautifulSoup


def get_soup(url):
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

    return soup


def parse_arguments():
    parser = argparse.ArgumentParser(description="Fetch web page title.")
    parser.add_argument("link", help="Link URL")
    return parser.parse_args()


def main(url):
    soup = get_soup(url)
    if not soup:
        return None

    if soup.title:
        link_title = soup.title.text.strip()
        if link_title:
            print(f"Title: {link_title}")

    meta_tag = soup.find("meta", property="og:description")
    if meta_tag:
        content = meta_tag["content"].strip()
        nl = content.find('\n')
        if nl > 0:
            print(content[:nl])
        else:
            print(content)

    #print(soup)


if __name__ == "__main__":
    args = parse_arguments()
    main(args.link)
