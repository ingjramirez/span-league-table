# League Standings — English First Division, 1974/75

CLI tool that reads football match results from CSV and prints a league standing table.
Built for the SPAN backend coding test (brief: `BE Coding Test 2026.pdf`).

## The rules are historical, not modern. This is the crux of the exercise.

The table MUST follow the rules in force in the English First Division in 1974/75.
Do not apply modern football conventions. Specifically:

- **2 points for a win, 1 for a draw, 0 for a loss.** Three points for a win was not
  introduced in England until 1981/82. Never use 3.
- **Ties on points are broken by goal AVERAGE, not goal difference.**
  Goal average = goals scored ÷ goals conceded (a ratio).
  Goal difference (GF − GA) did not replace goal average in the Football League until
  1976/77, so it is the wrong rule for this season.
  Both rules must be verified against a cited source before the sort is written, and the
  source cited in README.md.

If a change would make the table match modern rules, that is a signal the change is wrong.

## Known edge cases in goal average

- A team with 0 goals conceded gives a division by zero (undefined / infinite average).
- A team with 0 games played gives 0/0.
Both need a deliberate, documented decision — not an accidental one.

## Interpretation to state explicitly

"The 10th week of the season" is ambiguous (10 matchdays played vs. the 10th calendar week,
which differ once fixtures are rescheduled). Pick one, justify it in README.md, and keep the
tool general: it computes a table from whatever results it is given. Do not hard-code week 10.

## Design constraints

- Domain logic (points, goal average, sort order) MUST be separate from I/O (CSV, CLI), so
  the rules are unit-testable without touching the filesystem.
- Support both stdin/stdout and filenames as arguments.
- Malformed input: clear error message, non-zero exit code.
- Automated tests are mandatory. Include a test where goal average and goal difference would
  order two teams DIFFERENTLY — that test is the proof the historical rule is implemented.
- Do not commit installed packages (venv, node_modules, vendor).

## Submission artifacts (mandatory — a missing one fails the submission)

`README.md`, `CLAUDE.md`, `AI_REFLECTION.md`, `.claude/`, `ai/` (conversation history),
plus the input and output CSV files.
