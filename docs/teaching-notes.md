# Teaching notes

Practical things that are not in a module README.

## The scripts

Every module has a `scripts/` folder holding the course agent as it stands at the end of
that module. Learners build their own version during the session; the folder is what they
check against when theirs does not work. Each folder runs on its own, with no API key, and
prints the same numbers every time, so the numbers quoted in the READMEs are the numbers
the room will see.

Run every command from inside the module's `scripts/` folder. The ledger, the daily total
and the checkpoints are written relative to it. Deleting `ledger/` (and `checkpoints/` from
module 4 on) resets a module to zero.

## The iPad segments

The finished version of every diagram drawn live is in that module's `panels/` folder.
Draw it live rather than showing the finished panel, because the drawing is the pacing. The
finished panel exists so you can check yourself, and so the session still works if
somebody else teaches it.

## The dangerous commands

`--no-caps` in module 6 and in the capstone is the only genuinely risky thing in the
course, and only on the looping input. Keep the step ceiling on, run it once to prove the
alert fires, and stop it before you walk away from the machine. The model is simulated, so
here it costs nothing; on a real agent it would not be free.

Say that out loud when you demo it. People copy what they see.

## Pacing

The runtimes in each README are what the sessions actually take when the live drawing
happens at a normal speed. If you are running long, the command references and exercises
can be cut, but the iPad segments cannot: the drawing is where the ideas land.

## What to cut when you are short

Cut the command-reference walkthrough; it is in every README so nobody has to scrub back
through the video. Never cut the "turn it off" demonstrations. They are the only part that
changes anybody's mind.
