# AI Reflection

## Where the AI went wrong: it deleted code that coverage said was dead

We worked test-first and I asked for 100% branch coverage as a gate. That combination
produced the most instructive failure of the session, and it was caused by the coverage
target itself.

While building the sort, the coverage report flagged one uncovered line: the `__eq__`
method on a small private wrapper class used to sort goal averages in descending order.
The AI reasoned — plausibly, and out loud — that `sorted()` only ever calls `__lt__`, so
`__eq__` was dead code, and deleted it rather than annotate it with a `# pragma: no cover`.
That reasoning is wrong, and subtly so. Python compares tuples element by element, using
`==` to decide whether to move on to the next element. With `__eq__` gone, two clubs with
*identical* goal averages compared as unequal (falling back to identity), so the sort never
reached the third element of the key — the club name — and the alphabetical tie-break
became silently unreachable. Nothing would have crashed. The table would just have been
quietly non-deterministic for clubs level on both points and goal average.

The test I had insisted on writing first caught it in about ten seconds, and that is the
whole point. Had we written the code first and the tests after, I am fairly sure the test
would have been written to match the behaviour rather than the rule, and the bug would have
shipped green. What I took from it: an uncovered line is a *question*, not a verdict. It
means "no test exercises this", which is exactly as consistent with "this is load-bearing
and untested" as with "this is dead". The AI collapsed that ambiguity in the direction that
made the number go up. I now treat a coverage gate as something that generates work, not
something that licenses deletion — and the restored `__eq__` carries a comment explaining
why it exists, so the next person (or model) doesn't make the same cut.

A smaller version of the same thing happened twice more. The AI wrote a test asserting
Burnley would finish above Carlisle; the code disagreed, and the code was right — goal
average separated them and the *test* was the thing that was wrong. Writing tests first
does not make them correct, it just makes the disagreement surface early enough to be
interesting.

## Where I pushed back: "the 10th week" is not the 10th matchday, necessarily

The AI's first instinct — and a reasonable one — was to read "the 10th week of the season"
as "after 10 matchdays" and get on with it. I pushed on that, because the two readings only
coincide if fixtures fall one per week, and I did not believe they had. Forcing the actual
dates out of the data proved they had not: the League played extra midweek rounds in the
opening fortnight, so all 22 clubs had played 10 games by 28 September 1974, only six
calendar weeks in, and the literal 10th calendar week lands in *late October*, by which
point clubs had played thirteen or fourteen. The ambiguity was real and worth about ten
minutes of argument.

I settled on the matchday reading, and the README argues it on three grounds rather than
asserting it. But the more useful decision was structural: since the tool is general and
the week lives in the data rather than the code, both cut-offs cost nothing to ship, so
both ship — the rounds 1–10 table as the submitted answer, and the "as it actually stood on
28 September" table alongside it, six clubs still on nine games because their round-9
fixtures were postponed to December and April. Making the tool ignorant of matchdays turned
a judgement call I could have got wrong into a judgement call I did not have to make
irreversibly.

## What I would not let the AI skip: proving the data, not just the code

The historical rules were verified against cited sources before the sort was written, which
is the part of this exercise that is actually load-bearing — a beautifully tested
implementation of *goal difference* would be a wrong answer, and it would be wrong silently.
But I also wanted the *data* proved, not just the rules. The results were scraped, and
scraped through a third-party text proxy at that, because the archive blocks plain HTTP
clients; that is transport, not provenance, and it is exactly the sort of detail that gets
waved through. So the computed table was cross-checked row by row against two independent
sources — worldfootball's own matchday-10 table and 11v11's date-based table for 28
September 1974 — and they agree on every club's played, won, drawn, lost, goals for, goals
against and points. The six clubs where 11v11 disagrees are precisely the six affected by
the postponements, each differing by exactly one result with no leftover goals. The two
datasets corroborate each other.

And then I got caught by exactly the thing I had just congratulated myself on avoiding.

The verification agent reported that worldfootball *displays* its table sorted by goal
difference, which would neatly explain why Liverpool sits 7th there and 4th in ours. It is a
lovely story — the historical rule, visible in the wild, on the very season the exercise
asks about — and I wrote it into both the README and this document without opening the page.
A second review checked it and it is false: in worldfootball's 13-point block, Liverpool are
*last* on a goal difference of +9, below Middlesbrough (+8), Everton (+3) and Sheffield
United (0). Goal-difference sorting would have put them first in that block. Whatever
explains their row order, it is not the tidy story I told, and I had cited the page that
disproves it.

The data cross-check itself survived — the numbers do agree, club by club, and that is what
the verification was for. What did not survive was my explanation of someone else's table,
which I had accepted from a model summary because it was pleasing and confirmed the point I
wanted to make. That is the whole failure mode this exercise is about, committed by me, in
the paragraph claiming I don't commit it. I have removed the claim rather than patch it,
because I do not know what worldfootball sorts by and have no need to.

The lesson I actually take from the session is narrower than "verify things". It is:
**an AI's summary of a source is not the source**, and the more a claim flatters your
argument, the more it deserves the click. The match data got that treatment and held up. My
favourite sentence in the write-up did not get it, and was wrong.

It is also why the load-bearing test in this repo does not merely assert an ordering: it
asserts that goal average and goal difference *disagree* about the pair, so it cannot pass
by coincidence, and anyone who "modernises" the sort gets a red test rather than a plausible
table.
