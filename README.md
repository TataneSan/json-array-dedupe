# json-array-dedupe

Remove duplicate elements from arrays inside JSON or JSONL documents.
Deduplication is structural (key order in objects is normalized) and stable:
the first occurrence of each element is kept, later duplicates are dropped.

## Features

- Recursive: deduplicates arrays at any depth, including inside objects
- Structural comparison — `{"x":1,"y":2}` duplicates `{"y":2,"x":1}`
- Stable ordering: first occurrence wins, relative order preserved
- Type-aware: `1` (number) and `"1"` (string) are considered distinct
- `--check` CI mode: exits 2 when any duplicate element is found, no rewrite
- `--json` machine-readable report on stderr
- Pure Python standard library, no dependencies; output as JSON Lines

## Installation

```bash
pip install .
# or directly from GitHub
pip install git+https://github.com/TataneSan/json-array-dedupe.git
```

## Usage

```bash
echo '{"tags": ["a", "b", "a", "c"]}' | json-array-dedupe -
# {"tags": ["a", "b", "c"]}

# JSONL stream
json-array-dedupe events.jsonl > events.deduped.jsonl

# CI check
json-array-dedupe --check config.json || echo "duplicates found"

# JSON report
json-array-dedupe --json data.jsonl
```

Example JSON report (stderr):

```json
{
  "documents": 3,
  "duplicates_removed": 5
}
```

## Exit codes

- `0` — success (in `--check` mode: no duplicates found)
- `1` — I/O, CLI or JSON parse error
- `2` — `--check` mode: at least one duplicate array element exists

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
