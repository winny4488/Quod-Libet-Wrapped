import json
import argparse
from pathlib import Path

parser = argparse.ArgumentParser(description="Generate m3u playlist file based on this years playcounts")
parser.add_argument("--output", "-o", default="Top_Songs.m3u", help="Output m3u path")
args = parser.parse_args()

INPUT_JSON = "playcounts.json"
OUTPUT_M3U = Path(args.output)
LIMIT = 100

with open(INPUT_JSON, "r", encoding="utf-8") as f:
    entries = json.load(f)

with open(OUTPUT_M3U, "w", encoding="utf-8") as f:
    f.write("#EXTM3U\n")

    for i, entry in enumerate(entries):
        if i >= LIMIT:
            break

        path = Path(entry["file"])
        if path.exists():
            f.write(str(path.resolve()) + "\n")
        else:
            print("Missing file:", path)

print(f"Wrote {min(LIMIT, len(entries))} tracks to {OUTPUT_M3U}")
