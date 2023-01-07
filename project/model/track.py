from typing import List, Set

from google.cloud.firestore_v1 import CollectionReference, DocumentReference
from tekore import NotFound
from tekore._model import FullTrack, FullArtist


class AnalyzedTrack:
    id: str
    name: str
    duration: float
    artist_genres: Set[str]

    def __init__(self,
                 full_track: FullTrack,
                 artists: List[FullArtist]):
        self.id = full_track.id
        self.name = full_track.name
        self.duration = full_track.duration_ms
        self.artist_genres = set([genre for artist in artists
                                  for genre in artist.genres])

    def upsert(self, collection: CollectionReference):
        doc_ref: DocumentReference = collection.document(self.id)
        try:
            doc_ref.update(self.__dict__)
        except:
            doc_ref.set(self.__dict__)

    def __repr__(self):
        return f"AnalyzedTrack(id={self.id}, " \
               + f" name={self.name}, " \
               + f"duration={self.duration}, " \
               + f"artist_genres={self.artist_genres})"


class AnalyzedTracks:
    tracks: List[AnalyzedTrack]

    def __init__(self, tracks: List[FullTrack], artists: List[FullArtist]):
        self.tracks = [
            AnalyzedTrack(track, [artist
                                  for artist in artists
                                  if artist.id in [a.id for a in track.artists]])
            for track in tracks
        ]

    def upsert(self, collection: CollectionReference):
        for track in self.tracks:
            track.upsert(collection)

    def __repr__(self):
        return f"AnalyzedTracks(tracks={self.tracks})"
