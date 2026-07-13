"""Reading results from CSV and writing the table back out.

The parser is deliberately forgiving about columns it does not need and strict
about the ones it does. `round` and `date` are ignored, which is what keeps the
tool general: the same binary tabulates any set of results without knowing
anything about matchdays or the 1974/75 season.
"""

import csv
import io

import pytest

from league_table.csvio import InvalidInput, read_matches, write_table
from league_table.models import Match
from league_table.table import build_table

HEADER = "home_team,away_team,home_goals,away_goals\n"


def read(text):
    return read_matches(io.StringIO(text))


def fails(text):
    with pytest.raises(InvalidInput) as caught:
        read(text)
    return str(caught.value)


# --------------------------------------------------------------------------
# Reading well-formed results.
# --------------------------------------------------------------------------


def test_reads_one_match_per_line():
    matches = read(HEADER + "Ipswich Town,Chelsea,3,1\nEverton,Arsenal,2,2\n")

    assert len(matches) == 2
    assert matches[0].home_team == "Ipswich Town"
    assert matches[0].away_team == "Chelsea"
    assert (matches[0].home_goals, matches[0].away_goals) == (3, 1)
    assert (matches[1].home_goals, matches[1].away_goals) == (2, 2)


def test_a_file_with_only_a_header_is_a_valid_empty_set_of_results():
    # Not an error: a league simply has not kicked off yet.
    assert read(HEADER) == []


def test_extra_columns_are_ignored():
    """`round` and `date` ride along in the data files but mean nothing here.

    The tool must not know what a matchday is; it tabulates what it is handed.
    """
    matches = read(
        "round,date,home_team,away_team,home_goals,away_goals\n"
        "1,1974-08-17,Stoke City,Leeds United,3,0\n"
    )

    assert len(matches) == 1
    assert matches[0] == Match(
        home_team="Stoke City", away_team="Leeds United", home_goals=3, away_goals=0
    )


def test_column_order_does_not_matter():
    matches = read("away_goals,away_team,home_goals,home_team\n0,Leeds United,3,Stoke City\n")

    assert matches[0].home_team == "Stoke City"
    assert (matches[0].home_goals, matches[0].away_goals) == (3, 0)


def test_headers_and_values_tolerate_surrounding_whitespace_and_case():
    matches = read(" Home_Team , AWAY_TEAM ,home_goals,away_goals\n Burnley , Everton ,1, 2\n")

    assert matches[0].home_team == "Burnley"
    assert matches[0].away_team == "Everton"
    assert (matches[0].home_goals, matches[0].away_goals) == (1, 2)


def test_blank_lines_between_results_are_skipped():
    matches = read(HEADER + "Ipswich Town,Chelsea,3,1\n\n   \nEverton,Arsenal,2,2\n")

    assert len(matches) == 2


def test_club_names_containing_commas_survive_csv_quoting():
    matches = read(HEADER + '"Bolton, Wanderers of",Chelsea,1,0\n')

    assert matches[0].home_team == "Bolton, Wanderers of"


# --------------------------------------------------------------------------
# Rejecting malformed input. Every message must name the line at fault.
# --------------------------------------------------------------------------


def test_a_completely_empty_file_is_rejected():
    assert "no header" in fails("").lower()


def test_a_missing_required_column_is_rejected_and_named():
    message = fails("home_team,away_team,home_goals\nIpswich Town,Chelsea,3\n")

    assert "away_goals" in message


def test_all_missing_columns_are_named_at_once():
    message = fails("home_team,away_team\nIpswich Town,Chelsea\n")

    assert "home_goals" in message
    assert "away_goals" in message


def test_a_non_numeric_score_is_rejected_with_its_line_number():
    message = fails(HEADER + "Ipswich Town,Chelsea,3,1\nEverton,Arsenal,two,2\n")

    assert "line 3" in message  # header is line 1
    assert "two" in message


def test_a_negative_score_is_rejected():
    message = fails(HEADER + "Everton,Arsenal,-1,2\n")

    assert "line 2" in message
    assert "negative" in message.lower()


def test_a_missing_score_is_rejected():
    message = fails(HEADER + "Everton,Arsenal,,2\n")

    assert "line 2" in message


def test_a_short_row_is_rejected():
    message = fails(HEADER + "Everton,Arsenal,1\n")

    assert "line 2" in message


def test_a_blank_club_name_is_rejected():
    message = fails(HEADER + " ,Arsenal,1,2\n")

    assert "line 2" in message
    assert "name" in message.lower()


def test_a_club_playing_itself_is_rejected():
    message = fails(HEADER + "Arsenal,Arsenal,1,1\n")

    assert "line 2" in message
    assert "Arsenal" in message


# --------------------------------------------------------------------------
# Writing the table.
# --------------------------------------------------------------------------


def test_the_table_is_written_in_the_conventional_column_order():
    out = io.StringIO()

    write_table(build_table(read(HEADER + "Ipswich Town,Chelsea,3,1\n")), out)

    lines = out.getvalue().splitlines()
    assert lines[0] == (
        "Position,Team,Played,Won,Drawn,Lost,GoalsFor,GoalsAgainst,GoalAverage,Points"
    )
    assert lines[1] == "1,Ipswich Town,1,1,0,0,3,1,3.000,2"
    assert lines[2] == "2,Chelsea,1,0,0,1,1,3,0.333,0"


def test_an_empty_table_still_writes_its_header():
    out = io.StringIO()

    write_table([], out)

    assert out.getvalue().splitlines() == [
        "Position,Team,Played,Won,Drawn,Lost,GoalsFor,GoalsAgainst,GoalAverage,Points"
    ]


def test_the_goal_average_edge_cases_are_written_readably():
    out = io.StringIO()

    write_table(build_table(read(HEADER + "Clean Sheets FC,Hapless United,1,0\n")), out)

    body = out.getvalue()
    assert ",inf," in body  # conceded nothing
    assert ",0.000," in body  # scored nothing, conceded one


def test_the_written_table_parses_back_into_the_same_numbers():
    """A real round trip: write it, then read it back with csv and check it.

    (The previous version of this test merely counted newlines, which would have
    passed even if every number in the table had been wrong.)"""
    out = io.StringIO()

    write_table(build_table(read(HEADER + "Everton,Arsenal,2,1\n")), out)

    parsed = list(csv.DictReader(io.StringIO(out.getvalue())))
    assert [row["Team"] for row in parsed] == ["Everton", "Arsenal"]
    assert parsed[0] == {
        "Position": "1", "Team": "Everton", "Played": "1", "Won": "1", "Drawn": "0",
        "Lost": "0", "GoalsFor": "2", "GoalsAgainst": "1", "GoalAverage": "2.000",
        "Points": "2",
    }
    assert parsed[1]["Points"] == "0"
    assert parsed[1]["GoalAverage"] == "0.500"


# --------------------------------------------------------------------------
# Malformed headers and rows that must not be allowed to produce a wrong table.
# --------------------------------------------------------------------------


def test_a_duplicated_required_column_is_rejected():
    """Two `home_goals` columns cannot be silently resolved to one.

    Left unchecked this is the worst failure this tool has: a plausible table,
    exit code 0, and the wrong numbers in it.
    """
    message = fails(
        "home_team,away_team,home_goals,away_goals,home_goals\nIpswich Town,Chelsea,3,1,99\n"
    )

    assert "home_goals" in message
    assert "more than once" in message


def test_a_row_with_too_many_fields_is_rejected():
    # As much a sign of a misaligned file as a row with too few.
    message = fails(HEADER + "Everton,Arsenal,1,2,junk\n")

    assert "line 2" in message
    assert "4" in message and "5" in message


def test_a_byte_order_mark_does_not_hide_the_first_column():
    # This is what Excel and Google Sheets write by default.
    matches = read_matches(io.StringIO("﻿" + HEADER + "Everton,Arsenal,2,1\n"))

    assert matches[0].home_team == "Everton"


def test_line_numbers_survive_a_club_name_containing_a_newline():
    """csv records and physical lines are not the same thing.

    The bad score below sits on physical line 4; a naive record counter reports
    line 3 and sends the reader to the wrong row.
    """
    message = fails(
        HEADER + '"Ipswich\nTown",Chelsea,3,1\n' + "Everton,Arsenal,two,2\n"
    )

    assert "line 4" in message


def test_underscores_in_a_score_are_not_a_number():
    # Python's int() accepts PEP 515 separators: int("1_0") == 10.
    message = fails(HEADER + "Everton,Arsenal,1_0,2\n")

    assert "line 2" in message
    assert "1_0" in message


def test_non_ascii_digits_in_a_score_are_not_a_number():
    # int() happily parses Arabic-Indic digits; a goal count should not.
    message = fails(HEADER + "Everton,Arsenal,٣,2\n")

    assert "line 2" in message
