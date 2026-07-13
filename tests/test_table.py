"""Building the standing table from a list of match results.

Pure domain: these tests never touch the filesystem, a CSV, or the CLI.
"""

from league_table.models import Match
from league_table.table import build_table


def played(home, away, home_goals, away_goals):
    return Match(
        home_team=home,
        away_team=away,
        home_goals=home_goals,
        away_goals=away_goals,
    )


def positions(table):
    return [row.team for row in table]


# --------------------------------------------------------------------------
# Aggregation.
# --------------------------------------------------------------------------


def test_no_matches_gives_an_empty_table():
    assert build_table([]) == []


def test_a_single_match_records_a_win_and_a_loss():
    table = build_table([played("Ipswich Town", "Chelsea", 3, 1)])

    winner, loser = table

    assert (winner.team, winner.played, winner.won, winner.drawn, winner.lost) == (
        "Ipswich Town",
        1,
        1,
        0,
        0,
    )
    assert (winner.goals_for, winner.goals_against, winner.points) == (3, 1, 2)

    assert (loser.team, loser.played, loser.won, loser.drawn, loser.lost) == (
        "Chelsea",
        1,
        0,
        0,
        1,
    )
    assert (loser.goals_for, loser.goals_against, loser.points) == (1, 3, 0)


def test_a_draw_gives_both_clubs_a_point():
    table = build_table([played("Arsenal", "Everton", 2, 2)])

    assert [(row.team, row.drawn, row.points) for row in table] == [
        ("Arsenal", 1, 1),
        ("Everton", 1, 1),
    ]


def test_a_club_accumulates_across_home_and_away_matches():
    table = build_table(
        [
            played("Liverpool", "Luton Town", 2, 0),  # home win
            played("Derby County", "Liverpool", 1, 1),  # away draw
            played("Liverpool", "Leeds United", 0, 3),  # home loss
        ]
    )

    liverpool = next(row for row in table if row.team == "Liverpool")

    assert (liverpool.played, liverpool.won, liverpool.drawn, liverpool.lost) == (3, 1, 1, 1)
    assert (liverpool.goals_for, liverpool.goals_against) == (3, 4)
    assert liverpool.points == 3  # one win (2) + one draw (1)


# --------------------------------------------------------------------------
# Ordering.
# --------------------------------------------------------------------------


def test_clubs_are_ordered_by_points_descending():
    table = build_table(
        [
            played("Stoke City", "Burnley", 1, 0),  # Stoke 2pts; Burnley 0
            played("Burnley", "Carlisle United", 1, 1),  # a point each
        ]
    )

    # Stoke top on 2 points. Burnley and Carlisle both finish on 1, and the
    # goal average splits them: Carlisle 1/1 = 1.000, Burnley 1/2 = 0.500.
    assert positions(table) == ["Stoke City", "Carlisle United", "Burnley"]
    assert [row.points for row in table] == [2, 1, 1]


def test_positions_are_numbered_from_one_in_table_order():
    table = build_table(
        [
            played("Stoke City", "Burnley", 1, 0),
            played("Carlisle United", "Chelsea", 3, 0),
        ]
    )

    # Pinning the clubs too, not just the numbers: asserting [1, 2, 3, 4] alone
    # would pass under any ordering at all, including a broken one.
    assert [(row.position, row.team) for row in table] == [
        (1, "Carlisle United"),  # 2 pts; won 3-0, so conceded nothing: average inf
        (2, "Stoke City"),  # 2 pts; won 1-0, also conceded nothing -- but 'C' < 'S'
        (3, "Burnley"),  # 0 pts, average 0.000
        (4, "Chelsea"),  # 0 pts, average 0.000, alphabetically after Burnley
    ]


# --------------------------------------------------------------------------
# The load-bearing test, at table level.
# --------------------------------------------------------------------------


def test_clubs_level_on_points_are_separated_by_goal_average_not_goal_difference():
    """The historical rule, exercised through the real sort.

    Both clubs finish on 2 points from one win each.

        Rovers beat a minnow    10-5  -> average 2.00, difference +5
        United won a shootout   25-19 -> average 1.32, difference +6

    Goal average puts Rovers first. Goal difference would put United first.
    1974/75 used goal average, so Rovers top the table.
    """
    table = build_table(
        [
            played("Rovers", "Minnows", 10, 5),
            played("United", "Wanderers", 25, 19),
        ]
    )

    assert positions(table)[:2] == ["Rovers", "United"]

    rovers, united = table[0], table[1]
    assert rovers.points == united.points == 2

    # Goal average agrees with the order above...
    assert rovers.goal_average > united.goal_average

    # ...and goal difference would have reversed it. Asserting the disagreement
    # explicitly is what stops this test passing by accident: if someone swaps
    # the sort to the modern rule, the ordering assertion above fails.
    rovers_difference = rovers.goals_for - rovers.goals_against
    united_difference = united.goals_for - united.goals_against
    assert united_difference > rovers_difference


def test_a_club_that_has_conceded_nothing_outranks_a_club_with_a_finite_average():
    # Level on points; the clean sheet gives an unbounded average.
    table = build_table(
        [
            played("Clean Sheets FC", "Hapless United", 1, 0),
            played("Leaky Rovers", "Feeble City", 9, 1),
        ]
    )

    assert positions(table)[:2] == ["Clean Sheets FC", "Leaky Rovers"]
    assert table[0].goal_average.is_infinite


def test_clubs_level_on_points_and_goal_average_fall_back_to_alphabetical_order():
    """The Football League had no further tie-break in 1974/75.

    Clubs level on both points and goal average genuinely shared the position.
    We order them alphabetically so the output is deterministic, and say so in
    the README rather than inventing a historical rule that did not exist.
    """
    table = build_table(
        [
            played("Zebras", "Wolves", 2, 1),
            played("Aardvarks", "Badgers", 2, 1),
        ]
    )

    assert positions(table)[:2] == ["Aardvarks", "Zebras"]
    assert table[0].points == table[1].points
    assert table[0].goal_average == table[1].goal_average
