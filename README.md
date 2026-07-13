# League Standings — English First Division, 1974/75

A command-line tool that reads football results from CSV and prints a league standing
table, using the rules in force in the English First Division in the 1974/75 season.

The tool is general: it tabulates whatever results it is given. It knows nothing about
weeks, matchdays or 1974 — those live in the data, not the code.

```
$ league-table --pretty data/results_1974-75_rounds_1-10.csv
Pos  Team                      P  W  D  L   F   A   GAvg  Pts
  1  Ipswich Town             10  8  0  2  18   6  3.000   16
  2  Newcastle United         10  6  2  2  19  14  1.357   14
  3  Manchester City          10  6  2  2  14  11  1.273   14
  4  Middlesbrough            10  5  3  2  15   7  2.143   13
  5  Liverpool                10  6  1  3  17   8  2.125   13
  ...
```

## Setup

Python 3.9+. No runtime dependencies; the tool itself is pure standard library.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .                     # installs the `league-table` command
pip install -r requirements-dev.txt  # pytest + coverage, for the tests
```

## Usage

Filenames, stdin/stdout, or any mixture of the two:

```bash
league-table results.csv                     # file   -> stdout
league-table results.csv -o standings.csv    # file   -> file
cat results.csv | league-table               # stdin  -> stdout  (a plain unix filter)
league-table --pretty results.csv            # aligned text instead of CSV
python -m league_table results.csv           # without installing the console script
```

**Input** needs four columns — `home_team`, `away_team`, `home_goals`, `away_goals` — in
any order. Any other column is ignored, which is how the shipped data files can carry
`round` and `date` for a human's benefit while the tool stays ignorant of matchdays.

```csv
round,date,home_team,away_team,home_goals,away_goals
1,1974-08-17,Stoke City,Leeds United,3,0
```

**Output** is the table in the conventional column order:

```csv
Position,Team,Played,Won,Drawn,Lost,GoalsFor,GoalsAgainst,GoalAverage,Points
1,Ipswich Town,10,8,0,2,18,6,3.000,16
```

Malformed input is rejected with a message on stderr naming the offending line. Nothing is
written to the output on failure — no half-written table, and an in-place rewrite
(`league-table results.csv -o results.csv`) is safe, because the table is rendered to memory
before the output is opened.

| exit | meaning |
|---|---|
| 0 | the table was written |
| 2 | the input could not be read: bad CSV, missing/duplicated column, bad score, missing file |
| 141 | stdout was closed early (`\| head`), the conventional 128 + SIGPIPE |

The parser rejects anything it cannot read *unambiguously* rather than guessing: a required
column named twice, a row with the wrong number of fields, a score that is not a plain run
of ASCII digits. (Python's own `int()` would accept `"1_0"` as 10 and non-ASCII digits as
numbers — either would silently put wrong goals in the table, which is worse than an error.)
Input is decoded as `utf-8-sig`, so the byte-order mark Excel and Google Sheets write by
default does not make the first column unreadable.

Two things are *suspicious* rather than wrong, so they warn on stderr and still produce a
table (exit 0):

- **A repeated fixture.** The same pairing twice is the likeliest corruption in a results
  feed — but some leagues genuinely play the same fixture twice at the same ground, and this
  tool tabulates whatever league it is given. Every occurrence is counted, and said so.
- **Club names differing only by case.** `Arsenal` and `ARSENAL` are one club in any league
  that ever existed, and left alone they become two rows with half a season each. We do not
  merge them — the tool does not guess what a name *means* — but a silent split is exactly
  the confidently-wrong output everything else here exists to prevent.

Both are deliberate: refuse what cannot be read, warn about what can be read but looks wrong,
and never quietly produce a plausible table from bad data.

## The rules, and why they are not the modern ones

This is the crux of the exercise. Two rules differ from the modern game, and both were
verified against sources before the sort was written.

### Two points for a win, one for a draw, none for a loss

Three points for a win was **not** introduced in England until 1981/82. Wikipedia's
[1981–82 Football League][1981-82] page: *"This was the first league season with three
points for a win."* 1974/75 predates it, so a win is worth two.

### Clubs level on points are separated by goal AVERAGE, not goal difference

Goal average is a **ratio** — goals scored ÷ goals conceded. Goal difference (scored −
conceded) did not replace it in the Football League until 1976/77. Wikipedia's
[1974–75 Football League][1974-75] page:

> Beginning with the season 1894–95, clubs finishing level on points were separated
> according to goal average (goals scored divided by goals conceded)... The goal average
> system was eventually scrapped beginning with the 1976–77 season.

1974/75 sits squarely inside the goal-average era.

**This is not a technicality — it changes the submitted table.** Middlesbrough and
Liverpool both finish matchday 10 on 13 points:

| | scored | conceded | goal average | goal difference |
|---|---|---|---|---|
| Middlesbrough | 15 | 7 | **2.143** | +8 |
| Liverpool | 17 | 8 | 2.125 | **+9** |

Goal average puts Middlesbrough 4th and Liverpool 5th. The modern rule would swap them.
Lower down it is starker still: Tottenham, Arsenal and QPR all end matchday 10 on 6 points
*and* an identical −5 goal difference — the modern rule cannot separate them at all, while
goal average orders them 0.706 / 0.667 / 0.615.

Both cases are locked down by tests in `tests/test_1974_75_season.py`.

### No further tie-break

The Football League had none in 1974/75: clubs level on both points and goal average
genuinely shared the position. The tool falls back to alphabetical order purely so the
output is deterministic. That is a presentation choice, not a historical rule, and it is
marked as such in the code.

## Goal average has two edge cases. Both are deliberate.

A ratio has a denominator, so it can misbehave in ways a difference cannot:

| case | arithmetic | decision | printed |
|---|---|---|---|
| Conceded nothing, scored something | division by zero | unbounded — ranks **above** every finite average | `inf` |
| Neither scored nor conceded (incl. a club with no games) | 0 ÷ 0 | undefined — ranks **below** every finite average | `n/a` |

The reasoning: a club that has conceded nothing has an average better than any club that
has conceded, however many goals it scored — so it sorts top. A club with no goals either
way has no average at all; it has achieved nothing to be ranked *by*, so it cannot outrank
a club that has, and it sorts bottom. Note that 0 scored against 5 conceded is a **real**
average of 0.000, quite distinct from the undefined 0/0 case.

The uncomfortable consequence, stated rather than hidden: an undefined club sorts below a
club with a genuine average of 0.000 — so a club that has *lost* can finish above a club
that is unbeaten, if they are level on points.

```
Pos  Team         P  W  D  L  F  A   GAvg  Pts
  3  Beaten FC    2  0  1  1  0  2  0.000    1   <- lost a game
  4  Unbeaten FC  1  0  1  0  0  0    n/a    1   <- unbeaten, but 0/0
```

Banding 0/0 with 0.000 instead does not rescue it: the two would then tie on average and
fall to the alphabetical tie-break, with Beaten FC still ahead. The case is genuinely
degenerate — it needs a goalless club, and it cannot arise in a league where every club has
scored or conceded at least once, as all 22 had by matchday 10 of 1974/75. We picked the
reading we could defend and wrote a test for it, rather than letting the sort decide by
accident.

Averages are held as exact `Fraction`s, never floats — but the honest reason is narrower
than "floats would break it". At football scorelines they would not: a `float64` separates
14/11 from 25/19 with about fifteen digits to spare, and no club will ever score enough
goals to collide. `Fraction` is used so that the *correctness of the ordering does not
depend on the magnitude of the inputs at all* — the sort is exact by construction rather
than exact by luck, and nobody has to reason about ULPs to know the table is right. The
test that demonstrates the difference (`test_averages_are_exact_and_do_not_collapse_under_
float_rounding`) necessarily uses absurd goal counts to force a float collision, and is
labelled as the in-principle argument it is.

## "The 10th week of the season" is ambiguous. Here is the reading, and the alternative.

The season kicked off on Saturday 17 August 1974. The Football League squeezed extra
midweek rounds into the opening weeks (19–21 Aug, 27–28 Aug, 31 Aug), so the two natural
readings of "the 10th week" fall almost a month apart:

- **After 10 matchdays** — every club has played 10 games, reached on Saturday 28 September 1974.
- **The 10th calendar week** — 19–25 October 1974, closing after Round 14 on Saturday the 19th,
  by which point clubs had played 12 to 14 games.

**We use the matchday reading**, for three reasons:

1. It is the ordinary football usage. "Week 10", "gameweek 10" and "matchweek 10" all mean
   *ten rounds played*. Nobody describes the 19 October 1974 table as "the 10th week".
2. The calendar reading is not even well-defined. Is a week Saturday-to-Friday from kickoff,
   or Monday-to-Sunday? Moving the boundary two days moves the answer from round 13 to round
   14 — a different table. A rule that fragile cannot be the intended one.
3. It is the reading under which every club has played the same number of games, so the
   table can be read straight down without mentally adjusting for games in hand.

That third point is a convenience, not a principle — real First Division tables were
published mid-week with clubs on unequal games played all the time, and the 11v11 table
cited below is exactly that. It is a reason to *lead* with the matchday table, not a reason
the other one is wrong, which is why both are shipped.

### All three readings are shipped

Within the matchday reading there is one further wrinkle worth being honest about. Three
round-9 fixtures were postponed and actually played months later — Leeds v Tottenham
(4 Dec 1974), Middlesbrough v Leicester (10 Dec 1974) and Newcastle v Arsenal (23 Apr 1975).
A "rounds 1–10" table therefore includes three results that were not on the pitch in
September.

So rather than argue the ambiguity and pick one in private, every reading is in the repo as
an input/output pair. The same binary produces all three — only the input differs, which is
the whole point of keeping the week out of the code.

| input | output | what it is |
|---|---|---|
| `results_1974-75_rounds_1-10.csv` (110 matches) | `standings_1974-75_after_matchday_10.csv` | **The submitted answer.** Ten matchdays complete; all clubs P=10. |
| `results_1974-75_played_by_1974-09-28.csv` (107 matches) | `standings_1974-75_as_of_1974-09-28.csv` | The table as it actually stood on matchday 10's evening: six clubs on P=9. |
| `results_1974-75_played_by_1974-10-19.csv` (148 matches) | `standings_1974-75_as_of_1974-10-19.csv` | The **10th calendar week**, ending Sat 19 Oct 1974. Clubs on 12–14 games. |

The honest tension, since it cuts against the file we lead with: the matchday-10 table
contains three results that had not been played in September — one of them not until April
1975. It is a *reconstruction* of a ten-game table, not a table anyone could have printed at
the time. We lead with it because "the 10th week" most naturally means ten rounds played,
and because it is the table the archives reproduce — but a reviewer who reads the brief the
other way will find their table here too, computed by the same code.

### The calendar-week table validates the data — and, pointedly, not the rule

The 19 October 1974 table is worth more than completeness. [11v11 publishes the table for
that exact date][11v11-19oct], and — unusually — prints its own **goal average** column.
Our output reproduces it **exactly: all 22 rows, in the same order, with the same goal
averages to three decimal places.**

```
Pos  Team                P   W  D  L   F   A   GAvg  Pts
  1  Liverpool           13  9  1  3  21   8  2.625   19     <- 13 games
  2  Manchester City     14  8  3  3  19  15  1.267   19     <- 14 games
  3  Ipswich Town        14  8  1  5  18   9  2.000   17
  4  Everton             14  4  9  1  19  16  1.188   17
  ...
 18  Leicester City      12  3  4  5  16  18  0.889   10     <- 12 games
```

That comparison validates the match data, the two-point rule, the goal-average *arithmetic*,
and the handling of clubs on unequal games played (six postponed fixtures leave Leicester on
12 and ten clubs on 13). Liverpool top it on 19 points from **thirteen** games while
Manchester City have 19 from **fourteen** — an ordering only a ratio produces.

**What it does not validate is the tie-break rule itself, and it would be dishonest to imply
otherwise.** In this particular table goal average and goal difference never actually
disagree: sort the same results by goal difference and the output is *byte-identical*. The
same is true of the 28 September table. So both externally-verified tables check the data
exhaustively and the sort not at all.

The one table where the historical rule changes the answer is the matchday-10 reconstruction
— where Middlesbrough and Liverpool swap — and that is precisely the table no archive
publishes, so its ordering rests on our reading of the sources above rather than on a
published table. That is the honest epistemic position:

| | what it proves | what it doesn't |
|---|---|---|
| 11v11 comparisons (28 Sep, 19 Oct) | the data, the points, the arithmetic | nothing about goal average vs goal difference |
| Matchday-10 table + unit tests | the historical rule changes real positions | — |

The rule is defended by `test_goal_average_and_goal_difference_disagree` and by the
matchday-10 assertions, *not* by the archive comparisons. We found this out by mutating the
sort to goal difference and watching two of the three outputs come out unchanged.

(One further thing we do *not* claim: in the two cases where clubs tie on both points and
goal average — Burnley/Newcastle on 1.000, Birmingham/Wolverhampton on 1.000 — our
alphabetical fallback happens to agree with 11v11's order. But goals-scored would order both
pairs the same way, so this data cannot tell us which rule 11v11 applies, and we do not
pretend it does.)

## Tests

```bash
pytest
```

101 tests. The suite enforces **100% branch coverage** and fails below it; the only excluded
line in the codebase is the `if __name__ == "__main__":` process entry point, which cannot
be exercised in-process.

Coverage is a floor, not a goal — and it is not enough on its own. A QA review of this repo
found the `--pretty` formatter was *executed* by the tests but never *asserted on*: swapping
its `ljust`/`rjust` wrecked the layout and every test still passed. It is now pinned
character for character. Several real bugs hid behind a green 100% bar (a duplicated CSV
column silently producing wrong numbers; a BOM making a valid file unreadable; wrong line
numbers in errors; a `BrokenPipeError` traceback when piped to `head`). All are fixed, and
each has a test that fails without the fix.

The tests that actually protect this submission are:

- `test_goal_average_and_goal_difference_disagree` — two clubs the historical rule and the
  modern rule order **differently**. It asserts the disagreement explicitly, so it cannot
  pass by coincidence. If someone "modernises" the sort, this is what fails.
- `test_goal_average_reorders_the_real_1974_75_table_against_goal_difference` — the same
  thing, in the real season, on the real submitted table.
- `test_the_tenth_calendar_week_table_matches_11v11s_published_table_exactly` — all 22 rows of
  a **published historical table**, reproduced exactly: same order, same goal averages, clubs
  on unequal games played. It validates the data, not the tie-break rule.
- `test_the_archive_tables_cannot_tell_the_two_rules_apart` — the limit of that validation,
  asserted so it cannot quietly be forgotten: both archive-verified tables come out identical
  under goal difference, so only the matchday-10 table can prove which rule we implemented.
- `test_averages_are_exact_and_do_not_collapse_under_float_rounding` — fails under a float
  implementation.
- The goal-average edge cases, the CSV failure modes and exit codes, and a golden test
  pinning the committed output files to what the tool produces today.
- The adversarial cases a review turned up: a duplicated header column, a row wider than its
  header, a BOM, a non-UTF-8 file, a club name containing a newline (which breaks naive line
  counting), scores like `"1_0"` that `int()` would silently accept, and a closed pipe.

## Design

```
src/league_table/
  rules.py    # the 1974/75 rules: points, goal average, ordering. Pure; no I/O.
  models.py   # Match, Standing
  table.py    # results -> standing table. Pure; no I/O.
  csvio.py    # all the CSV parsing and writing
  cli.py      # argument parsing and streams
```

The domain (`rules.py`, `table.py`, `models.py`) never touches the filesystem, so the
historical rules are unit-testable without a CSV in sight — and the rules are stated once,
in one file, where they can be checked against a source.

`Standing` deliberately has **no goal-difference column**. The 1974/75 table was published
with goals for, goals against and goal average; printing a difference beside them would
invite exactly the confusion this exercise is about.

## Data provenance

Match results were taken from [worldfootball.net's 1974/75 fixture archive][worldfootball]
(rounds 1–14, 154 matches) and validated on the way in: 11 matches per round, each of the 22
clubs appearing exactly once per round, and the club list an exact set-match with the 22
clubs in Wikipedia's [final 1974–75 First Division table][1974-75]. Every match carries the
date it was **actually played**, not its nominal matchday — six fixtures were postponed
(three from round 9, three from round 13) and played as late as April 1975, which is what
makes the date-based cut-offs meaningful.

The computed table was then checked against two independent sources:

- **[worldfootball.net's matchday-10 table][wf-md10]** (all 22 clubs on P=10): every club
  agrees on played, won, drawn, lost, goals for, goals against and points. Its *row order*
  differs from ours — it shows Liverpool 7th where we have them 4th — but we deliberately
  do not lean on its ordering, only its numbers. (Most of its points-blocks are ordered by
  goal difference, but the 13-point block matches neither goal difference nor goal average,
  so we make no claim about what rule it applies.)
- **[11v11's table for 28 September 1974][11v11]** (date-based, so six clubs show P=9): all
  sixteen clubs on P=10 agree exactly, and 11v11's own goal-average column matches ours to
  three decimal places. The six P=9 clubs differ from ours by precisely one result each,
  with no leftover goals or points — those deltas reconstruct exactly the three postponed
  round-9 fixtures listed above, so the two datasets corroborate one another.

[1974-75]: https://en.wikipedia.org/wiki/1974%E2%80%9375_Football_League
[1981-82]: https://en.wikipedia.org/wiki/1981%E2%80%9382_Football_League
[worldfootball]: https://www.worldfootball.net/all_matches/eng-premier-league-1974-1975/
[wf-md10]: https://www.worldfootball.net/schedule/eng-premier-league-1974-1975-spieltag/10/
[11v11]: https://www.11v11.com/league-tables/league-division-one/28-september-1974/
[11v11-19oct]: https://www.11v11.com/league-tables/league-division-one/19-october-1974/
