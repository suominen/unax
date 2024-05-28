import irc.bot
import argparse
import re
import requests
import signal
from bs4 import BeautifulSoup

class UnaxBot(irc.bot.SingleServerIRCBot):


    def __init__(self, channel, nickname, realname, server, port, debug=False):
        print(f"Starting (debug={debug})")
        self.channel = channel
        self.debug = debug
        self.refresh = True
        super().__init__([(server, port)], nickname, realname)


    def on_welcome(self, c, e):
        c.join(self.channel)


    def on_privmsg(self, c, e):
        message = e.arguments[0]
        sender = e.source.nick
        target = e.target

        if self.debug:
            print(f"Private message from {sender} to {e.target}: {message}")

        #if sender in self.channels[self.channel].users():
        #    self.process_links(c, message)


    def on_pubmsg(self, c, e):
        message = e.arguments[0]
        sender = e.source.nick
        target = e.target.lower()

        if self.debug:
            print(f"Public message from {sender} to {e.target}: {message}")

        if target == self.channel.lower():
            self.process_links(c, message)


    def process_links(self, c, message):
        if self.refresh:
            print("Refreshing domain lists")
            self.read_domain_files()

        bsky_regex = re.compile(
          r"(https?://(?:"
          + self.bsky_domains
          + r")/\S+)",
          re.IGNORECASE
        )
        if self.debug:
            print(f"Bluesky regex: {bsky_regex.pattern}")

        twitter_regex = re.compile(
          r"(https?://(?:"
          + self.twitter_domains
          + r")/\S+/status/\d+)",
          re.IGNORECASE
        )
        if self.debug:
            print(f"Twitter regex: {twitter_regex.pattern}")

        link_regex = re.compile(
          r"(https?://(?:www\.)?(?:"
          + self.link_domains
          + r")/[a-z0-9@#%&+.=/?-]*)",
          re.IGNORECASE
        )
        if self.debug:
            print(f"Link regex: {link_regex.pattern}")

        bsky_links = bsky_regex.findall(message)
        twitter_links = twitter_regex.findall(message)
        approved_links = link_regex.findall(message)

        for link in bsky_links:
            content = self.get_bsky_description(link)
            if content:
                c.privmsg(self.channel, f">>> {content}")

        for link in twitter_links:
            threadreader_link = self.get_threadreader_link(link)
            if threadreader_link:
                c.privmsg(self.channel, f"See also: {threadreader_link}")
                link_title = self.get_link_title(threadreader_link)
                if link_title:
                    c.privmsg(self.channel, f"Title: {link_title}")

        for link in approved_links:
            link_title = self.get_link_title(link)
            if link_title:
                c.privmsg(self.channel, f"Title: {link_title}")


    def get_bsky_description(self, link):
        user_agent = {"User-agent": "Mozilla/5.0"}
        try:
            response = requests.get(link, headers=user_agent)
        except Exception as e:
            print("Error retrieving link title:", e)
            return None

        if not response.status_code == 200:
            print(f"{response.status_code} from {link}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        if not soup:
            return None

        meta_tag = soup.find("meta", property="og:description")
        if not meta_tag:
            return None

        content = meta_tag["content"].strip()
        nl = content.find('\n')
        if nl > 0:
            return content[:nl]

        return content


    def get_threadreader_link(self, link):
        try:
            response = requests.get(
              f"https://threadreaderapp.com/thread/{link.split('/')[-1]}",
              allow_redirects=False
            )
        except Exception as e:
            print("Error retrieving ThreadReaderApp link:", e)
            return None

        if not response.status_code == 200:
            return None

        return response.url


    def get_link_title(self, link):
        user_agent = {"User-agent": "Mozilla/5.0"}
        try:
            response = requests.get(link, headers=user_agent)
        except Exception as e:
            print("Error retrieving link title:", e)
            return None

        if not response.status_code == 200:
            print(f"{response.status_code} from {link}")
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        if not soup.title:
            return None

        return soup.title.text.strip()


    def read_domain_files(self):
        bsky_domain_file = open("domains-bsky.txt", "r")
        bsky_domains = bsky_domain_file.read().splitlines()
        bsky_domain_file.close()
        self.bsky_domains = "|".join(bsky_domains)

        twitter_domain_file = open("domains-twitter.txt", "r")
        twitter_domains = twitter_domain_file.read().splitlines()
        twitter_domain_file.close()
        self.twitter_domains = "|".join(twitter_domains)

        link_domain_file = open("domains-links.txt", "r")
        link_domains = link_domain_file.read().splitlines()
        link_domain_file.close()
        self.link_domains = "|".join(link_domains)

        self.refresh = False


    def refresh_bot(self, signum, frame):
        sig = signal.Signals(signum).name
        print(f"Received {sig}. Requesting refresh.")
        self.refresh = True


    def reconnect_bot(self, signum, frame):
        sig = signal.Signals(signum).name
        print(f"Received {sig}. Reconnecting.")
        self.disconnect()


    def stop_bot(self, signum, frame):
        sig = signal.Signals(signum).name
        print(f"Received {sig}. Shutting down gracefully.")
        self.die()


    def keyboard_interrupt(self):
        print("Received a keyboard interrupt. Shutting down gracefully.")
        self.die()


def parse_arguments():
    parser = argparse.ArgumentParser(description="IRC bot to process weblinks.")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("channel", help="IRC channel to join")
    parser.add_argument("nickname", help="Nickname of the bot")
    parser.add_argument("realname", help="Real name of the bot")
    parser.add_argument("server", help="IRC server address")
    parser.add_argument("port", type=int, nargs="?", default=6667, help="IRC server port")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    bot = UnaxBot(args.channel, args.nickname, args.realname, args.server, args.port, args.debug)

    signal.signal(signal.SIGTERM, bot.stop_bot)
    signal.signal(signal.SIGHUP,  bot.stop_bot)
    signal.signal(signal.SIGUSR1, bot.refresh_bot)
    signal.signal(signal.SIGUSR2, bot.reconnect_bot)

    try:
        bot.start()
    except KeyboardInterrupt:
        bot.keyboard_interrupt()
