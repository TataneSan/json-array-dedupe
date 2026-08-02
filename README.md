# json-array-dedupe

Deduplicate elements of a JSON array using deep structural equality.
Pure Python, zero dependency.

## Features

- Deep equality: object key order ignored, arrays compared element-wise
- Keep first occurrence (default) or last with `--last`
- `--count` emits `[{"value": ..., "count": N}, ...]`
- `-p data.items` targets an array nested inside an object
- `--jsonl` mode deduplicates each line that is an array, passes the rest through
- `--check` CI gate: exit 2 when duplicates exist
- `--require-duplicates` inverse gate (exit 2 when none found)
- `--compact` / `--json` / `-q`

## Install

```bash
pip install .
# or directly
pip install git+https://github.com/TataneSan/json-array-dedupe.git
```

## Usage

```bash
echo '[1,2,1,{"a":1,"b":2},{"b":2,"a":1}]' | json-array-dedupe
# [1, 2, {"a": 1, "b": 2}]

json-array-dedupe payload.json -p data.items
echo '["a","a","b"]' | json-array-dedupe --count --compact
# [{"value":"a","count":2},{"value":"b","count":1}]

json-array-dedupe events.jsonl --jsonl
json-array-dedupe data.json --check           # CI: fail if duplicates
json-array-dedupe data.json --check --require-duplicates --json
```

## Deep equality rules

| A | B | Equal? |
|---|---|---|
| `{"a":1,"b":2}` | `{"b":2,"a":1}` | yes (key order ignored) |
| `[1,2]` | `[2,1]` | no (array order matters) |
| `{"l":[1,{"z":2}]}` | `{"l":[1,{"z":2}]}` | yes (recursive) |

## Exit codes

- `0` success
- `1` CLI / I/O / JSON parse error
- `2` check gate failed

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT — see LICENSE.
