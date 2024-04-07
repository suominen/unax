import irc.bot
import argparse
import re
import requests
import signal
from bs4 import BeautifulSoup

class UnaxBot(irc.bot.SingleServerIRCBot):
    def __init__(self, channel, nickname, realname, server, port, debug=False):
        super().__init__([(server, port)], nickname, realname)
        self.channel = channel
        self.debug = debug
        print(f"Starting (debug={debug})")

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
        twitter_regex = re.compile(r'''
            (https?://
              (?:               # List of domains
                twitter\.com
              )
              /\S+              # Username
              /status
              /\d+              # Status ID
            )''', re.IGNORECASE|re.X)
        link_regex = re.compile(r'''
            (https?://(?:www\.)?
              (?: # List of domains
                [-a-z0-9]+\.(?:de|dk|ee|fi|no|se)
                |mastodon\.social
                |threadreaderapp\.com
                |twitter\.com
                |youtu\.be
                |youtube\.com
              )
              /[a-z0-9@#%&+.=/?-]*
            )''', re.IGNORECASE|re.X)

        twitter_links = twitter_regex.findall(message)
        approved_links = link_regex.findall(message)

        for link in twitter_links:
            threadreader_link = self.get_threadreader_link(link)
            if threadreader_link:
                c.privmsg(self.channel, f"See also: {threadreader_link}")

        for link in approved_links:
            link_title = self.get_link_title(link)
            if link_title:
                c.privmsg(self.channel, f"Title: {link_title}")

    def get_threadreader_link(self, tweet_link):
        try:
            response = requests.get(f"https://threadreaderapp.com/thread/{tweet_link.split('/')[-1]}", allow_redirects=False)
            if response.status_code == 200:
                return response.url
            else:
                return None
        except Exception as e:
            print("Error retrieving ThreadReaderApp link:", e)
            return None

    def get_link_title(self, link):
        try:
            response = requests.get(link)
            soup = BeautifulSoup(response.text, 'html.parser')
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.string.strip()
            else:
                return None
        except Exception as e:
            print("Error retrieving link title:", e)
            return None

    def reconnect_bot(self, signum, frame):
        print("Received SIGHUP. Shutting down gracefully.")
        self.disconnect()

    def stop_bot(self, signum, frame):
        print("Received SIGTERM. Shutting down gracefully.")
        self.die()

    def keyboard_interrupt(self):
        print("Received a keyboard interrupt. Shutting down gracefully.")
        self.die()

def parse_arguments():
    parser = argparse.ArgumentParser(description="IRC bot to process Twitter and YouTube links.")
    parser.add_argument("channel", help="IRC channel to join")
    parser.add_argument("nickname", help="Nickname of the bot")
    parser.add_argument("realname", help="Real name of the bot")
    parser.add_argument("server", help="IRC server address")
    parser.add_argument("port", type=int, help="IRC server port")
    parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    bot = UnaxBot(args.channel, args.nickname, args.realname, args.server, args.port, args.debug)

    signal.signal(signal.SIGTERM, bot.stop_bot)
    signal.signal(signal.SIGHUP, bot.reconnect_bot)

    try:
        bot.start()
    except KeyboardInterrupt:
        bot.keyboard_interrupt()
