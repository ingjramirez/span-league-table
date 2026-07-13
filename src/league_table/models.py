"""The values the domain works in: a match result, and a row of the table."""

from dataclasses import dataclass

from league_table.rules import GoalAverage


@dataclass(frozen=True)
class Match:
    """One played match. A result, not a fixture: the score is known."""

    home_team: str
    away_team: str
    home_goals: int
    away_goals: int


@dataclass(frozen=True)
class Standing:
    """One club's row in the standing table.

    There is deliberately no goal-difference column. The 1974/75 table was
    published with goals for, goals against and goal average, and showing a
    difference alongside them would invite exactly the confusion this exercise
    is about.
    """

    position: int
    team: str
    played: int
    won: int
    drawn: int
    lost: int
    goals_for: int
    goals_against: int
    goal_average: GoalAverage
    points: int
