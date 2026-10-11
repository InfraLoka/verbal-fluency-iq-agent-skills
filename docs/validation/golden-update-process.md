# Golden fixture update process

`tests/fixtures/golden_scores.json` pins end-to-end pipeline output for the
tracked sample texts so unintended scoring changes fail CI. Edge cases (short,
mixed en/id, empty, unpunctuated) are pinned in `tests/test_golden.py` with
synthetic text written for the purpose.

## When recapture is allowed

Recapture only when a deliberate, reviewed change to scoring, gates, norms,
weights or policy alters the output (for example a new policy version or a
changed component formula). Never recapture to make a failing test pass
without understanding the diff. A dependency or model upgrade that moves
scores also counts as a scoring change and needs the same review.

## Process

1. Make the scoring change in its own commit, with tests, and state why the
   golden values should move.
2. Run `scripts/capture_golden.py` to rewrite the fixture.
3. Inspect `git diff tests/fixtures/golden_scores.json`. Every changed key must
   be explained by the scoring change; unexplained movement is a bug.
4. Put a summary of the diff (which sources, which keys, old to new values) in
   the commit message.
5. A second maintainer reviews the fixture diff and the commit message before
   merge. The author of the scoring change must not be the only reviewer.

## Never from personal data

Golden sources must be synthetic or openly licensed text that the project may
redistribute. Never capture from private or personal corpora (for example
`example/rahmat/`); `test_golden_sources_exclude_untracked_personal_corpus`
enforces this for the source list. Edge-case inputs are generated inline and
must not quote any real person.
