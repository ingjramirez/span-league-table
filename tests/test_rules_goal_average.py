"""Goal average: the 1974/75 tie-break, and the crux of this exercise.

Goal average is a RATIO -- goals scored divided by goals conceded. It is not
goal difference (goals scored minus goals conceded), which did not replace it
in the Football League until 1976/77.

The two rules do not merely differ in arithmetic; they can order the same two
clubs differently. `test_goal_average_and_goal_difference_disagree` below is
the proof that this codebase implements the historical rule. If someone
"modernises" the sort to goal difference, that test is what fails.
"""

from fractions import Fraction

import pytest

from league_table.rules import goal_average


def test_goal_average_is_goals_scored_divided_by_goals_conceded():
    assert goal_average(goals_for=10, goals_against=5).value == Fraction(2, 1)


def test_a_better_ratio_ranks_higher():
    assert goal_average(10, 5) > goal_average(10, 6)


def test_equal_ratios_compare_equal_even_when_the_goal_tallies_differ():
    # 2/1 and 4/2 are the same average; the raw tallies are irrelevant.
    assert goal_average(2, 1) == goal_average(4, 2)


# --------------------------------------------------------------------------
# The load-bearing test.
# --------------------------------------------------------------------------


def test_goal_average_and_goal_difference_disagree():
    """Two clubs where the historical rule and the modern rule swap the order.

        Rovers:  10 scored,  5 conceded -> average 2.00, difference +5
        United:  25 scored, 19 conceded -> average 1.32, difference +6

    Goal AVERAGE ranks Rovers above United. Goal DIFFERENCE would rank United
    above Rovers. Level on points, 1974/75 puts Rovers first.
    """
    rovers_for, rovers_against = 10, 5
    united_for, united_against = 25, 19

    rovers = goal_average(rovers_for, rovers_against)
    united = goal_average(united_for, united_against)

    # The historical rule: Rovers ahead.
    assert rovers > united

    # The modern rule would have said the opposite. Asserting this explicitly
    # keeps the test honest -- it proves the two rules really do disagree here,
    # so the assertion above cannot pass by coincidence.
    rovers_difference = rovers_for - rovers_against
    united_difference = united_for - united_against
    assert united_difference > rovers_difference


# --------------------------------------------------------------------------
# Edge cases. A ratio has two of them, and both are deliberate decisions.
# --------------------------------------------------------------------------


def test_conceding_nothing_ranks_above_every_finite_average():
    """A club that has conceded no goals divides by zero.

    The ratio is unbounded, so it outranks any finite average, however large.
    """
    unbeaten_defence = goal_average(goals_for=3, goals_against=0)

    assert unbeaten_defence > goal_average(1000, 1)
    assert unbeaten_defence.is_infinite


def test_all_infinite_averages_compare_equal():
    # 5/0 and 3/0 are both simply undefined-and-unbounded; neither is "better".
    assert goal_average(5, 0) == goal_average(3, 0)


def test_no_goals_either_way_is_undefined_and_ranks_below_every_finite_average():
    """0 scored and 0 conceded is 0/0 -- undefined, not zero.

    This is also the case for a club that has played no games at all. It cannot
    outrank a club that has actually achieved a ratio, so it sorts last.
    """
    undefined = goal_average(goals_for=0, goals_against=0)

    assert undefined.is_undefined
    assert undefined < goal_average(0, 1)  # even a club that only conceded
    assert undefined < goal_average(1, 1000)


def test_undefined_averages_compare_equal():
    assert goal_average(0, 0) == goal_average(0, 0)


def test_undefined_ranks_below_infinite():
    assert goal_average(0, 0) < goal_average(1, 0)


def test_scoring_nothing_but_conceding_is_a_real_ratio_of_zero():
    # 0/5 is a legitimate average of zero -- distinct from the 0/0 undefined
    # case above, and it still outranks undefined.
    scored_nothing = goal_average(0, 5)

    assert scored_nothing.value == Fraction(0, 1)
    assert not scored_nothing.is_undefined
    assert scored_nothing > goal_average(0, 0)


# --------------------------------------------------------------------------
# Exactness.
# --------------------------------------------------------------------------


def test_averages_are_exact_and_do_not_collapse_under_float_rounding():
    """Goal average is a Fraction, not a float.

    An in-principle test, and deliberately absurd: it takes goal counts no club
    could ever record to force a float64 collision. At real scorelines floats
    would cope fine -- 14/11 and 25/19 are separated by about fifteen digits.

    The point is not that floats would break on 1974/75 data. It is that with
    Fractions the ordering is exact by construction rather than exact by luck,
    and its correctness does not depend on how big the inputs happen to be.

    Both values below are 0.3333333333333333 in IEEE-754 double precision, so a
    float implementation calls them equal and mis-orders the clubs. Exactly,
    1/3 is the greater.
    """
    exact_third = goal_average(1, 3)
    just_under_a_third = goal_average(33_333_333_333_333_333, 100_000_000_000_000_000)

    assert float(exact_third.value) == float(just_under_a_third.value)  # floats agree
    assert exact_third > just_under_a_third  # fractions do not


# --------------------------------------------------------------------------
# Presentation.
# --------------------------------------------------------------------------


def test_a_finite_average_formats_to_three_decimal_places():
    assert str(goal_average(14, 11)) == "1.273"
    assert str(goal_average(18, 6)) == "3.000"


def test_the_edge_cases_format_readably():
    assert str(goal_average(3, 0)) == "inf"
    assert str(goal_average(0, 0)) == "n/a"


def test_str_matches_the_formatted_value():
    assert str(goal_average(14, 11)) == "1.273"
    assert str(goal_average(3, 0)) == "inf"


def test_repr_is_readable():
    assert repr(goal_average(18, 6)) == "GoalAverage(3.000)"


# --------------------------------------------------------------------------
# Behaving like a well-mannered value object.
# --------------------------------------------------------------------------


def test_equal_averages_hash_alike():
    # Lets averages be used in sets and as dict keys without surprises.
    assert hash(goal_average(2, 1)) == hash(goal_average(4, 2))
    assert len({goal_average(2, 1), goal_average(4, 2), goal_average(1, 2)}) == 2


def test_comparing_with_a_non_average_is_not_equal_rather_than_an_error():
    assert goal_average(2, 1) != "2.000"
    assert goal_average(2, 1) != 2


def test_ordering_against_a_non_average_is_a_type_error():
    # Refusing the comparison is safer than inventing an ordering for it.
    with pytest.raises(TypeError):
        goal_average(2, 1) < 2  # noqa: B015
