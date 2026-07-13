"""The scoring and ranking rules of the English First Division, 1974/75.

These are historical rules, not modern ones. See README.md for the sources.

Two rules matter and both differ from the modern game:

* Two points for a win, one for a draw. Three points for a win was not
  introduced in England until 1981/82.
* Clubs level on points are separated by goal AVERAGE (goals scored divided by
  goals conceded), not goal difference. Goal difference did not replace goal
  average in the Football League until 1976/77.

This module is pure: no I/O, no CSV, no filesystem.
"""

import functools
from fractions import Fraction
from typing import Optional, Tuple

POINTS_FOR_WIN = 2
POINTS_FOR_DRAW = 1
POINTS_FOR_LOSS = 0


def points_for_result(goals_for: int, goals_against: int) -> int:
    """Points a club earns from a single match with this scoreline."""
    if goals_for > goals_against:
        return POINTS_FOR_WIN
    if goals_for == goals_against:
        return POINTS_FOR_DRAW
    return POINTS_FOR_LOSS


# Ranking bands for the two degenerate cases of a ratio. A club that has
# conceded nothing has an unbounded average and so outranks every finite one; a
# club with no goals either way (including one that has played no games) has no
# average at all -- 0/0 -- and cannot outrank a club that achieved a real ratio.
# Both are deliberate choices, not accidents of arithmetic; see README.md.
_UNDEFINED = 0
_FINITE = 1
_INFINITE = 2


@functools.total_ordering
class GoalAverage:
    """Goals scored divided by goals conceded, as a totally ordered value.

    Held as a `Fraction`, never a float: averages like 14/11 and 25/19 are
    compared directly against one another, and float rounding would silently
    equate values that differ, mis-ordering the table.

    Greater is better, so these objects sort the way the league table reads.
    """

    __slots__ = ("_band", "_value")

    def __init__(self, goals_for: int, goals_against: int) -> None:
        if goals_against > 0:
            self._band = _FINITE
            self._value: Optional[Fraction] = Fraction(goals_for, goals_against)
        elif goals_for > 0:
            self._band = _INFINITE
            self._value = None
        else:
            self._band = _UNDEFINED
            self._value = None

    @property
    def value(self) -> Optional[Fraction]:
        """The exact ratio, or None where it is infinite or undefined."""
        return self._value

    @property
    def is_infinite(self) -> bool:
        """True when the club has scored but conceded nothing."""
        return self._band == _INFINITE

    @property
    def is_undefined(self) -> bool:
        """True when the club has neither scored nor conceded (0/0)."""
        return self._band == _UNDEFINED

    def sort_key(self) -> Tuple[int, Fraction]:
        """A plain (band, ratio) pair. Higher is better, in both elements.

        Both numbers negate cleanly, so a caller wanting descending order can
        simply negate them rather than wrap this in a reversing adapter.
        """
        ratio = Fraction(0) if self._value is None else self._value
        return (self._band, ratio)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GoalAverage):
            return NotImplemented
        return self.sort_key() == other.sort_key()

    def __lt__(self, other: "GoalAverage") -> bool:
        if not isinstance(other, GoalAverage):
            return NotImplemented
        return self.sort_key() < other.sort_key()

    def __hash__(self) -> int:
        return hash(self.sort_key())

    def __str__(self) -> str:
        if self._band == _INFINITE:
            return "inf"
        if self._band == _UNDEFINED:
            return "n/a"
        return f"{float(self._value):.3f}"

    def __repr__(self) -> str:
        return f"GoalAverage({self})"


def goal_average(goals_for: int, goals_against: int) -> GoalAverage:
    """The 1974/75 tie-break: goals scored divided by goals conceded.

    NOT goal difference. Goal difference did not replace goal average in the
    Football League until 1976/77 and is the wrong rule for this season.
    """
    return GoalAverage(goals_for, goals_against)
