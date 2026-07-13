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

The calendar-week file also turned out to be useful beyond completeness: 11v11 publishes the
real table for that date, and ours reproduces it exactly, which is about as good a check on the
match data as you can get.

Though not as good a check as I first claimed. See below.

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

And then, having written that paragraph, I did it again.

I'd said the 11v11 comparison was the strongest check in the repo, that if any part of the
implementation were wrong the table couldn't come out right. It sounded true. A reviewer tested
it by rewriting the sort to use goal difference — the exact modern-rules mistake this whole
exercise is built to catch — and regenerating everything. Two of the three tables came out
byte-identical. In both of the tables an archive can check for me, the two rules happen to
agree, so those comparisons validate the data thoroughly and the rule not at all. The only
table where the historical rule changes anything is the one no archive publishes.

I had it backwards, and I'd said so loudly, in the same document where I'd just finished
explaining that flattering claims deserve the click. Twice, with the lesson written down in
between.

What I'd actually change about how I worked, then, is not "check sources" — I did check sources.
It's that I never asked what my evidence would look like if I were wrong. The mutation test the
reviewer ran took about a minute and would have told me on day one that my headline validation
was blind to the thing it claimed to prove. It's now a test in the repo, asserting that those
two tables *can't* tell the rules apart, so nobody rebuilds the same false confidence later.
