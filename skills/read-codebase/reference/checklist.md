# Quality checklist: read-codebase

Go through this before replying. Every item has bitten a previous report.

## Content
- [ ] The **requirements / goals / constraints** table exists, and every later chapter visibly answers one of its rows.
- [ ] Every major component chapter answers: role · why it's hard · how it works · contracts · connections · gotchas.
- [ ] One **end-to-end lifecycle** follows a concrete request through all components, marking which hops are in which repo or not public.
- [ ] Non-obvious defaults and behaviours were read from the code (config defaults, middleware order, lazy loading), not assumed.
- [ ] Anything inferred rather than read is labelled as such.
- [ ] History claims (license changes, renames, removals) were verified with the GitHub API or old-SHA files.
- [ ] "What is not in the repo" (closed backends, SaaS, generated code) is stated where it matters for customizing.
- [ ] License chapter (if the reader may fork, ship or host): every part's license with evidence, scenario table, exceptions (assets, icons, trademarks, CLA), history, "not legal advice".
- [ ] Contributing chapter: setup commands that exist, the project's review rules, good first areas, customization routes.
- [ ] No filler sentences; no file-by-file tree dumps.

## Diagrams
- [ ] 8–16 diagrams for a medium project; each has a caption saying what to notice, with a source link.
- [ ] `--strict` build passes (no overlap, overflow, label-gap or link errors).
- [ ] **Every screenshot in `.shots/` was opened and looked at**: no edge through a node, no label on a node, no crossings that a node move would remove, arrows point the right way.
- [ ] Lifecycles that unfold over time use `::: steps` with highlights.

## Links and analogies
- [ ] 60–150 pinned source links; concrete claims have one next to them.
- [ ] `--links` passes (every external URL answers 200).
- [ ] 2–4 analogies, each with an explicit mapping, each next to the mechanism it explains.

## Output
- [ ] `report.html` and `report.pdf` exist in the output folder (not inside the analyzed repo).
- [ ] PDF page count is sane, and a few pages were spot-checked (diagrams render, tables not cut).
- [ ] Final reply: paths, chapter summary, pinned SHAs, what was verified, anything unverified. No commit or push unless asked.
