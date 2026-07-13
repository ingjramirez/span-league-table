"""The command line. Argument parsing and streams; no rules live here.

    league-table                       # stdin  -> stdout
    league-table results.csv           # file   -> stdout
    league-table results.csv -o t.csv  # file   -> file
    cat results.csv | league-table     # a plain unix filter

The table is computed in full before a single byte is written, so a malformed
input never leaves a half-written table behind.
"""

import argparse
import contextlib
import io
import os
import sys
from collections import Counter
from typing import IO, Iterator, List, Optional, Sequence

from league_table import __version__
from league_table.csvio import InvalidInput, read_matches, write_table
from league_table.models import Match, Standing
from league_table.table import build_table

EXIT_OK = 0
EXIT_INVALID_INPUT = 2
# The conventional status for a process killed by SIGPIPE (128 + 13), which is
# what a shell would have reported had we not caught the error.
EXIT_BROKEN_PIPE = 141

_STDIO = "-"

_PRETTY_COLUMNS = ("Pos", "Team", "P", "W", "D", "L", "F", "A", "GAvg", "Pts")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="league-table",
        description=(
            "Calculate a football league standing table from match results, "
            "using the rules of the English First Division in 1974/75: two points "
            "for a win, one for a draw, and clubs level on points separated by "
            "goal average (goals scored divided by goals conceded)."
        ),
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=_STDIO,
        help="CSV of results; omit or pass '-' to read standard input",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=_STDIO,
        help="where to write the table; omit or pass '-' for standard output",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="print an aligned text table instead of CSV",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"league-table {__version__}",
    )
    return parser


def _warn_about_repeated_fixtures(matches: Sequence[Match], stderr: IO[str]) -> None:
    """Flag any pairing that appears more than once at the same ground.

    Not an error: some leagues really do play the same fixture twice at the same
    ground in a season, and this tool tabulates whatever league it is handed. But
    a duplicated row in a results feed is the commonest way to end up with a
    confidently wrong table, so it does not go through in silence.
    """
    played = Counter((match.home_team, match.away_team) for match in matches)

    for (home, away), count in played.items():
        if count > 1:
            times = "twice" if count == 2 else f"{count} times"
            print(
                f"league-table: warning: {home} v {away} appears {times}; "
                "every occurrence has been counted",
                file=stderr,
            )


@contextlib.contextmanager
def _opened(path: str, mode: str, stream: IO[str]) -> Iterator[IO[str]]:
    """Yield the named file, or the given standard stream for '-'.

    Input is decoded as utf-8-sig, which strips a byte order mark if one is
    present and is a plain utf-8 read if not. Excel and Google Sheets both write
    a BOM by default, so without this the commonest real-world CSV in existence
    fails with a baffling "missing required column: home_team".
    """
    if path == _STDIO:
        yield stream
        return

    encoding = "utf-8-sig" if mode == "r" else "utf-8"

    try:
        handle = open(path, mode, newline="", encoding=encoding)
    except OSError as error:
        raise InvalidInput(f"cannot open {path}: {error.strerror}") from None

    try:
        # A decode error is bad input, not a crash: UnicodeError is a ValueError,
        # not an OSError, so it would otherwise sail past as a traceback.
        yield handle
    except UnicodeError as error:
        raise InvalidInput(f"cannot read {path}: {error}") from None
    finally:
        handle.close()


def _silence_stdout(stdout: IO[str]) -> None:
    """Redirect the real stdout to /dev/null, if there is a real one.

    Only meaningful for an actual file descriptor; under test the stream is an
    in-memory buffer with nothing to redirect, so there is nothing to do.
    """
    try:
        fileno = stdout.fileno()
    except (AttributeError, io.UnsupportedOperation):
        return

    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, fileno)


def _write_pretty(standings: Sequence[Standing], stream: IO[str]) -> None:
    rows = [
        (
            str(row.position),
            row.team,
            str(row.played),
            str(row.won),
            str(row.drawn),
            str(row.lost),
            str(row.goals_for),
            str(row.goals_against),
            str(row.goal_average),
            str(row.points),
        )
        for row in standings
    ]

    widths = [
        max(len(cell) for cell in column) for column in zip(_PRETTY_COLUMNS, *rows)
    ]

    def line(cells: Sequence[str]) -> str:
        # The club name reads best left-aligned; the numbers line up right.
        rendered = [
            cell.ljust(width) if index == 1 else cell.rjust(width)
            for index, (cell, width) in enumerate(zip(cells, widths))
        ]
        return "  ".join(rendered).rstrip()

    stream.write(line(_PRETTY_COLUMNS) + "\n")
    for row in rows:
        stream.write(line(row) + "\n")


def main(
    argv: Optional[List[str]] = None,
    stdin: Optional[IO[str]] = None,
    stdout: Optional[IO[str]] = None,
    stderr: Optional[IO[str]] = None,
) -> int:
    """Run the tool. Returns the process exit code.

    The streams are injectable so the tests can drive the real entry point
    without spawning a process or monkeypatching `sys`.
    """
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr

    args = _parser().parse_args(argv)

    try:
        with _opened(args.input, "r", stdin) as source:
            matches = read_matches(source)

        _warn_about_repeated_fixtures(matches, stderr)

        standings = build_table(matches)

        # Render to memory first: if anything above had failed we would not have
        # touched the output at all, and this keeps that guarantee for the write.
        rendered = io.StringIO()
        if args.pretty:
            _write_pretty(standings, rendered)
        else:
            write_table(standings, rendered)

        with _opened(args.output, "w", stdout) as destination:
            destination.write(rendered.getvalue())
            # Flush while we can still do something about a failure. Left to the
            # interpreter's exit-time flush, a broken pipe or a full disk would
            # surface as a traceback and an exit code we never chose.
            destination.flush()

    except InvalidInput as error:
        print(f"league-table: {error}", file=stderr)
        return EXIT_INVALID_INPUT

    except BrokenPipeError:
        # `league-table results.csv | head -1` closes the pipe under us. That is
        # a reader losing interest, not an error -- but Python flushes stdout
        # again on the way out, which would raise a second BrokenPipeError and
        # print a traceback. Point the fd at /dev/null so that final flush has
        # somewhere harmless to go, and exit the way a unix filter should.
        _silence_stdout(stdout)
        return EXIT_BROKEN_PIPE

    return EXIT_OK
