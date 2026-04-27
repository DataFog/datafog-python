# Contributing to DataFog Python

Thanks for helping improve DataFog. The project welcomes issues, bug reports,
documentation fixes, tests, and pull requests.

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md) in all project spaces.

## Branch And PR Policy

DataFog uses `dev` as the default development branch and `main` as the stable
release branch.

Use this workflow for normal contributions:

1. Fork the repository or create a topic branch from `dev`.
2. Name branches with a GitHub username prefix when practical, for example
   `sidmohan0/dfpy-v44-bridge` or `yourname/fix-cli-redaction`.
3. Open pull requests into `dev`.
4. Keep pull requests focused and include tests or docs when behavior changes.

Use `main` only for stable release promotion or urgent release hotfixes.
Do not use `dev` or `main` as working branches.

Maintainers should prefer pull requests even for small changes. Protected branch
rules should prevent branch deletion, require CI before merge, and avoid direct
pushes except for explicit emergency maintenance.

## Local Development

```bash
git clone https://github.com/datafog/datafog-python
cd datafog-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev,cli]"
```

For optional NLP or OCR work, install the relevant extras:

```bash
pip install -e ".[dev,cli,nlp]"
pip install -e ".[dev,cli,nlp,nlp-advanced]"
pip install -e ".[all,dev]"
```

## Tests

Run the core test suite before opening a pull request:

```bash
pytest tests/ -m "not slow" \
  --ignore=tests/test_gliner_annotator.py \
  --ignore=tests/test_image_service.py \
  --ignore=tests/test_ocr_integration.py \
  --ignore=tests/test_spark_integration.py \
  --ignore=tests/test_text_service_integration.py
```

Run the focused test file for the area you changed whenever possible. For
documentation-only changes, build the docs:

```bash
sphinx-build -b html docs docs/_build/html
```

## Pull Request Checklist

Before requesting review:

- Rebase or merge the latest `dev`.
- Add or update tests for behavior changes.
- Update docs for user-facing changes.
- Keep public API changes explicit in the PR description.
- Note any optional dependency profile you tested, such as `core`, `nlp`, or
  `nlp-advanced`.

## Commit Messages

Use clear, descriptive commit messages. Conventional-style prefixes are welcome
but not required, for example:

- `fix: handle empty scan input`
- `docs: clarify branch policy`
- `test: cover v5 preview redaction wrapper`

## Legal

By submitting a pull request, you license your contribution under the project
[license](LICENSE). You also affirm that you authored the contribution or have
the right to submit it under the project license.

## Contributors

Thanks to early contributors including:

- sroy9675
- pselvana
- sidmohan0
