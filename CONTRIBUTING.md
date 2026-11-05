# Contributing

Thanks for taking a look. This repository is a benchmark snapshot, not a
product, so the bar for changes is: keep the method reproducible and the
results honest.

## Issues

- Search existing issues first.
- Include the cell, phase, command and the relevant `grade.json` or
  `events.jsonl` excerpt.
- If you are reporting a benchmark flaw, say whether it affects a score, a
  claim in the README, or only the harness.

## Pull requests

- One logical change per PR. Conventional commits: `feat:`, `fix:`, `docs:`,
  `test:`, `chore:`, `refactor:`.
- Keep the existing structure (`bench/tasks`, `bench/tests`, `bench/graders`).
- If you change a task, update its hidden test and the reference
  implementation together.
- Run the relevant tests before opening the PR:

```sh
python3 -m unittest discover -s bench/seed/webapp/tests -v
python3 -m unittest discover -s bench/seed/render3d/tests -v
python3 -m unittest discover -s bench/seed/ledger/tests -v
```

- Do not add dependencies unless the benchmark genuinely needs them. The
  original suites are stdlib-only for a reason: reproducibility.

## Data and secrets

- Never commit API keys, `auth.json`, `*.db`, `.env`, `.bench-vault/` or
  private vault content.
- Do not publish raw session logs without reviewing them for host paths,
  credentials and personal data.

## License

By contributing, you agree that code is licensed under Apache-2.0 and
documentation/results under CC BY 4.0.
