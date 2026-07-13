"""The 1974/75 points system: 2 for a win, 1 for a draw, 0 for a loss.

Three points for a win was not introduced in England until 1981/82, so a `3`
appearing anywhere in these expectations is a bug, not an update.
"""

import pytest

from league_table.rules import POINTS_FOR_DRAW, POINTS_FOR_WIN, points_for_result


def test_a_win_is_worth_two_points():
    assert points_for_result(goals_for=3, goals_against=1) == 2


def test_a_draw_is_worth_one_point():
    assert points_for_result(goals_for=2, goals_against=2) == 1


def test_a_loss_is_worth_no_points():
    assert points_for_result(goals_for=0, goals_against=1) == 0


def test_a_goalless_draw_is_still_worth_one_point():
    assert points_for_result(goals_for=0, goals_against=0) == 1


@pytest.mark.parametrize(
    ("goals_for", "goals_against", "expected"),
    [(1, 0, 2), (0, 1, 0), (5, 4, 2), (4, 5, 0), (9, 9, 1)],
)
def test_points_across_a_range_of_scorelines(goals_for, goals_against, expected):
    assert points_for_result(goals_for, goals_against) == expected


def test_the_win_and_draw_values_are_the_historical_ones():
    # Guards against a well-meaning "modernisation" of the constants.
    assert (POINTS_FOR_WIN, POINTS_FOR_DRAW) == (2, 1)
