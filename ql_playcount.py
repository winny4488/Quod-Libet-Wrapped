#!/usr/bin/env python3
"""
Extract playcount metadata from Quod Libet music player
with yearly folder support and UTF-8 safe filtering.
"""

import os
import pickle
import json
from pathlib import Path
from datetime import datetime
import unicodedata

def get_quodlibet_db_path():
    home = Path.home()
    db_path = home / ".config" / "quodlibet" / "songs"
    if db_path.exists():
        return db_path

    alt_paths = [
        home / ".quodlibet" / "songs",
        home / ".config" / "quodlibet" / "songs",
    ]
    for alt in alt_paths:
        if alt.exists():
            return alt

    return db_path

def patch_quodlibet():
    try:
        import quodlibet.formats._audio
        quodlibet.formats._audio.AudioFile.__setitem__ = lambda self, k, v: dict.__setitem__(self, k, v)
    except ImportError:
        pass

def decode_safe(value):
    """Return a UTF-8 normalized string or None if it's invalid."""
    if value is None:
        return None

    if isinstance(value, list):
        value = value[0] if value else None

    if isinstance(value, bytes):
        try:
            value = value.decode("utf-8")
        except UnicodeDecodeError:
            return None

    if not isinstance(value, str):
        value = str(value)

    # Normalize Unicode; reject strings that still contain invalid sequences
    try:
        value = unicodedata.normalize("NFC", value)
    except Exception:
        return None

    # Reject strings that contain replacement chars �
    if "�" in value:
        return None

    return value

def get_value(song, key):
    if key in song:
        return song[key]
    if key.encode() in song:
        return song[key.encode()]
    return None

def extract_playcounts(db_path, min_playcount=0):
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    patch_quodlibet()

    with open(db_path, "rb") as f:
        songs = pickle.load(f)

    if not isinstance(songs, list):
        raise ValueError("Expected list from Quod Libet DB")

    results = []
    skipped = 0

    for song_data in songs:
        playcount = get_value(song_data, "~#playcount")
        playcount = int(playcount) if playcount is not None else 0

        if playcount < min_playcount:
            continue

        title = decode_safe(get_value(song_data, "title"))
        artist = decode_safe(get_value(song_data, "artist"))
        album = decode_safe(get_value(song_data, "album"))
        filename = decode_safe(get_value(song_data, "~filename"))
        lastplayed = str(get_value(song_data, "~#lastplayed") or "Never")

        # If *any* of these is unreadable, skip the entire entry
        if not all([title, artist, album, filename]):
            skipped += 1
            continue

        results.append({
            "file": filename,
            "playcount": playcount,
            "title": title,
            "artist": artist,
            "album": album,
            "lastplayed": lastplayed,
        })

    print(f"Skipped {skipped} songs due to malformed metadata", file=__import__("sys").stderr)
    results.sort(key=lambda x: x["playcount"], reverse=True)
    return results

def save_json_yearly(results, output_file=None):
    year = str(datetime.now().year)
    base = Path("playcounts") / year
    base.mkdir(parents=True, exist_ok=True)

    if output_file is None:
        output_file = base / "playcounts.json"
    else:
        output_file = base / output_file

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Saved: {output_file}", file=__import__("sys").stderr)

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", help="Output file name (inside yearly folder)")
    parser.add_argument("-m", "--min-playcount", type=int, default=0)
    parser.add_argument("-d", "--database", help="Custom database path")
    args = parser.parse_args()

    db_path = Path(args.database) if args.database else get_quodlibet_db_path()

    print(f"Reading DB at: {db_path}", file=__import__("sys").stderr)
    results = extract_playcounts(db_path, args.min_playcount)
    save_json_yearly(results, args.output)

if __name__ == "__main__":
    main()
