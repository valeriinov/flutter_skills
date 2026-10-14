# Reviewer recall

Measures how many of a pull request's known findings a review agent reports on its own. The
procedure carries no project data: pairs and expected findings live in the plan that runs it.

## Inputs

- A set of pairs, each: repository, `base` sha, `head` sha, and the expected findings —
  `file:line`, one line of essence, a bucket label.
- Per run: the review prompt and the subject it hands the reviewer — the range `<base>...<head>`,
  or a narrower diff the prompt supplies.
- The agent name — a parameter. The working reviewer and a candidate run by the same procedure,
  on the same pairs, with the same matching.
- The lens — an optional parameter: a paragraph appended to the prompt that restricts the run to
  some of the reviewer's criteria. A lens set is scored as the union of its runs on a pair, each
  expected finding counted once.
- Slices × passes — the search condition: the number of agents that split the range by layer
  times the number of passes over it, e.g. `4 × 2` or `8 × 1`. A condition is scored as the
  union of its runs on a pair, each expected finding counted once.

## Isolation

1. Per pair: `git -C <repo> worktree add --detach <dir outside the main tree> <head>`. The main
   tree holds the review documents and the plan; the worktree at `head` holds neither.
2. The prompt names the worktree as the only repository and the run's subject, and forbids
   reading `plan/` and any path outside the worktree.
3. The prompt carries no expected finding, no bucket and no hint drawn from the review documents.
4. After the run: `git worktree remove <dir>`. A run whose output cites a path under `plan/` or
   outside the worktree, a package cache included, is discarded and rerun.

## Runs

- At most 5 agents per batch; the next batch starts when the previous one has returned.
- Spread: some pairs run twice with the same agent and prompt; the spread is the difference
  between the two runs' found counts.
- The raw output of every run is kept beside the tables, one file per run.

## Matching

- A reported finding matches an expected one when it names the same file, a line within ±10 or
  the same symbol, and the same essence. Severity and wording do not matter.
- One reported finding may close several expected ones — a pattern finding listing every
  location closes each expected occurrence it names.
- An expected finding counts once, however many reported findings match it.
- Every reported finding that matches nothing is checked by the main session against the code at
  `head`. One that does not survive the check is extra; one that survives is a new true finding,
  listed under the table and counted in neither found nor extra.

## Table

One row per run, plus one union row per pair and lens set:

| pair | agent | lens | run | found per bucket | found / expected | extra | total output |
|---|---|---|---|---|---|---|---|

- lens — the lens name, `—` for a run without one, `union` for a lens set's row.
- found per bucket — matched expected findings, per bucket label.
- extra — reported findings that failed verification.
- total output — every finding the run reported.

Totals row: found / expected and extra / total output across all pairs. Spread row: per twice-run
pair, the two found counts and their difference.

## Synthetic case

Two cases, each run on its own.

Branch review checks that a review of a whole branch reaches code outside its last stage's
diff. Fixture: `fixtures/branch-review/`.

1. `bash fixtures/branch-review/build.sh [<dir>]` — builds a repository with an empty root
   commit and two stage commits, prints the range `<base>...<head>` and the dir.
2. Run the reviewer agent on the printed range, naming the printed dir as the only repository
   and forbidding any path outside it, as Isolation steps 2 and 4. The prompt carries nothing
   from `expect.md`.
3. Match its output against `fixtures/branch-review/expect.md` by the Matching rules above; the
   case passes when all four expected findings are found.

Fix regression checks that the one re-review after a fix catches a defect the fix brings in.
Fixture: `fixtures/fix-regression/`.

1. `bash fixtures/fix-regression/build.sh [<dir>]` — commits the code before the fix, lays the
   fix on top uncommitted, prints the head and the dir.
2. The snapshot is the one the re-review takes before fixing — `git stash create`, empty output
   → `HEAD`. On the built repository it is the printed head: the fix is already on top.
3. Run the reviewer agent over `git diff <head>` plus the untracked files read whole,
   Significant and above, with the isolation of the branch-review case. The prompt carries
   nothing from `expect.md`.
4. Match its output against `fixtures/fix-regression/expect.md` by the Matching rules above;
   the case passes when the one expected finding is found.
