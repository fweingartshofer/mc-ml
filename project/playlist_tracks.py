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

    def playlist_tracks(self, playlist_id: str, offset: int = 0):
        completed = False
        limit = 50

        while not completed:
            print('loading playlist', playlist_id, 'offset:', offset)
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

                offset += limit
            except Exception as e:
                print('Error while fetching playlist tracks: ', e)
                completed = False
                sleep(3)

