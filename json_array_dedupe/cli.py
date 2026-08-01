#!/usr/bin/env python3
"""json-array-dedupe - stable deduplication of JSON array elements.

Reads a JSON array (whole document) or JSON Lines (one array per line) and
removes duplicated elements while preserving the first occurrence. Elements
are compared by canonical serialization, or by an extracted key.

Exit codes:
    0 - success (with --check: no duplicates found)
    1 - CLI, parse or I/O error
    2 - --check found duplicates that would be removed
"""

import argparse
import json
import sys


def canonical(value):
    """Canonical, hashable representation of any JSON value."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def extract_key(element, path):
    """Extract a comparison key from an element following a dot path.

    Numeric segments index into arrays. A missing segment raises KeyError.
    """
    node = element
    for part in path.split("."):
        if isinstance(node, dict):
            node = node[part]
        elif isinstance(node, list):
            node = node[int(part)]
        else:
            raise KeyError(part)
    return node


def dedupe(array, key_path=None, keep_last=False):
    """Return (unique_list, removed_count). Stable: first (or last) kept."""
    seen = {}
    for index, element in enumerate(array):
        try:
            basis = extract_key(element, key_path) if key_path else element
        except (KeyError, IndexError, TypeError, ValueError):
            raise ValueError("key path %r not found in element %d"
                             % (key_path, index))
        fingerprint = canonical(basis)
        if keep_last or fingerprint not in seen:
            seen[fingerprint] = element
    unique = list(seen.values())
    return unique, len(array) - len(unique)


def read_input(path):
    if path in (None, "-"):
        return sys.stdin.read()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def emit(value, indent=None):
    if indent is None:
        json.dump(value, sys.stdout, separators=(",", ":"),
                  ensure_ascii=False)
    else:
        json.dump(value, sys.stdout, indent=indent, ensure_ascii=False)
    sys.stdout.write("\n")


def process_document(text, key_path, keep_last):
    """Dedupe a JSON array. Returns (output, original_len, removed)."""
    data = json.loads(text)
    if not isinstance(data, list):
        raise ValueError("top-level value must be a JSON array")
    output, removed = dedupe(data, key_path, keep_last)
    return output, len(data), removed


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="json-array-dedupe",
        description="Remove duplicate elements from JSON arrays "
                    "(stable order, optional key-based comparison).",
    )
    parser.add_argument(
        "file", nargs="?", metavar="FILE",
        help="JSON file; reads stdin when omitted or '-'",
    )
    parser.add_argument(
        "--key", metavar="PATH", default=None,
        help="dot path used as comparison key for objects "
             "(e.g. id, user.name, 0.id)",
    )
    parser.add_argument(
        "--keep-last", action="store_true",
        help="keep the last occurrence instead of the first",
    )
    parser.add_argument(
        "--jsonl", action="store_true",
        help="treat input as JSON Lines: one array per line",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="exit 2 when duplicates are found; writes nothing",
    )
    parser.add_argument(
        "--indent", type=int, default=None, metavar="N",
        help="pretty-print output with N spaces",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="emit a JSON stats report instead of the deduped array",
    )
    args = parser.parse_args(argv)

    try:
        text = read_input(args.file)
    except OSError as exc:
        print("json-array-dedupe: %s: %s" % (args.file, exc), file=sys.stderr)
        return 1

    reports = []
    had_dupes = False
    rc = 0

    if args.jsonl:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        out_lines = []
        for lineno, line in enumerate(lines, 1):
            try:
                output, total, removed = process_document(
                    line, args.key, args.keep_last)
            except (ValueError, json.JSONDecodeError) as exc:
                print("json-array-dedupe: line %d: %s" % (lineno, exc),
                      file=sys.stderr)
                rc = 1
                continue
            had_dupes = had_dupes or removed > 0
            reports.append({"line": lineno, "elements": total,
                            "removed": removed, "kept": total - removed})
            out_lines.append(output)
        if not args.check and not args.json:
            for output in out_lines:
                emit(output, args.indent)
    else:
        try:
            output, total, removed = process_document(
                text, args.key, args.keep_last)
        except json.JSONDecodeError as exc:
            print("json-array-dedupe: invalid JSON: %s" % exc, file=sys.stderr)
            return 1
        except ValueError as exc:
            print("json-array-dedupe: %s" % exc, file=sys.stderr)
            return 1
        had_dupes = removed > 0
        reports.append({"file": args.file or "<stdin>", "elements": total,
                        "removed": removed, "kept": total - removed})
        if not args.check and not args.json:
            emit(output, args.indent)

    if args.json:
        payload = reports[0] if len(reports) == 1 else reports
        emit(payload, 2)

    if args.check and had_dupes:
        return 2
    return rc


if __name__ == "__main__":
    sys.exit(main())
