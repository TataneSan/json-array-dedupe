# json-array-dedupe

Remove duplicate elements from JSON arrays — stable order, canonical comparison, optional key-based dedupe. Works on whole documents or JSON Lines streams.

## Features

- Stable: keeps first occurrence by default (`--keep-last` to invert)
- Deep comparison via canonical serialization (key order inside objects ignored)
- `--key PATH` to dedupe by an extracted field (`id`, `user.name`, `0.id`)
- JSON Lines mode: one array per line, deduped independently
- `--check` CI mode: exit 2 when duplicates exist, writes nothing
- `--json` stats report (elements / removed / kept)
- `--indent N` pretty-print
- Zero dependencies, pure Python 3.9+

## Install

```bash
pip install .
# or directly from GitHub
pip install git+https://github.com/TataneSan/json-array-dedupe.git
```

## Usage

```
json-array-dedupe [OPTIONS] [FILE]
```

Reads stdin when FILE is omitted or `-`.

### Basic dedupe

```bash
echo '[1, 2, 2, 3, 1, "a", "a"]' | json-array-dedupe
# [1,2,3,"a"]
```

### Dedupe objects by a key

```bash
cat users.json | json-array-dedupe --key id
```

For input `[{"id":1,"v":"a"},{"id":2,"v":"b"},{"id":1,"v":"c"}]` this keeps the first two elements — the full objects are kept, only the key drives the comparison.

Nested paths work: `--key user.name`, and numeric segments index arrays (`--key 0.id`).

### Keep the last occurrence

```bash
echo '[{"id":1,"v":"old"},{"id":1,"v":"new"}]' | json-array-dedupe --key id --keep-last
# [{"id":1,"v":"new"}]
```

### JSON Lines mode

```bash
json-array-dedupe --jsonl lines.txt
```

Each non-empty line must be a JSON array; each is deduped independently.

### CI check

```bash
json-array-dedupe --check data.json; echo "exit=$?"
# exit=2 when duplicates are present, 0 when already unique
```

### Stats report

```bash
json-array-dedupe --json --check data.json
```

```json
{
  "file": "data.json",
  "elements": 10,
  "removed": 3,
  "kept": 7
}
```

## Options

| Option | Description |
|---|---|
| `FILE` | JSON file; stdin when omitted or `-` |
| `--key PATH` | dedupe objects by extracted key (dot path, numeric segments index arrays) |
| `--keep-last` | keep the last occurrence instead of the first |
| `--jsonl` | input is JSON Lines (one array per line) |
| `--check` | check-only: exit 2 if duplicates found, writes nothing |
| `--indent N` | pretty-print with N spaces |
| `--json` | emit a stats report instead of the array |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | success (`--check`: no duplicates) |
| 1 | CLI, parse or I/O error |
| 2 | `--check` found duplicates |

## Tests

```bash
python -m unittest discover -s tests -v
```

## License

MIT — see [LICENSE](LICENSE).
