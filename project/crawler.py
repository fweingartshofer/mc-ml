import tekore as tk
from dotenv import load_dotenv
import httpx
from os import environ as env
import json

from google.cloud.firestore_v1 import Client
from tekore import Spotify, Credentials

from authentication.spotify_server import SpotifyServer
from typing import List
from project.random_track import RandomTrack
from project.util import Partition
import pylast
from authentication.lastfm_credentials import LastFmCredentials
from lastfm import LastFmScraper, LastFmProxy
import track as model
from project.track import TaggedTrack
from time import sleep
import firebase_admin
from firebase_admin import firestore


class Crawler:
    _host: str
    _port: int
    _spotify: Spotify
    _lastfm: LastFmProxy
    _conf: tuple
    _cred: Credentials

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port

        load_dotenv()

        conf = tk.config_from_environment()
        self._cred = tk.Credentials(*conf)

        creds = LastFmCredentials()

        self._spotify = tk.Spotify()
        last_network = pylast.LastFMNetwork(
            api_key=creds.api_key,
            api_secret=creds.shared_secret,
        )

        self._lastfm = LastFmProxy(last_network, LastFmScraper())
        firebase_admin.initialize_app()

        self._set_spotify_credentials()
        self._store_spotify_credentials()

    def collect_tracks(self, amount: int):
        self._spotify.token = self._cred.refresh(self._spotify.token)
        tracks = self._retrieve_random_tracks()
        artists = self._retrieve_artists(tracks)

        for i in range(0, amount // 50):
            analyzed_tracks = model.AnalyzedTracks(tracks, artists)
            self._retrieve_tags(analyzed_tracks.tracks)
            self._enrich_tracks(analyzed_tracks.tracks)

            client: Client = firestore.client()
            analyzed_tracks.upsert(client.collection("tracks"))

    def _set_spotify_credentials(self):
        try:
            with open(".spotify_credentials.json", "r") as infile:
                token_dict = json.load(infile)
                token_dict["scope"] = " ".join(token_dict["scope"])
                self._spotify.token = tk.Token(token_dict, token_dict["uses_pkce"])
                self._spotify.token = self._cred.refresh(self._spotify.token)
        except Exception as e:
            print(e)
            app = SpotifyServer(self._host, self._port, self._spotify, self._cred)
            self._spotify.token = app.spawn_single_use_server()

    def _store_spotify_credentials(self):
        token: tk.Token = self._spotify.token
        scopes: List[str] = list(token.scope)
        token_dict = {
            "token_type": token.token_type,
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "scope": scopes[0].replace("[", "").replace("]", "").replace("'", "").split(", ") if len(
                scopes) == 0 else scopes,
            "expires_at": token.expires_at,
            "uses_pkce": token.uses_pkce,
            "expires_in": 0
        }
        json_object = json.dumps(token_dict, indent=4)
        with open(".spotify_credentials.json", "w") as outfile:
            outfile.write(json_object)

    def _retrieve_random_tracks(self):
        random_track = RandomTrack(self._spotify, self._cred)
        return random_track.random_tracks()

    def _retrieve_artists(self, tracks):
        artist_ids = [artist.id for track in tracks for artist in track.artists]
        artist_id_partitions = Partition(artist_ids)
        artists = [self._spotify.artists(ids) for ids in artist_id_partitions]
        artists = list(artist for partition in artists for artist in partition)
        return artists

    def _retrieve_tags(self, tracks):
        for track in tracks:
            try:
                tags = TaggedTrack(self._lastfm, track.name, track.artist_names).tags()
                if len(tags) == 0:
                    raise Exception("No tags")
            except Exception as e:
                print(e, track.id, track.name, track.artist_names)
                continue
            track.tags = tags

    def _enrich_tracks(self, tracks):
        track_ids = [track.id for track in tracks]
        track_id_partitions = Partition(track_ids)
        features = [self._spotify.tracks_audio_features(ids) for ids in track_id_partitions]
        features = [feature for partition in features for feature in partition]

        for track in tracks:
            successful = False
            analysis = None
            while not successful:
                try:
                    analysis = self._spotify.track_audio_analysis(track_id=track.id)
                    successful = True
                except httpx.HTTPError:
                    print('Error while fetching audio analysis.')
                    successful = False
                    sleep(3)

            feature = [feature for feature in features if feature.id == track.id][0]
            track.acousticness = feature.acousticness
            track.pitches = {str(segment.start): [p for p in segment.pitches] for segment in analysis.segments}
            track.loudness = feature.loudness
            track.energy = feature.energy
            track.danceability = feature.danceability
            track.mode = feature.mode
            track.instrumentalness = feature.instrumentalness
            track.key = feature.key
            track.liveness = feature.liveness
            track.tempo = feature.tempo
            track.time_signature = feature.time_signature
            track.valence = feature.valence
