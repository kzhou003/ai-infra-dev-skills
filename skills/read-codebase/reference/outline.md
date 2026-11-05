# Report outline (code-wiki style)

Use `##` for chapters (each starts a new PDF page) and `###` for sections; both appear in the left table of contents. Adapt the names, keep the spine.

## 0. How to read this report (short)
Who it is for, what they will be able to do afterwards, the chapter order in one list, and the pinned versions in a `::: callout key` box.

## 1. The big picture: problem, goals, constraints
- **What problem exists without this project?** Two to four rows in a table: stage, problem, who solves it.
- **One overview diagram**: the system and its neighbours (users, upstream data, external services, other repos), with open-source and closed parts visually distinct (`k=dark` for closed or external).
- **Requirements / goals / constraints matrix**: a table with one column per project (or per major subsystem). Rows: core goal, functional requirements, scale pressure, external constraints, key techniques, license. This table is the skeleton of the report: later chapters explain how each constraint is met.
- At most one analogy for the whole system.

## 2–N. One chapter per major component
Order them along the main data path. Every chapter answers:
1. **Role**: what it is responsible for, in two sentences.
2. **Why it's hard**: the constraint that forces the design (scale, latency, failure, compatibility, untrusted input...).
3. **How it works**: the mechanism, with a diagram. Use `::: flow` for structure and `::: steps` for anything that happens over time. Link the code at every hop.
4. **Contracts**: the key types and interfaces in a table (name, purpose, key fields, link).
5. **Connections**: what calls it, what it calls, what data crosses the boundary, in which format.
6. **Gotchas**: one or two non-obvious behaviours a contributor will trip on (cache stores raw output, lazy loading, ordering of middleware...).

Typical components: entry and bootstrap, routing or dispatch, core engine, storage and caching, sync or state, plugin or extension system, output or rendering, deployment modes and config.

## End-to-end lifecycle
One concrete request followed through every component, as a numbered `::: flow` or a `::: steps` walk-through. Mark which hops are in which repo and which are not public.

## License (when the reader may fork, ship or host)
- Table: part, license, evidence link (LICENSE, package manifest, README exceptions).
- Core rules of the license in plain words (for AGPL: the network clause).
- Scenario table: use privately / contribute upstream / publish a fork / ship binaries / host for others / app stores / closed-source reuse → allowed? what you must do.
- History: when the license changed (verified via the GitHub API), and that past releases keep their old license.
- Exceptions: assets, icons, fonts, trademarks, CLA. Close with "Not legal advice."

## Contributing and customizing
- Dev setup commands (copied from CONTRIBUTING, verified to exist).
- The project's review rules (AGENTS.md, lint, tests, PR template) as a short checklist.
- Good first areas and areas to avoid (e.g. anything needing an unreleased server API).
- Customization routes as a small diagram + table (fork the client, self-host, plugin, agent workflow), with costs and dependencies.

## Appendix: source index
Tables of topic → pinned link, one per repo. This is what readers come back to.

## Size guide
A medium project (one or two repos, ~100k LOC): 6–9 chapters, 8–16 diagrams, 2–4 analogies, 60–150 source links, 15–30 PDF pages.
