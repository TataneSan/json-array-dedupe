import io
import json
import unittest
from contextlib import redirect_stdout, redirect_stderr
from unittest import mock

from json_array_dedupe.cli import canonical, dedupe, extract_key, main


class UnitTests(unittest.TestCase):
    def test_canonical_key_order(self):
        self.assertEqual(canonical({"a": 1, "b": 2}), canonical({"b": 2, "a": 1}))

    def test_extract_key_nested(self):
        self.assertEqual(extract_key({"user": {"name": "ada"}}, "user.name"), "ada")

    def test_extract_key_array_index(self):
        self.assertEqual(extract_key([{"id": 7}], "0.id"), 7)

    def test_extract_key_missing(self):
        with self.assertRaises(KeyError):
            extract_key({"a": 1}, "b")

    def test_dedupe_scalars(self):
        unique, removed = dedupe([1, 2, 2, 3, 1])
        self.assertEqual(unique, [1, 2, 3])
        self.assertEqual(removed, 2)

    def test_dedupe_stable_first(self):
        unique, _ = dedupe([{"id": 1, "v": "a"}, {"id": 1, "v": "b"}],
                           key_path="id")
        self.assertEqual(unique, [{"id": 1, "v": "a"}])

    def test_dedupe_keep_last(self):
        unique, _ = dedupe([{"id": 1, "v": "a"}, {"id": 1, "v": "b"}],
                           key_path="id", keep_last=True)
        self.assertEqual(unique, [{"id": 1, "v": "b"}])

    def test_dedupe_objects_deep(self):
        unique, removed = dedupe([{"a": 1, "b": 2}, {"b": 2, "a": 1}])
        self.assertEqual(len(unique), 1)
        self.assertEqual(removed, 1)


class CliTests(unittest.TestCase):
    def run_cli(self, argv, stdin_text=""):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch("sys.stdin", io.StringIO(stdin_text)), \
                redirect_stdout(out), redirect_stderr(err):
            rc = main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_stdin_basic(self):
        rc, out, _ = self.run_cli([], '[1, 2, 2, 3, 1]')
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out), [1, 2, 3])

    def test_key(self):
        rc, out, _ = self.run_cli(
            ["--key", "id"],
            '[{"id":1,"v":"a"},{"id":2,"v":"b"},{"id":1,"v":"c"}]')
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out),
                         [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}])

    def test_not_array(self):
        rc, _, err = self.run_cli([], '{"a": 1}')
        self.assertEqual(rc, 1)
        self.assertIn("array", err)

    def test_invalid_json(self):
        rc, _, err = self.run_cli([], 'not json')
        self.assertEqual(rc, 1)
        self.assertIn("invalid JSON", err)

    def test_check_no_dupes(self):
        rc, out, _ = self.run_cli(["--check"], '[1, 2, 3]')
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_check_dupes(self):
        rc, out, _ = self.run_cli(["--check"], '[1, 1]')
        self.assertEqual(rc, 2)
        self.assertEqual(out, "")

    def test_json_report(self):
        rc, out, _ = self.run_cli(["--json"], '[1, 1, 2]')
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertEqual(report["removed"], 1)
        self.assertEqual(report["kept"], 2)

    def test_jsonl(self):
        rc, out, _ = self.run_cli(["--jsonl"], '[1,1]\n[2,3,3]\n')
        self.assertEqual(rc, 0)
        lines = [json.loads(ln) for ln in out.splitlines()]
        self.assertEqual(lines, [[1], [2, 3]])

    def test_jsonl_bad_line(self):
        rc, _, err = self.run_cli(["--jsonl"], '[1]\nbroken\n')
        self.assertEqual(rc, 1)
        self.assertIn("line 2", err)

    def test_missing_key_element(self):
        rc, _, err = self.run_cli(["--key", "id"], '[{"id":1},{"x":2}]')
        self.assertEqual(rc, 1)
        self.assertIn("element 1", err)


if __name__ == "__main__":
    unittest.main()
