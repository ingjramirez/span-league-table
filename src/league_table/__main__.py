"""Lets the tool run as `python -m league_table`."""

import sys

from league_table.cli import main

if __name__ == "__main__":
    sys.exit(main())
