"""CSV in, CSV out. All the I/O lives here; none of the rules do.

The parser needs four columns -- home_team, away_team, home_goals, away_goals --
and ignores every other column it finds. That is what lets the data files carry
`round` and `date` for a human's benefit while the tool stays entirely ignorant
of matchdays and seasons.
"""

import csv
from collections import Counter
from typing import IO, Iterable, List, Sequence

from league_table.models import Match, Standing

REQUIRED_COLUMNS = ("home_team", "away_team", "home_goals", "away_goals")

OUTPUT_COLUMNS = (
    "Position",
    "Team",
    "Played",
    "Won",
    "Drawn",
    "Lost",
    "GoalsFor",
    "GoalsAgainst",
    "GoalAverage",
    "Points",
)


class InvalidInput(Exception):
    """The input is not a readable set of results.

    Carries a message naming the offending line, so a human can go and fix it.
    """


def _normalise_header(fieldnames: Sequence[str]) -> List[str]:
    # A leading BOM would otherwise ride along on the first column name, so that
    # 'home_team' fails to match 'home_team'. Files opened by this module are
    # decoded as utf-8-sig, but a caller can hand us any stream -- stdin, most
    # obviously -- so strip it here too.
    return [(name or "").lstrip("﻿").strip().lower() for name in fieldnames]


def _is_goal_count(value: str) -> bool:
    """True for a plain run of ASCII digits, and nothing else."""
    return value.isascii() and value.isdigit()


def _read_goals(row: dict, column: str, line: int) -> int:
    # Every required column is guaranteed present: the header is checked once up
    # front, and rows of the wrong width are rejected before we get here.
    value = row[column].strip()

    if value == "":
        raise InvalidInput(f"line {line}: missing a value for '{column}'")

    if value.startswith("-") and _is_goal_count(value[1:]):
        raise InvalidInput(f"line {line}: '{column}' cannot be negative, got {value}")

    # Deliberately stricter than int(), which accepts PEP 515 underscores
    # ("1_0" -> 10) and non-ASCII decimal digits. Neither is a goal count, and
    # both would silently produce a wrong table rather than an error.
    if not _is_goal_count(value):
        raise InvalidInput(
            f"line {line}: '{column}' must be a whole number of goals, got {value!r}"
        )

    return int(value)


def _read_team(row: dict, column: str, line: int) -> str:
    name = row[column].strip()

    if name == "":
        raise InvalidInput(f"line {line}: '{column}' is blank; every club needs a name")

    return name


def read_matches(stream: IO[str]) -> List[Match]:
    """Parse match results from an open CSV stream.

    Raises `InvalidInput` -- with the line number -- on anything it cannot read.
    """
    reader = csv.reader(stream)

    try:
        raw_header = next(reader)
    except StopIteration:
        raise InvalidInput("the input is empty: no header row found") from None

    header = _normalise_header(raw_header)
    seen = Counter(header)

    missing = [column for column in REQUIRED_COLUMNS if column not in header]
    if missing:
        raise InvalidInput(
            "the header is missing required column(s): "
            + ", ".join(missing)
            + f". Expected at least: {', '.join(REQUIRED_COLUMNS)}"
        )

    # A required column appearing twice cannot be resolved: one of the two values
    # would win silently, and the table would be quietly wrong. Refuse instead.
    duplicated = [column for column in REQUIRED_COLUMNS if seen[column] > 1]
    if duplicated:
        raise InvalidInput(
            "the header names these required column(s) more than once: "
            + ", ".join(duplicated)
        )

    matches = []

    for values in reader:
        # csv records and physical lines are not the same thing: a quoted club
        # name may span lines. `line_num` is the reader's own count of physical
        # lines, which is the number a human needs in order to find the row.
        line = reader.line_num

        if not any(value.strip() for value in values):
            continue  # a blank separator line is not an error

        if len(values) != len(header):
            raise InvalidInput(
                f"line {line}: expected {len(header)} columns, found {len(values)}"
            )

        row = dict(zip(header, values))

        home = _read_team(row, "home_team", line)
        away = _read_team(row, "away_team", line)

        if home == away:
            raise InvalidInput(f"line {line}: {home} cannot play itself")

        matches.append(
            Match(
                home_team=home,
                away_team=away,
                home_goals=_read_goals(row, "home_goals", line),
                away_goals=_read_goals(row, "away_goals", line),
            )
        )

    return matches


def write_table(standings: Iterable[Standing], stream: IO[str]) -> None:
    """Write the standing table as CSV, in the conventional column order."""
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(OUTPUT_COLUMNS)

    for row in standings:
        writer.writerow(
            (
                row.position,
                row.team,
                row.played,
                row.won,
                row.drawn,
                row.lost,
                row.goals_for,
                row.goals_against,
                str(row.goal_average),
                row.points,
            )
        )
