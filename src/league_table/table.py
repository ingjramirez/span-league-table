"""Turning a list of match results into a standing table.

Pure domain: no I/O. The rules it applies live in `rules.py`.

The tool knows nothing about weeks, matchdays or the 1974/75 season. It
tabulates whatever results it is given; deciding *which* results constitute
"the 10th week" is the caller's business, and is discussed in README.md.
"""

from typing import Dict, Iterable, List, Tuple

from league_table.models import Match, Standing
from league_table.rules import goal_average, points_for_result


class _Tally:
    """A club's running totals while the results are being read."""

    __slots__ = ("won", "drawn", "lost", "goals_for", "goals_against", "points")

    def __init__(self) -> None:
        self.won = 0
        self.drawn = 0
        self.lost = 0
        self.goals_for = 0
        self.goals_against = 0
        self.points = 0

    def record(self, scored: int, conceded: int) -> None:
        self.goals_for += scored
        self.goals_against += conceded
        self.points += points_for_result(scored, conceded)

        if scored > conceded:
            self.won += 1
        elif scored == conceded:
            self.drawn += 1
        else:
            self.lost += 1

    @property
    def played(self) -> int:
        return self.won + self.drawn + self.lost


def _ranking_key(entry: Tuple[str, _Tally]):
    """The 1974/75 order: points, then goal average, then club name.

    Points and the goal average both sort descending -- higher is better -- and
    both are plain numbers, so they are simply negated. The club name breaks the
    remaining ties ascending.

    The name is not a historical rule. The Football League had no tie-break
    beyond goal average; clubs level on both genuinely shared the position. It is
    here so the output is deterministic, and it is documented as such.
    """
    team, tally = entry
    band, ratio = goal_average(tally.goals_for, tally.goals_against).sort_key()
    return (-tally.points, -band, -ratio, team)


def build_table(matches: Iterable[Match]) -> List[Standing]:
    """The standing table for these results, best club first."""
    tallies: Dict[str, _Tally] = {}

    for match in matches:
        home = tallies.setdefault(match.home_team, _Tally())
        away = tallies.setdefault(match.away_team, _Tally())

        home.record(match.home_goals, match.away_goals)
        away.record(match.away_goals, match.home_goals)

    ranked = sorted(tallies.items(), key=_ranking_key)

    return [
        Standing(
            position=position,
            team=team,
            played=tally.played,
            won=tally.won,
            drawn=tally.drawn,
            lost=tally.lost,
            goals_for=tally.goals_for,
            goals_against=tally.goals_against,
            goal_average=goal_average(tally.goals_for, tally.goals_against),
            points=tally.points,
        )
        for position, (team, tally) in enumerate(ranked, start=1)
    ]
