# Contributing to Fiscoscope

Thanks for considering a contribution. This project is small and opinionated, so a few notes before you open a PR will save us both time.

## Before you start

For anything bigger than a typo or a one-line fix, open an issue first describing what you want to change and why. KPI methodology changes especially need discussion before code lands, because the dashboard's value depends on the numbers being defensible.

If you're not sure whether something fits, ask. Better to find out before you've written 300 lines.

## Project name

The project is **Fiscoscope**, written as one word with a capital F. Lowercase `fiscoscope` is fine in URLs, package names, image tags, systemd units, and other identifier contexts. Never write it as `fisc-o-scope`, `fisoscope`, or any other variant.

## Development setup

```bash
git clone https://github.com/Arnobgr/french-efficiency-dashboard.git
cd french-efficiency-dashboard/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Validate idBank resolution first:
python -m fetchers.insee_idbank_resolver

# Full pipeline:
python run_pipeline.py --mode full
```

Python 3.11+. No secrets needed; all data sources are public.

## Branching and PRs

- Target the `dev` branch, not `main`.
- One logical change per PR. A new fetcher, a KPI tweak, or a doc fix — pick one. PRs that bundle three unrelated changes get held up while we untangle them.
- Match the existing code style. No reformatting passes on files you didn't otherwise need to touch.
- Commit messages should describe *why*, not *what*. The diff already shows what.

## Rules that aren't negotiable

These come from PRD §12 and exist for good reasons. PRs that violate them will be sent back.

1. **No hardcoded INSEE idBanks.** Always load from `data/raw/insee_idbanks.json`, which is produced by `fetchers/insee_idbank_resolver.py`. INSEE renumbers series; hardcoded ids break silently.
2. **Processors must be deterministic.** Same raw input → same output JSON, every time. No timestamps in the data, no random sampling, no API calls inside a processor.
3. **Every fetcher must cache its raw response** to `data/raw/{source}_{date}.{json,csv,xlsx}` before any transformation. This lets us re-run processors without re-fetching, and gives us an audit trail when a number changes.
4. **No secrets in git.** `.env` stays in `.gitignore`. All credentials and origin URLs come from environment variables.
5. **Flag the COFOG 2020 base change.** If your processor consumes a long COFOG series, it must detect and surface the methodological break in the output `methodology` field.

## What to update when you change a KPI

If your PR changes the value of any KPI, even by a rounding digit, include:

- A short note in `docs/runtime-discoveries.md` explaining the methodology choice and why. Don't just say "fixed formula" — say what was wrong, what the new formula is, and why it's better. Future contributors (and future you) will need this.
- The before/after JSON for the affected KPI in the PR description, so reviewers can see the numerical impact at a glance.
- If you broke compatibility with a previous interpretation, mention it in `docs/known-gaps.md` too.

## What to update when you add a fetcher or KPI

- A new module under `backend/fetchers/` or `backend/processors/`, following the structure of an existing one.
- A line in `run_pipeline.py` calling it in the right phase (`monthly` or `annual`).
- A section in `docs/PRD.md` §3 (data source) or §5 (KPI spec).
- An entry in the README's KPI table if it's a new KPI.

## Code style

Match what's there. The existing code is straightforward Python with type hints on function signatures, light comments, and no premature abstractions. Resist the urge to introduce a framework, a dependency-injection container, or a base class hierarchy. If you're adding a fetcher and you find yourself writing a `BaseFetcher` ABC, stop.

## Reporting bugs

Open an issue with:

- What you ran (the exact command).
- What you expected.
- What you got (paste the error, not a screenshot).
- The KPI or data source affected, if any.
- Whether the issue is reproducible from a clean clone or only on your machine.

A bug report that lets a reviewer reproduce the problem in two minutes is worth ten reports that don't.

## License

By contributing, you agree that your contribution will be released under the project's [MIT License](LICENSE).
