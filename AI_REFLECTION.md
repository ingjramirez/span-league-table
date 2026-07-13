# AI Reflection

## The coverage gate made the AI delete a bug into existence

I asked for TDD and a 100% branch coverage gate. Those two things together caused the most
interesting failure of the session.

Partway through the sort, the coverage report flagged a method as never executed. Claude
reasoned that nothing would ever call it, concluded it was dead, and deleted it. The reasoning
sounded fine and was wrong. That method was quietly holding up the tie-break between clubs
level on points and goal average, and without it the order of those clubs became arbitrary.
Nothing crashed. The table just would have been slightly wrong in a way nobody would ever have
noticed.

The test I'd written first caught it in about ten seconds, which is the whole argument for TDD
in one incident. If we'd written the code first, I'm fairly sure the test would have been
written to match whatever the code did, and it would have shipped green.

What I took from it is narrower than "TDD good". An uncovered line is a question, not an
answer. It tells you no test touches this, which is just as consistent with "this is
load-bearing and nobody tested it" as with "this is dead". Claude resolved that ambiguity in
the direction that made the number go up, which is what you'd expect from anything you hand a
target to. I stopped treating the coverage gate as permission to delete code and started
treating it as a list of things to go and test.

A smaller version happened twice, the other way round: Claude wrote a test, the code disagreed,
and the code was right. Writing the test first doesn't make it correct. It just means you find
out early.

## Pushing back on "the 10th week"

Claude's first instinct was to read "the 10th week of the season" as ten matchdays and get on
with it. I didn't buy it, because that only works if fixtures land one per week, and I doubted
they had. They hadn't. The League played extra midweek rounds early on, so every club had ten
games in by late September, while the literal tenth calendar week doesn't arrive until the
middle of October. The two readings are almost a month apart.

I went with the matchday reading, but the decision that mattered was structural. The tool
doesn't know what a week is. It tabulates whatever file you give it, and the cut-off lives in
the data. So all three readings cost nothing to ship, and all three ship. A judgement call I
could have got wrong became one I didn't have to make irreversibly.

The calendar-week file turned out to be the most useful thing in the repo, because 11v11
publishes the real table for that date with its own goal average column, and ours reproduces it
exactly. That single comparison tests the data, the rules and the sort all at once.

## The part I'm least pleased about

I made Claude verify the historical rules against real sources before writing the sort, and
cross-check the scraped results against two archives rather than trusting the scrape. The rules
are the trap in this exercise: a beautifully tested implementation of goal difference is a wrong
answer, and it's wrong silently.

Then I fell for exactly the thing I'd been guarding against.

An agent told me worldfootball sorts its table by goal difference, which would neatly explain
why the two tables disagree about Liverpool. Nice story. The old rule, visible in the wild, on
the very season the exercise is about. I liked it enough to put it in the README and in this
document, and I never opened the page. A later review did, and it's false. Whatever explains
their row order, it isn't that, and the page I cited disproves it.

The data cross-check itself held up, which is what it was actually for. What didn't hold up was
my explanation of somebody else's table, taken from a model's summary because it was pleasing
and it confirmed the point I wanted to make. I deleted the claim rather than patch it. I don't
know what worldfootball sorts by and I don't need to.

So the lesson is smaller and more annoying than "verify things". A model's summary of a source
is not the source, and the more a claim flatters your argument, the more it deserves the click.
The match data got that scrutiny and survived. My favourite sentence in the write-up didn't,
and was wrong.
