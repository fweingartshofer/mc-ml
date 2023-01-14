import random
from typing import Union, List

from tekore import Spotify, Credentials, RefreshingCredentials
from tekore._model import FullTrack


class RandomTracks:
    def __init__(self, spotify: Spotify, credentials: Union[Credentials, RefreshingCredentials]):
        self.spotify = spotify
        self.credentials = credentials

    def random_tracks(self) -> List[FullTrack]:
        start_char = random.choice("abcdefghijklmnopqrstuvwxyz")
        tracks: List[FullTrack] = self.spotify.search(query=f"{start_char}%", limit=50)[0].items
        return tracks

