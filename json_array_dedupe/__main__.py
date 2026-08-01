"""Entry point for python -m json_array_dedupe."""
import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())
