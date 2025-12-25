#!/bin/bash

year=$(date +%Y)
prev_year=$((year - 1))

PLAYCOUNTS="playcounts/$year/playcounts.json"
WORKDIR="playcounts/$year/"

# Step 1 - Generate playcount.json
if ! python3 ql_playcount.py; then
    echo 'Failed to retrieve playcounts from Quod Libet, QL Songs DB not found'
    exit 1
fi

# Step 2 - Generate stats.json
if ! python3 stats_from_playcounts.py --previous $prev_year $PLAYCOUNTS; then
    echo 'Failed to generate statistics from playcount'
    exit 1
fi

# Step 3 - Generate Your Top Songs <YEAR> m3u playlist
cp top_songs_playlist.py $WORKDIR || {
    echo 'Failed to copy playlist generator'
    exit 1
}

cd "$WORKDIR" || {
    echo "Failed to enter $WORKDIR"
    exit 1
}

if ! python3 top_songs_playlist.py -o "Your Top Songs $year.m3u"; then
    echo 'Failed to generate Top Songs playlist'
    echo 'Run manually with `python3 playcounts/$year/top_songs_playlist.py`'
    exit 1
fi

echo 'Cleaning up...'
rm top_songs_playlist.py

echo 'Success'

exit 0
