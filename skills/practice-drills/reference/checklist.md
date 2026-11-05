# Quality checklist: practice-drills

## Curriculum
- [ ] Each drill rebuilds **one** mechanism that a practitioner must understand, mirrored from a named function in a pinned repo.
- [ ] Tracks go from foundations to integration; dependencies between drills are stated.
- [ ] Minutes and difficulty are honest (an expert can finish in about half the stated time).

## Code
- [ ] Solution module docstring = complete spec: every rule a test checks is written there.
- [ ] Solution comments explain why (invariants, ordering, what the naive version breaks, how the real code differs).
- [ ] `given` keeps boilerplate out of the learner's hour.
- [ ] `DRILL_IMPL=solutions ./check.sh all` passes.
- [ ] `./check.sh all` fails on **every** drill (no test passes on a stub).
- [ ] `gen_stubs.py drills.json --check` passes; stubs keep signatures and docstrings, and contain no answers.
- [ ] Tests are deterministic, CPU-only, fast (whole suite in seconds), and named after behaviours.
- [ ] Every pitfall listed on a hint page has a test that catches it.

## Pages
- [ ] Each hint page has: the drill in one minute · analogy · diagram · step-through · pitfalls · L1/L2/L3 · embedded solution · follow-ups with real-source links.
- [ ] Every number in examples and step-throughs was produced by running the solution.
- [ ] Knowledge pages explain the domain the drills need, with diagrams and pinned links, ending with "where the drills fit".
- [ ] `build_drills.py --strict` passes (links, files, symbols, diagram lint, quality minimums).
- [ ] **Every screenshot under `.shots/` was opened and looked at**; layouts fixed until clean.
- [ ] `--links` passes; the PDF builds; a few pages were spot-checked.

## Repo
- [ ] README with intro, quick start, layout, how to do a drill, progress table, rebuild command, license note.
- [ ] `.gitignore` excludes `.venv/`, caches, `.shots/`, temporary print files.
- [ ] Committed and pushed **only if asked**; if Pages was enabled, the live URL was checked.
