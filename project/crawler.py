import os

import certifi
import tekore as tk
from dotenv import load_dotenv
import httpx
import json

from pymongo.collection import Collection
from tekore import Spotify, Credentials, NotFound, TooManyRequests

from authentication.spotify_server import SpotifyServer
from typing import List

from project.playlist_tracks import PlaylistTracks
from project.random_tracks import RandomTracks
from project.util import Partition
import pylast
from authentication.lastfm_credentials import LastFmCredentials
from lastfm import LastFmScraper, LastFmProxy
import track as model
from project.track import TaggedTrack
from time import sleep
from pymongo.server_api import ServerApi
from pymongo import MongoClient


def refresh_token(func):
    """
    Decorator that refreshes the spotify token
    """

    def wrap(*args, **kwargs):
        self: Crawler = args[0]
        token: tk.Token = self._spotify.token
        if token.is_expiring:
            self._spotify.token = self._cred.refresh(self._spotify.token)
            print("refreshing spotify credentials at", func.__name__)
        result = func(*args, **kwargs)
        return result

    return wrap


class Crawler:
    _host: str
    _port: int
    _spotify: Spotify
    _lastfm: LastFmProxy
    _conf: tuple
    _cred: Credentials
    _track_collection: Collection

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

        self._lastfm = LastFmProxy(last_network, LastFmScraper(), scraper_only=True)

        self._set_spotify_credentials()
        self._store_spotify_credentials()
        mongo_uri = os.environ.get("MONGO_URL")
        mongo_certificate = os.environ.get("MONGO_CERTIFICATE")
        client = MongoClient(mongo_uri,
                             tls=True,
                             tlsCAFile=certifi.where(),
                             tlsCertificateKeyFile=mongo_certificate,
                             server_api=ServerApi('1'))
        db = client['spotifai']
        self._track_collection = db['tracks']

    def collect_tracks_from_playlist(self, playlist_id: str, offset: int = 0):
        self._spotify.token = self._cred.refresh(self._spotify.token)
        track_generator = self._retrieve_playlist_tracks(playlist_id, offset)

        for tracks in track_generator:
            analyzed_tracks = self._analyze_tracks(tracks)
            self._save_tracks(analyzed_tracks)

    def collect_random_tracks(self):
        tracks = self._retrieve_random_tracks()
        analyzed_tracks = self._analyze_tracks(tracks)
        self._save_tracks(analyzed_tracks)

    def _save_tracks(self, analyzed_tracks):
        print("Saving tracks ...")
        analyzed_tracks.upsert(self._track_collection)

    def _analyze_tracks(self, tracks) -> model.AnalyzedTracks:
        print("Analyzing", len(tracks), "tracks ...")
        artists = self._retrieve_artists(tracks)

        analyzed_tracks = model.AnalyzedTracks(tracks, artists)
        self._retrieve_tags(analyzed_tracks.tracks)
        self._enrich_tracks(analyzed_tracks.tracks)

        return analyzed_tracks

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
        random_tracks = RandomTracks(self._spotify, self._cred)
        return random_tracks.random_tracks()

    def _retrieve_artists(self, tracks):
        artist_ids = [artist.id for track in tracks for artist in track.artists]
        artist_id_partitions = Partition(artist_ids)
        pending = True
        while pending:
            try:
                artists = [self._spotify.artists(ids) for ids in artist_id_partitions]
                pending = False
            except tk.ServerError as se:
                print("Error retrieving artists:", se)
                pending = True
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

    @refresh_token
    def _enrich_tracks(self, tracks):
        track_ids = [track.id for track in tracks]
        track_id_partitions = Partition(track_ids)
        features = [self._spotify.tracks_audio_features(ids) for ids in track_id_partitions]
        features = [feature for partition in features for feature in partition]

        for track in tracks:
            successful = False
            analysis = None
            retries_404 = 0
            while not successful:
                try:
                    analysis = self._spotify.track_audio_analysis(track_id=track.id)
                    successful = True
                except httpx.HTTPError:
                    print("Retry of audio analysis for track", track.id, "necessary.")
                    successful = False
                    sleep(4)
                except NotFound as nf:
                    if retries_404 >= 5:
                        successful = True
                        print("Track", track.id, "does not have audio analysis:", nf)
                    else:
                        retries_404 += 1
                        print("Could not find analysis for", track.id, "trying again: ", retries_404, "/5")
                except TooManyRequests:
                    print("Too many requests, waiting 30s...")
                    sleep(30)
            if analysis is None:
                continue
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

    @refresh_token
    def _retrieve_playlist_tracks(self, playlist_id: str, offset: int):
        playlist_tracks = PlaylistTracks(self._spotify, self._cred)
        return playlist_tracks.playlist_tracks(playlist_id, offset)


if __name__ == "__main__":
    crawler = Crawler("127.0.0.1", 5000)
    crawler.collect_tracks_from_playlist("69fEt9DN5r4JQATi52sRtq")
