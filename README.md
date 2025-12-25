# Quod-Libet-Wrapped
Bash and Python script set to generate a Spotify Wrapped style Year-In Review for Quod Libet users
Generates yearly listening statistics and a "Your Top Songs <YEAR>.m3u" playlist
from a local Quod Libet library.

## Requirements
- Python 3.9+
- Quod Libet (local songs DB)
- Bash (Linux/macOS, or WSL on Windows)

## Usage
./orchestrator.sh

## Output
`playcounts/<YEAR>/`
  - playcounts.json
  - stats.json
  - Your Top Songs <YEAR>.m3u

## Notes
- First run will not have previous-year comparisons.
- This tool does not modify your Quod Libet library.
