import certifi
import os

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.server_api import ServerApi
import pandas as pd
from typing import List
from typing import Dict


load_dotenv()

mongo_uri = os.environ.get("MONGO_URL")
mongo_certificate = os.environ.get("MONGO_CERTIFICATE")
client = MongoClient(mongo_uri,
                     tls=True,
                     tlsCAFile=certifi.where(),
                     tlsCertificateKeyFile=mongo_certificate,
                     server_api=ServerApi('1'))
db = client['spotifai']

track_collection = db["preprocessed_tracks"]

pitch_symbol = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
tolower = lambda s: s.lower()
flatmap = lambda list_of_lists: [item for l in list_of_lists for item in l]


def tracks(collection: Collection, offset=0, limit=400):
    loading = True
    try:
        while loading:
            print("fetching tracks with offset", offset)
            docs = collection.find({}, allow_disk_use=True)\
                .skip(offset)\
                .limit(limit)
            current_track_data = [doc for doc in docs]
            loading = len(current_track_data) < limit
            yield current_track_data
            offset += limit
    except Exception as e:
        print(e)


def pitch_trans(p):
    pitch_frequency = list()
    for timestamp in p:
        pitch_dict = {"timestamp": float(timestamp)}
        for i in range(0, len(p[timestamp])):
            pitch_dict[pitch_symbol[i]] = p[timestamp][i]
        pitch_frequency.append(pitch_dict)
    return pitch_frequency


def pitches_to_dataframe(p):
    return pd.DataFrame(p).sort_values(by=["timestamp"])


def max_of_pitches(freq: List[Dict[str, float]], pitch: chr):
    return max([item[pitch] for item in freq])


def min_of_pitches(freq: List[Dict[str, float]], pitch: chr):
    return min([item[pitch] for item in freq])


if __name__ == "__main__":
    for tracks in tracks(track_collection):
        df = pd.DataFrame(tracks)
        df.set_index("_id", inplace=True)
        df = df[~df["pitches"].isna()]
        tags = pd.Series(flatmap(df[~df["tags"].isna()]["tags"].values.tolist())).apply(tolower).drop_duplicates()
        pitches = df["pitches"].apply(pitch_trans)
        df["pitches"] = pitches
        for sym in pitch_symbol:
            df.insert(len(df.columns), f"{sym}_max", [max_of_pitches(item, sym) for item in df["pitches"]])
            df.insert(len(df.columns), f"{sym}_min", [min_of_pitches(item, sym) for item in df["pitches"]])
        temp_df = pd.DataFrame()

        for index, row in enumerate(df["pitches"].values):
            song = pitches_to_dataframe(row)
            song["timestamp"] = song["timestamp"].apply(pd.to_timedelta, unit='s')
            resampled: pd.DataFrame = song.set_index("timestamp").resample(
                f"{song.iloc[-1]['timestamp'].total_seconds() * 10 // 1}ms").mean().interpolate()[:100]
            d: pd.DataFrame = pd.DataFrame()
            for col in resampled.columns:
                if col == "timestamp":
                    continue
                d = pd.concat([d, pd.DataFrame({f"{col}_{row_idx}": [val] for row_idx, val in enumerate(resampled[col].values)},
                                               index=[df.index[index]])], axis=1)
            temp_df = pd.concat([temp_df, d])

        df = pd.concat([df, temp_df], axis=1)
        df.drop(columns=["pitches"], inplace=True)  # drop unprocessed pitches
        with open("songs.csv", 'a') as f:
            df.to_csv(f, mode='a', header=f.tell() == 0, index=False)
