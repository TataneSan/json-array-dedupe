#!/usr/bin/env python3
"""json-array-dedupe — deduplicate elements of a JSON array.

Elements are compared with deep structural equality: objects keys are
compared recursively in any order, arrays element-wise in order.

Supports plain JSON documents containing a top-level array, arrays targeted
by a dotted path inside an object, and JSONL streams (one JSON value per
line, each line deduplicated if it is an array).

Exit codes:
    0  success
    1  CLI / I/O / JSON parse error
    2  --check and duplicates were found (or --unique and no duplicate found)
"""

import argparse
import json
import sys


def canon(value):
    """Canonical string form for deep equality of a JSON value."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def dedupe(seq, stable=True, count=False):
    """Return (items, counts or None, removed)."""
    seen = {}
    order = []
    for item in seq:
        key = canon(item)
        if key not in seen:
            seen[key] = {"item": item, "count": 1, "first": len(order)}
            order.append(key)
        else:
            seen[key]["count"] += 1
            if not stable:
                seen[key]["item"] = item  # last occurrence wins
    items = [seen[k]["item"] for k in order]
    counts = [seen[k]["count"] for k in order] if count else None
    removed = len(seq) - len(items)
    return items, counts, removed


def resolve_path(doc, path):
    """Walk dotted path (digits index arrays). Return (array, setter) or None."""
    if not path:
        return doc if isinstance(doc, list) else None, None
    cur = doc
    parts = path.split(".")
    for part in parts[:-1]:
        if isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return None, None
        elif isinstance(cur, dict):
            if part not in cur:
                return None, None
            cur = cur[part]
        else:
            return None, None
    last = parts[-1]
    if isinstance(cur, dict) and last in cur and isinstance(cur[last], list):
        return cur[last], lambda v: cur.__setitem__(last, v)
    if isinstance(cur, list):
        try:
            idx = int(last)
        except ValueError:
            return None, None
        if 0 <= idx < len(cur) and isinstance(cur[idx], list):
            return cur[idx], lambda v: cur.__setitem__(idx, v)
    return None, None


def build_parser():
    p = argparse.ArgumentParser(
        prog="json-array-dedupe",
        description="Deduplicate elements of a JSON array (deep equality).",
    )
    p.add_argument("file", nargs="?", default="-",
                   help="JSON file (default: stdin, '-' for stdin)")
    p.add_argument("-p", "--path", default="",
                   help="dotted path to the array inside an object "
                        "(e.g. 'data.items'); digits index into arrays")
    p.add_argument("--last", dest="stable", action="store_false",
                   help="keep the LAST occurrence of each duplicate "
                        "(default: keep first)")
    p.add_argument("--count", action="store_true",
                   help="emit an object per unique element: "
                        "{'value': ..., 'count': N}")
    p.add_argument("--jsonl", action="store_true",
                   help="treat input as JSONL: dedupe each line that is an "
                        "array, pass other lines through")
    p.add_argument("--compact", action="store_true",
                   help="compact JSON output (no indentation)")
    p.add_argument("-o", "--output", default=None,
                   help="output file (default: stdout)")
    p.add_argument("--check", action="store_true",
                   help="do not write output; exit 2 if duplicates exist")
    p.add_argument("--require-duplicates", action="store_true",
                   help="with --check: exit 2 when NO duplicate is found "
                        "(inverse CI gate)")
    p.add_argument("--json", action="store_true",
                   help="print a JSON report on stderr")
    p.add_argument("-q", "--quiet", action="store_true",
                   help="suppress the human report on stderr")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.file == "-":
        text = sys.stdin.read()
    else:
        try:
            with open(args.file, encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            print("error: cannot read %s: %s" % (args.file, exc),
                  file=sys.stderr)
            return 1

    total_in = 0
    total_out = 0
    removed_total = 0

    def dump(value):
        if args.compact:
            return json.dumps(value, separators=(",", ":"),
                              ensure_ascii=False)
        return json.dumps(value, indent=2, ensure_ascii=False)

    if args.jsonl:
        out_lines = []
        for lineno, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                val = json.loads(line)
            except json.JSONDecodeError:
                print("error: invalid JSON on line %d" % lineno,
                      file=sys.stderr)
                return 1
            if isinstance(val, list):
                items, counts, removed = dedupe(val, stable=args.stable,
                                                count=args.count)
                total_in += len(val)
                total_out += len(items)
                removed_total += removed
                if args.count:
                    val = [{"value": v, "count": c}
                           for v, c in zip(items, counts)]
                else:
                    val = items
            out_lines.append(json.dumps(val, ensure_ascii=False))
        output_text = "\n".join(out_lines) + ("\n" if out_lines else "")
    else:
        try:
            doc = json.loads(text)
        except json.JSONDecodeError as exc:
            print("error: invalid JSON: %s" % exc, file=sys.stderr)
            return 1
        arr, setter = resolve_path(doc, args.path) if args.path else (
            (doc, None) if isinstance(doc, list) else (None, None))
        if arr is None:
            print("error: no array found"
                  + (" at path '%s'" % args.path if args.path else
                     " (top-level value is not an array; use -p PATH)"),
                  file=sys.stderr)
            return 1
        items, counts, removed = dedupe(arr, stable=args.stable,
                                        count=args.count)
        total_in, total_out, removed_total = len(arr), len(items), removed
        replacement = items
        if args.count:
            replacement = [{"value": v, "count": c}
                           for v, c in zip(items, counts)]
        if setter is not None:
            setter(replacement)
            out_doc = doc
        else:
            out_doc = replacement
        output_text = dump(out_doc) + "\n"

    has_dupes = removed_total > 0
    status = 0
    if args.check:
        if args.require_duplicates:
            status = 0 if has_dupes else 2
        else:
            status = 2 if has_dupes else 0
        if not args.quiet and not args.json:
            print("check: %d element(s) in, %d unique, %d duplicate(s)"
                  % (total_in, total_out, removed_total), file=sys.stderr)
        if args.json:
            print(json.dumps({
                "elements_in": total_in,
                "elements_unique": total_out,
                "duplicates": removed_total,
                "gate": "require-duplicates" if args.require_duplicates
                        else "no-duplicates",
                "ok": status == 0,
            }, indent=2), file=sys.stderr)
        return status

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(output_text)
        except OSError as exc:
            print("error: cannot write %s: %s" % (args.output, exc),
                  file=sys.stderr)
            return 1
    else:
        sys.stdout.write(output_text)

    report = {
        "elements_in": total_in,
        "elements_unique": total_out,
        "duplicates_removed": removed_total,
    }
    if args.json:
        print(json.dumps(report, indent=2), file=sys.stderr)
    elif not args.quiet and args.output:
        print("deduped: %d -> %d (%d removed)"
              % (total_in, total_out, removed_total), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
