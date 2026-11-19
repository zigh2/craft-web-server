# Contributing

```bash
python -m unittest discover -s tests -v     # tests (standard library only)
pip install ruff && ruff check .            # lint
```

- Keep the project dependency-free (Python standard library + vanilla JS).
- Add a test for every behaviour change and a line to `CHANGELOG.md` under the version in `VERSION`.
- Releases are automatic: every merge to `main` is tested and published (see `.github/workflows/release.yml`).
  Bump `VERSION` for a new minor/major; otherwise the patch number is incremented for you.
- Dashboard code must stay CSP-safe: no inline scripts/styles, no `innerHTML` with data.
