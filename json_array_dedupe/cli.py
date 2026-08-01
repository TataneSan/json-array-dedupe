"""json-array-dedupe: remove duplicate elements from arrays in JSON/JSONL.

Every array encountered in the input documents is deduplicated by canonical
JSON serialization (key order normalized), preserving the first occurrence
position. Nested arrays/objects inside elements are compared structurally.

Reads stdin when FILE is omitted or "-", writes the transformed documents to
stdout as JSON Lines (one document per line).

Exit codes:
    0: success
    1: I/O, CLI or JSON parse error
    2: --check mode and at least one duplicate element was found
"""
import argparse
import json
import sys


def canon(item):
    return json.dumps(item, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def dedupe_array(arr, stats):
    seen = set()
    out = []
    for item in arr:
        key = canon(item)
        if key in seen:
            stats["removed"] += 1
            continue
        seen.add(key)
        out.append(item)
    return out


def walk(node, stats):
    if isinstance(node, list):
        node = dedupe_array(node, stats)
        for i, item in enumerate(node):
            node[i] = walk(item, stats)
        return node
    if isinstance(node, dict):
        for k, v in node.items():
            node[k] = walk(v, stats)
        return node
    return node


def read_docs(text):
    text = text.strip()
    if not text:
        return []
    try:
        return [json.loads(text)]
    except json.JSONDecodeError:
        pass
    docs = []
    for lineno, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            docs.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {lineno}: invalid JSON: {exc}")
    return docs


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="json-array-dedupe",
        description="Remove duplicate elements from arrays in JSON/JSONL documents.",
    )
    parser.add_argument("file", nargs="?", default="-",
                        help="JSON/JSONL input file (default: stdin)")
    parser.add_argument("--check", action="store_true",
                        help="exit 2 if any duplicate array element exists, no rewrite")
    parser.add_argument("--json", action="store_true",
                        help="emit a machine-readable JSON report on stderr")
    args = parser.parse_args(argv)

    try:
        if args.file == "-":
            data = sys.stdin.read()
        else:
            with open(args.file, "r", encoding="utf-8") as f:
                data = f.read()
    except OSError as exc:
        print(f"error: cannot read {args.file}: {exc}", file=sys.stderr)
        return 1

    try:
        docs = read_docs(data)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    stats = {"removed": 0}
    out_docs = [walk(doc, stats) for doc in docs]

    report = {
        "documents": len(docs),
        "duplicates_removed": stats["removed"],
    }

    if args.check:
        if args.json:
            print(json.dumps(report, indent=2), file=sys.stderr)
        else:
            print(f"duplicates: {stats['removed']}", file=sys.stderr)
        return 2 if stats["removed"] else 0

    for doc in out_docs:
        print(json.dumps(doc, ensure_ascii=False))

    if args.json:
        print(json.dumps(report, indent=2), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
