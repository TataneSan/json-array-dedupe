import io
import json
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr

from json_array_dedupe.cli import main, dedupe, canon


class TestDedupe(unittest.TestCase):
    def test_scalars(self):
        items, counts, removed = dedupe([1, 2, 1, 3, 2, 1], count=True)
        self.assertEqual(items, [1, 2, 3])
        self.assertEqual(counts, [3, 2, 1])
        self.assertEqual(removed, 3)

    def test_deep_equality(self):
        a = {"x": 1, "y": [1, {"z": 2}]}
        b = {"y": [1, {"z": 2}], "x": 1}
        self.assertEqual(canon(a), canon(b))
        items, _, removed = dedupe([a, b])
        self.assertEqual(len(items), 1)
        self.assertEqual(removed, 1)

    def test_order_sensitive_arrays(self):
        a = [1, 2]
        b = [2, 1]
        items, _, removed = dedupe([a, b])
        self.assertEqual(len(items), 2)

    def test_last_wins(self):
        a = {"x": 1, "y": 2}
        b = {"y": 2, "x": 1}  # deep-equal to a, distinct object
        items, _, _ = dedupe([a, b], stable=True)
        self.assertIs(items[0], a)  # first occurrence kept by default
        items, _, _ = dedupe([a, b], stable=False)
        self.assertIs(items[0], b)  # last occurrence kept with stable=False


def run_cli(argv, stdin_text=""):
    old = sys.stdin
    sys.stdin = io.StringIO(stdin_text)
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
    finally:
        sys.stdin = old
    return code, out.getvalue(), err.getvalue()


class TestCli(unittest.TestCase):
    def test_basic(self):
        code, out, _ = run_cli([], "[1,2,1,3,2]\n")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), [1, 2, 3])

    def test_path(self):
        code, out, _ = run_cli(["-p", "data.items"],
                               '{"data":{"items":["a","b","a"]},"k":1}')
        doc = json.loads(out)
        self.assertEqual(doc["data"]["items"], ["a", "b"])
        self.assertEqual(doc["k"], 1)

    def test_bad_path(self):
        code, _, err = run_cli(["-p", "nope"], '{"a":[1]}')
        self.assertEqual(code, 1)

    def test_count(self):
        code, out, _ = run_cli(["--count", "--compact"], '["a","a","b"]')
        doc = json.loads(out)
        self.assertEqual(doc, [{"value": "a", "count": 2},
                               {"value": "b", "count": 1}])

    def test_jsonl(self):
        code, out, _ = run_cli(["--jsonl"], '[1,1,2]\n{"k":1}\n[3,3]\n')
        lines = [json.loads(l) for l in out.strip().splitlines()]
        self.assertEqual(lines, [[1, 2], {"k": 1}, [3]])

    def test_check_dupes(self):
        code, _, _ = run_cli(["--check"], "[1,1]")
        self.assertEqual(code, 2)

    def test_check_clean(self):
        code, _, _ = run_cli(["--check", "-q"], "[1,2,3]")
        self.assertEqual(code, 0)

    def test_require_duplicates(self):
        code, _, _ = run_cli(["--check", "--require-duplicates"], "[1,2]")
        self.assertEqual(code, 2)
        code, _, _ = run_cli(["--check", "--require-duplicates"], "[1,1]")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
