"""The actual answer to the exercise, pinned down.

These tests run the real 1974/75 results through the real CLI and assert on the
real table. They are the regression lock: if anyone changes the rules, the
parsing or the sort, the English First Division of 1974/75 changes shape and
these fail.
"""

import csv
import io
from pathlib import Path

from league_table.cli import EXIT_OK, main

DATA = Path(__file__).resolve().parent.parent / "data"

ROUNDS_1_TO_10 = DATA / "results_1974-75_rounds_1-10.csv"
PLAYED_BY_28_SEP = DATA / "results_1974-75_played_by_1974-09-28.csv"

STANDINGS_AFTER_MATCHDAY_10 = DATA / "standings_1974-75_after_matchday_10.csv"
STANDINGS_AS_OF_28_SEP = DATA / "standings_1974-75_as_of_1974-09-28.csv"


def table_for(results: Path):
    """Run the CLI over a results file and return the parsed table rows."""
    out = io.StringIO()
    code = main([str(results)], stdout=out)

    assert code == EXIT_OK
    return list(csv.DictReader(io.StringIO(out.getvalue())))


# --------------------------------------------------------------------------
# The submitted answer: the table after ten matchdays.
# --------------------------------------------------------------------------


def test_the_input_holds_every_match_of_the_first_ten_rounds():
    rows = list(csv.DictReader(ROUNDS_1_TO_10.open()))

    # 22 clubs, 11 matches a round, 10 rounds.
    assert len(rows) == 110
    assert {row["round"] for row in rows} == {str(n) for n in range(1, 11)}


def test_every_club_has_played_exactly_ten_matches():
    table = table_for(ROUNDS_1_TO_10)

    assert len(table) == 22
    assert {row["Played"] for row in table} == {"10"}


def test_ipswich_town_lead_the_first_division_after_ten_matchdays():
    top = table_for(ROUNDS_1_TO_10)[0]

    assert top["Team"] == "Ipswich Town"
    assert top["Points"] == "16"
    assert (top["Won"], top["Drawn"], top["Lost"]) == ("8", "0", "2")
    assert (top["GoalsFor"], top["GoalsAgainst"]) == ("18", "6")
    assert top["GoalAverage"] == "3.000"


def test_the_full_top_ten_after_matchday_ten():
    table = table_for(ROUNDS_1_TO_10)

    assert [(row["Team"], row["Points"]) for row in table[:10]] == [
        ("Ipswich Town", "16"),
        ("Newcastle United", "14"),
        ("Manchester City", "14"),
        ("Middlesbrough", "13"),
        ("Liverpool", "13"),
        ("Everton", "13"),
        ("Sheffield United", "13"),
        ("Derby County", "11"),
        ("Stoke City", "11"),
        ("Wolverhampton Wanderers", "11"),
    ]


# --------------------------------------------------------------------------
# The historical rule, visible in the real season.
# --------------------------------------------------------------------------


def test_goal_average_reorders_the_real_1974_75_table_against_goal_difference():
    """The rule is not academic: it moves clubs in the actual table.

    Middlesbrough and Liverpool both finish matchday 10 on 13 points.

        Middlesbrough  15 scored,  7 conceded -> average 2.143, difference +8
        Liverpool      17 scored,  8 conceded -> average 2.125, difference +9

    Goal average puts Middlesbrough 4th and Liverpool 5th. Goal difference --
    the modern rule, and the wrong one for 1974/75 -- would swap them. This is
    the exercise's whole point, occurring in the submitted answer itself.
    """
    table = table_for(ROUNDS_1_TO_10)
    by_team = {row["Team"]: row for row in table}

    boro, pool = by_team["Middlesbrough"], by_team["Liverpool"]

    assert boro["Points"] == pool["Points"] == "13"
    assert int(boro["Position"]) < int(pool["Position"])  # goal average: Boro ahead

    # And goal difference would have said the opposite.
    boro_difference = int(boro["GoalsFor"]) - int(boro["GoalsAgainst"])
    pool_difference = int(pool["GoalsFor"]) - int(pool["GoalsAgainst"])
    assert pool_difference > boro_difference


def test_goal_average_separates_three_clubs_that_goal_difference_would_tie():
    """The bottom three all end matchday 10 on 6 points AND -5 goal difference.

        Tottenham Hotspur    12-17  -> difference -5, average 0.706
        Arsenal              10-15  -> difference -5, average 0.667
        Queens Park Rangers   8-13  -> difference -5, average 0.615

    Goal difference cannot separate them at all. Goal average orders them
    cleanly, and that order is the one the 1974/75 table shows.
    """
    table = table_for(ROUNDS_1_TO_10)
    bottom_three = table[-3:]

    assert [row["Team"] for row in bottom_three] == [
        "Tottenham Hotspur",
        "Arsenal",
        "Queens Park Rangers",
    ]
    assert {row["Points"] for row in bottom_three} == {"6"}
    assert {
        int(row["GoalsFor"]) - int(row["GoalsAgainst"]) for row in bottom_three
    } == {-5}  # identical on the modern rule
    assert [row["GoalAverage"] for row in bottom_three] == ["0.706", "0.667", "0.615"]


# --------------------------------------------------------------------------
# The alternative reading, also shipped: the table as it actually stood.
# --------------------------------------------------------------------------


def test_the_28_september_table_reflects_the_three_postponed_fixtures():
    """Three round-9 games were postponed and played in Dec 1974 / Apr 1975.

    So on the evening of matchday 10, six clubs had played only nine games. This
    is the table as it truly stood, and the reason the submitted answer uses the
    matchday reading instead. See README.md.
    """
    table = table_for(PLAYED_BY_28_SEP)
    played_nine = {row["Team"] for row in table if row["Played"] == "9"}

    assert played_nine == {
        "Newcastle United",
        "Middlesbrough",
        "Leicester City",
        "Leeds United",
        "Arsenal",
        "Tottenham Hotspur",
    }
    assert table[0]["Team"] == "Ipswich Town"  # top either way


# --------------------------------------------------------------------------
# The committed output files must match what the tool actually produces.
# --------------------------------------------------------------------------


def test_the_committed_output_files_are_what_the_tool_produces_today():
    for results, expected in (
        (ROUNDS_1_TO_10, STANDINGS_AFTER_MATCHDAY_10),
        (PLAYED_BY_28_SEP, STANDINGS_AS_OF_28_SEP),
    ):
        produced = io.StringIO()

        assert main([str(results)], stdout=produced) == EXIT_OK
        assert produced.getvalue() == expected.read_text(), f"{expected.name} is stale"


# --------------------------------------------------------------------------
# The calendar reading, shipped so the ambiguity can be judged rather than taken
# on trust. It validates the data against a published table -- but NOT the
# tie-break rule, for the reason spelled out at the bottom of this file.
# --------------------------------------------------------------------------

PLAYED_BY_19_OCT = DATA / "results_1974-75_played_by_1974-10-19.csv"
STANDINGS_AS_OF_19_OCT = DATA / "standings_1974-75_as_of_1974-10-19.csv"


def test_the_tenth_calendar_week_table_matches_11v11s_published_table_exactly():
    """Our table for 19 October 1974, against the one 11v11 publishes.

    A published historical table, read from
    https://www.11v11.com/league-tables/league-division-one/19-october-1974/

    This validates the match data, the two-points rule, the goal-average
    arithmetic, and the handling of clubs on unequal games played (six postponed
    fixtures leave Leicester on 12 and ten clubs on 13).

    It does NOT validate the tie-break rule, and it must not be mistaken for a
    test that does. In this table goal average and goal difference never
    disagree, so it passes just as happily with the modern rule implemented --
    see test_the_archive_tables_cannot_tell_the_two_rules_apart below. The rule
    is defended by test_goal_average_and_goal_difference_disagree and by the
    matchday-10 assertions above, not by this.
    """
    published = [
        # team, P, W, D, L, GF, GA, GAvg, Pts
        ("Liverpool", "13", "9", "1", "3", "21", "8", "2.625", "19"),
        ("Manchester City", "14", "8", "3", "3", "19", "15", "1.267", "19"),
        ("Ipswich Town", "14", "8", "1", "5", "18", "9", "2.000", "17"),
        ("Everton", "14", "4", "9", "1", "19", "16", "1.188", "17"),
        ("Middlesbrough", "13", "6", "4", "3", "19", "14", "1.357", "16"),
        ("Stoke City", "13", "6", "4", "3", "20", "15", "1.333", "16"),
        ("Derby County", "14", "5", "6", "3", "21", "19", "1.105", "16"),
        ("Burnley", "14", "7", "1", "6", "23", "23", "1.000", "15"),
        ("Newcastle United", "13", "5", "5", "3", "19", "19", "1.000", "15"),
        ("West Ham United", "14", "5", "4", "5", "25", "22", "1.136", "14"),
        ("Birmingham City", "14", "6", "2", "6", "20", "20", "1.000", "14"),
        ("Wolverhampton Wanderers", "14", "4", "6", "4", "15", "15", "1.000", "14"),
        ("Sheffield United", "14", "5", "4", "5", "19", "24", "0.792", "14"),
        ("Carlisle United", "14", "5", "3", "6", "12", "12", "1.000", "13"),
        ("Coventry City", "13", "3", "6", "4", "18", "23", "0.783", "12"),
        ("Leeds United", "13", "4", "3", "6", "16", "15", "1.067", "11"),
        ("Chelsea", "13", "3", "5", "5", "13", "20", "0.650", "11"),
        ("Leicester City", "12", "3", "4", "5", "16", "18", "0.889", "10"),
        ("Tottenham Hotspur", "13", "4", "1", "8", "16", "20", "0.800", "9"),
        ("Queens Park Rangers", "13", "2", "5", "6", "11", "16", "0.688", "9"),
        ("Luton Town", "14", "1", "6", "7", "12", "21", "0.571", "8"),
        ("Arsenal", "13", "2", "3", "8", "12", "20", "0.600", "7"),
    ]

    ours = [
        (
            row["Team"], row["Played"], row["Won"], row["Drawn"], row["Lost"],
            row["GoalsFor"], row["GoalsAgainst"], row["GoalAverage"], row["Points"],
        )
        for row in table_for(PLAYED_BY_19_OCT)
    ]

    assert ours == published


def test_the_postponements_leave_clubs_on_unequal_games_by_19_october():
    # Two postponement clusters -- three round-9 fixtures and three round-13 --
    # and Leicester City were caught by both.
    table = table_for(PLAYED_BY_19_OCT)
    by_games = {row["Team"]: row["Played"] for row in table}

    assert by_games["Leicester City"] == "12"  # hit twice
    assert sorted(by_games.values()).count("13") == 10
    assert sorted(by_games.values()).count("14") == 11


def test_the_committed_calendar_week_output_is_what_the_tool_produces_today():
    produced = io.StringIO()

    assert main([str(PLAYED_BY_19_OCT)], stdout=produced) == EXIT_OK
    assert produced.getvalue() == STANDINGS_AS_OF_19_OCT.read_text()


def test_the_archive_tables_cannot_tell_the_two_rules_apart():
    """The limit of the external validation, asserted so it cannot be forgotten.

    It is tempting to present the 11v11 comparisons as proof that the historical
    rule is implemented. They are not, and this test pins down exactly why: in
    both archive-verified tables, ordering by goal average and ordering by goal
    difference produce the SAME table. Only the matchday-10 table can tell the
    two rules apart.

    So if someone "modernises" the sort, these two datasets stay green and only
    the matchday-10 tests go red. That is worth knowing, and worth writing down
    where the next reader will find it.
    """

    def ordered_by_goal_difference(results):
        """The same clubs, ranked by the MODERN rule instead."""
        table = table_for(results)
        return sorted(
            (row["Team"] for row in table),
            key=lambda team: (
                -int(next(r["Points"] for r in table if r["Team"] == team)),
                -(
                    int(next(r["GoalsFor"] for r in table if r["Team"] == team))
                    - int(next(r["GoalsAgainst"] for r in table if r["Team"] == team))
                ),
                team,
            ),
        )

    def ours(results):
        return [row["Team"] for row in table_for(results)]

    # The two tables an archive can check for us: both rules agree, so neither
    # comparison says anything at all about which rule we implemented.
    assert ours(PLAYED_BY_19_OCT) == ordered_by_goal_difference(PLAYED_BY_19_OCT)
    assert ours(PLAYED_BY_28_SEP) == ordered_by_goal_difference(PLAYED_BY_28_SEP)

    # The submitted table is the one that discriminates -- and it is the one no
    # archive publishes, which is precisely why the unit tests carry the weight.
    assert ours(ROUNDS_1_TO_10) != ordered_by_goal_difference(ROUNDS_1_TO_10)
