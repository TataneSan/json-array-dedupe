import io
import unittest
from contextlib import redirect_stdout, redirect_stderr

from json_array_dedupe.cli import main


def run(argv, stdin_text=""):
    import sys
    old = sys.stdin
    sys.stdin = io.StringIO(stdin_text)
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
    finally:
        sys.stdin = old
    return code, out.getvalue(), err.getvalue()


class TestDedupe(unittest.TestCase):
    def test_scalar_dupes(self):
        code, out, _ = run(["-"], '{"tags": ["a", "b", "a", "c", "b"]}')
        self.assertEqual(out, '{"tags": ["a", "b", "c"]}\n')

    def test_object_dupes_key_order(self):
        code, out, _ = run(["-"], '{"items": [{"x": 1, "y": 2}, {"y": 2, "x": 1}]}')
        self.assertEqual(out, '{"items": [{"x": 1, "y": 2}]}\n')

    def test_nested_arrays(self):
        code, out, _ = run(["-"], '[[1, 1], [2]]')
        self.assertEqual(out, '[[1], [2]]\n')

    def test_jsonl(self):
        code, out, _ = run(["-"], '{"a": [1, 1]}\n{"b": [2]}\n')
        self.assertEqual(out, '{"a": [1]}\n{"b": [2]}\n')

    def test_strings_not_numbers(self):
        code, out, _ = run(["-"], '{"v": [1, "1"]}')
        self.assertEqual(out, '{"v": [1, "1"]}\n')

    def test_check_fail(self):
        code, _, _ = run(["--check", "-"], '{"a": [1, 1]}')
        self.assertEqual(code, 2)

    def test_check_pass(self):
        code, _, _ = run(["--check", "-"], '{"a": [1, 2]}')
        self.assertEqual(code, 0)

    def test_invalid(self):
        code, _, err = run(["-"], "{bad")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
