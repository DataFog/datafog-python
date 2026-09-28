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

The current contributor runbook for DataFog 4.5 lives in
[`docs/contributing.rst`](docs/contributing.rst). It includes supported Python
versions, install profiles, focused and broad test commands, docs-build
verification, and the 4.5 release-flow boundary.

```bash
git clone https://github.com/datafog/datafog-python
cd datafog-python
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -e ".[dev,cli]"
```

For pinned local tooling, install the development requirements after the editable
package install:

```bash
pip install -r requirements-dev.txt
```

For optional NLP, OCR, or distributed work, install the relevant extras:

```bash
pip install -e ".[dev,cli,nlp]"
pip install -e ".[dev,cli,nlp,nlp-advanced]"
pip install -e ".[dev,cli,ocr]"
pip install -e ".[dev,cli,distributed]"
pip install -e ".[all,dev]"
```

## Tests

Run focused tests for the area you changed before opening a pull request. For
core import and dependency-boundary work, use:

```bash
DATAFOG_NO_TELEMETRY=1 DO_NOT_TRACK=1 \
  pytest tests/test_runtime_dependency_safety.py tests/test_no_network_core.py -q
```

For broader local confidence, run the non-slow suite:

```bash
pytest -m "not slow" -q
```

To mimic the core CI profile, run:

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
python -m sphinx -b html docs docs/_build/html
```

See [`docs/contributing.rst`](docs/contributing.rst) for optional-profile smoke
commands and release-prep checks.

## Pull Request Checklist

Before requesting review:

- Rebase or merge the latest `dev`.
- Add or update tests for behavior changes.
- Update docs for user-facing changes.
- Keep public API changes explicit in the PR description.
- Note any optional dependency profile you tested, such as `core`, `nlp`, or
  `nlp-advanced`.
- Complete the CLA Assistant check. First-time contributors receive a comment
  on the pull request with a link to review and accept the agreement.

## Commit Messages

Use clear, descriptive commit messages. Conventional-style prefixes are welcome
but not required, for example:

- `fix: handle empty scan input`
- `docs: clarify branch policy`
- `test: cover v5 preview redaction wrapper`

## Legal

DataFog requires each contributor to accept the
[Individual Contributor License Agreement](CLA.md). CLA Assistant handles the
signature directly from the pull request:

1. Open your pull request against `dev`.
2. Follow the link in the CLA Assistant comment and sign in with the same
   GitHub account that authored the commits.
3. Review the agreement, complete the short signing form, and accept it. The
   `cla-assistant` check updates automatically; no document upload is needed.

You normally sign once. A new signature is requested only when DataFog updates
the agreement. If a commit has multiple authors, every human co-author must
sign. Bot accounts are handled separately by maintainers.

If your employer or another organization may own your work, confirm that you
are allowed to contribute before signing. Questions can be sent to
`sid@datafog.ai`.

## Contributors

Thanks to early contributors including:

- sroy9675
- pselvana
- sidmohan0
