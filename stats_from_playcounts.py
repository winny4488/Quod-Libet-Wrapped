#!/usr/bin/env python3
"""
stats_from_playcounts.py

Compute "this year's" statistics from a Quod Libet playcounts snapshot by
subtracting the previous year's snapshot (if present). This produces a
Spotify-Wrapped-like per-year summary.

Behavior summary:
- If a previous-year file exists (auto-detected or passed via --previous),
  the script computes per-song delta = max(0, current - previous). All
  top lists/aggregations use that delta (so they reflect plays that happened
  during the year).
- Negative deltas (previous > current) are treated as 0 (interpreted as "no
  plays counted this year" — DB resets or metadata removals would otherwise
  create confusing negative counts).
- If no previous file is found, the script treats the entire current snapshot
  as the year's plays (useful for the first year).

Output:
- JSON file with summary statistics, lists, and metadata.

Future expansion:
- If you extract "genre" in ql_playcount.py later, add genre aggregation to
  the "by_genre" section — keep the same pattern (aggregate deltas per genre).
"""

from pathlib import Path
import json
from collections import Counter, defaultdict
import argparse
import re
from typing import Dict, Any

def load_playcounts(path: Path) -> Dict[str, Dict[str, Any]]:
    """Load playcounts JSON and return a mapping keyed by unique file path.
    Each value is the original song dict (must contain keys: file, playcount, title, artist, album).
    """
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    mapping = {}
    for item in data:
        key = item.get("file") or f"{item.get('artist','Unknown')} - {item.get('title','Unknown')}"
        # Coerce types & defaults
        mapping[key] = {
            "file": item.get("file", key),
            "title": item.get("title", "Unknown"),
            "artist": item.get("artist", "Unknown"),
            "album": item.get("album", "Unknown"),
            "playcount": int(item.get("playcount", 0)),
            # keep raw item for any future fields (genre, etc)
            "_raw": item,
        }
    return mapping

def detect_previous_path_from_current(current_path: Path) -> Path:
    """
    Try to find a previous-year playcounts file based on current_path.
    Strategy:
      - Look for a 4-digit year directory in the current path (e.g., playcounts/2025/playcounts.json).
      - If found, construct sibling path with year-1 (playcounts/2024/playcounts.json).
      - If not found, return None.
    """
    # search parents for a folder named YYYY
    year = None
    for p in reversed(current_path.parents):
        if re.fullmatch(r"\d{4}", p.name):
            year = int(p.name)
            parent_dir = p.parent
            filename = current_path.name
            prev_dir = parent_dir / str(year - 1)
            return (prev_dir / filename)
    # nothing found
    return None

def compute_deltas(current_map, prev_map):
    """Return a dict of keys -> {curr, prev, delta} with delta = max(0, curr - prev)."""
    all_keys = set(current_map.keys()) | set(prev_map.keys())
    deltas = {}
    for k in all_keys:
        curr = current_map.get(k, {"playcount": 0})
        prev = prev_map.get(k, {"playcount": 0})
        curr_count = int(curr.get("playcount", 0))
        prev_count = int(prev.get("playcount", 0))
        delta = curr_count - prev_count
        if delta < 0:
            # handle DB resets / removals gracefully by treating negative as 0
            delta = 0
        deltas[k] = {
            "file": curr.get("file") or prev.get("file"),
            "title": curr.get("title") or prev.get("title"),
            "artist": curr.get("artist") or prev.get("artist"),
            "album": curr.get("album") or prev.get("album"),
            "current_playcount": curr_count,
            "previous_playcount": prev_count,
            "delta": delta
        }
    return deltas

def aggregate_stats(deltas):
    """Aggregate artist/album totals and compute top lists based on per-song deltas."""
    total_play_deltas = 0
    tracks_with_plays = 0

    by_artist = Counter()
    by_album = Counter()
    top_songs = []

    for k, v in deltas.items():
        d = v["delta"]
        total_play_deltas += d
        if d > 0:
            tracks_with_plays += 1
            by_artist[v["artist"]] += d
            by_album[v["album"]] += d
            top_songs.append({
                "title": v["title"],
                "artist": v["artist"],
                "album": v["album"],
                "plays": d,
                "file": v["file"]
            })

    top_songs.sort(key=lambda x: x["plays"], reverse=True)
    top_5_songs = top_songs[:100]

    top_5_artists = [{"artist": a, "plays": p, "tracks": None} for a, p in by_artist.most_common(5)]
    # fill "tracks" = number of contributing tracks for that artist
    artist_track_counts = defaultdict(int)
    for v in deltas.values():
        if v["delta"] > 0:
            artist_track_counts[v["artist"]] += 1
    for item in top_5_artists:
        item["tracks"] = artist_track_counts.get(item["artist"], 0)

    # find top album (if tie, returns the one with highest plays; ties not specially grouped)
    top_album = None
    if by_album:
        album_name, album_plays = by_album.most_common(1)[0]
        top_album = {"album": album_name, "plays": album_plays, "tracks": None}
        # count contributing tracks
        album_track_counts = defaultdict(int)
        for v in deltas.values():
            if v["delta"] > 0:
                album_track_counts[v["album"]] += 1
        top_album["tracks"] = album_track_counts.get(album_name, 0)

    stats = {
        "total_play_deltas": total_play_deltas,
        "tracks_with_plays_this_year": tracks_with_plays,
        "average_plays_per_played_track": (total_play_deltas / tracks_with_plays) if tracks_with_plays else 0.0,
        "top_5_artists": top_5_artists,
        "top_album": top_album,
        "top_100_songs": top_5_songs,
    }
    return stats

def produce_summary(current_map, prev_map, deltas, stats):
    """Build a friendly summary dict to dump to JSON."""
    current_total_tracks = len(current_map)
    prev_total_tracks = len(prev_map)
    new_tracks = [k for k, v in deltas.items() if v["previous_playcount"] == 0 and v["current_playcount"] > 0]
    removed_tracks = [k for k, v in deltas.items() if v["previous_playcount"] > 0 and v["current_playcount"] == 0]

    summary = {
        "metadata": {
            "current_snapshot_tracks": current_total_tracks,
            "previous_snapshot_tracks": prev_total_tracks,
            "new_tracks_count": len(new_tracks),
            "removed_tracks_count": len(removed_tracks),
            "tracks_added_list_sample": new_tracks[:10],
            "tracks_removed_list_sample": removed_tracks[:10],
        },
        "deltas_summary": {
            "total_plays_this_year": stats["total_play_deltas"],
            "tracks_with_plays_this_year": stats["tracks_with_plays_this_year"],
            "average_plays_per_played_track": stats["average_plays_per_played_track"]
        },
        "top_lists": {
            "top_5_artists": stats["top_5_artists"],
            "top_album": stats["top_album"],
            "top_100_songs": stats["top_100_songs"]
        },
        # include a small per-song delta index for potential debugging / further analysis
        "per_song_deltas_count": len(deltas),
    }
    return summary

def main():
    parser = argparse.ArgumentParser(description="Compute this-year stats from Quod Libet playcounts snapshots.")
    parser.add_argument("input", help="Path to current playcounts.json (e.g., playcounts/2025/playcounts.json)")
    parser.add_argument("--previous", "-p", help="Explicit path to previous year's playcounts.json (overrides auto-detect)")
    parser.add_argument("--output", "-o", default=None, help="Output JSON path (defaults to same folder as input as stats.json)")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    # Try to find previous automatically unless user provided one
    prev_path = None
    if args.previous:
        prev_path = Path(args.previous)
        if not prev_path.exists():
            print(f"Warning: explicit previous file not found: {prev_path} -- continuing without previous snapshot")
            prev_path = None
    else:
        auto_prev = detect_previous_path_from_current(input_path)
        if auto_prev and auto_prev.exists():
            prev_path = auto_prev

    current_map = load_playcounts(input_path)
    prev_map = load_playcounts(prev_path) if prev_path else {}

    deltas = compute_deltas(current_map, prev_map)
    stats = aggregate_stats(deltas)
    summary = produce_summary(current_map, prev_map, deltas, stats)

    # Output path default: same folder as input, file named stats.json
    if args.output:
        out_path = Path(args.output)
    else:
        out_path = input_path.parent / "stats.json"

    with out_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Saved stats to {out_path}")
    if prev_path:
        print(f"Used previous snapshot: {prev_path}")
    else:
        print("No previous snapshot found; stats treat current snapshot as full-year totals.")

if __name__ == "__main__":
    main()
