import logging
import urllib.parse
from typing import Set

from bs4 import BeautifulSoup
import requests
from pylast import LastFMNetwork


class LastFmScraper:
    def __init__(self):
        pass

    def get_tags(self, artist: str, track: str) -> Set[str]:
        artist = urllib.parse.quote(artist)
        track = urllib.parse.quote(track)
        url = f"https://www.last.fm/music/{artist}/_/{track}/+tags"
        r = requests.get(url)
        tags_html = BeautifulSoup(r.content, features="html.parser")
        tag_links = tags_html.find_all("a", href=True)
        return {t.text for t in tag_links if t["href"].startswith("/tag/") and t.text != ""}


class LastFmProxy:
    network: LastFMNetwork
    scraper: LastFmScraper

    def __init__(self, network: LastFMNetwork, scraper: LastFmScraper):
        self.network = network
        self.scraper = scraper

    def get_tags(self, artist: str, track: str) -> Set[str]:
        try:
            tags = self._get_tags_with_network(artist, track)
        except:
            logging.debug(f"Track '{track}' from {artist} not found")
            tags = set()
        scrapped_tags = self.scraper.get_tags(artist, track)
        return tags.union(scrapped_tags)

    def _get_tags_with_network(self, artist: str, track: str) -> Set[str]:
        return {tag.item.name for tag in self.network.get_track(artist, track).get_top_tags()}

    def __getattr__(self, attr):
        dispatcher = getattr(self.network, attr)
        if dispatcher is None:
            logging.warning(f"{attr} does not exist on LastFMNetwork")
            return
        return dispatcher


