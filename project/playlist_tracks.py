import random
from time import sleep
from typing import Union, List

import httpx
from tekore import Spotify, Credentials, RefreshingCredentials
from tekore._model import FullPlaylistTrack, PlaylistTrackPaging


class PlaylistTracks:
    def __init__(self, spotify: Spotify, credentials: Union[Credentials, RefreshingCredentials]):
        self.spotify = spotify
        self.credentials = credentials

    def playlist_tracks(self, playlist_id: str):
        offset = 0
        completed = False

        while not completed:
            try:
                playlist_page: Union[PlaylistTrackPaging, dict] = self.spotify.playlist_items(
                    playlist_id=playlist_id,
                    offset=offset,
                    limit=50
                )
                if len(playlist_page.items) == 0:
                    completed = True
                else:
                    yield [item.track for item in playlist_page.items]
                    completed = False

                offset += 50
            except httpx.HTTPError:
                print('Error while fetching audio analysis.')
                completed = False
                sleep(3)

