# Beta Release Notes

_Beta Release: 2025-05-30_

⚠️ **This is a beta release for testing purposes.**

## 🚀 New Features

- fix(ci): add diagnostics and plugin verification for benchmark tests
- fix(ci): add diagnostics and plugin verification for benchmark tests
- Merge pull request #104 from DataFog/feature/sample-notebooks
- Merge branch 'dev' into feature/sample-notebooks
- Fix segmentation fault in beta-release workflow and add sample notebook
- Merge pull request #103 from DataFog/feature/sample-notebooks
- Fix segmentation fault in beta-release workflow and add sample notebook
- Merge pull request #102 from DataFog/feature/gliner-integration-v420
- Merge branch 'dev' into feature/gliner-integration-v420
- Merge branch 'feature/gliner-integration-v420' of github.com:DataFog/datafog-python into feature/gliner-integration-v420
- Merge pull request #101 from DataFog/feature/gliner-integration-v420
- Merge branch 'dev' into feature/gliner-integration-v420
- Merge pull request #100 from DataFog/feature/gliner-integration-v420
- docs: add release guidelines to Claude.md
- feat(nlp): add GLiNER integration with smart cascading engine
- fix(deps): add pydantic-settings to cli and all extras
- Merge pull request #92 from DataFog/feature/automated-release-pipeline
- feat(ci): configure release workflows for 4.2.0 minor version bump
- feat(ci): add comprehensive alpha→beta→stable release cycle
- feat(ci): add nightly alpha builds for Monday-Thursday
- Merge pull request #91 from DataFog/feature/implement-weekly-release-plan
- feat(release): implement weekly release plan infrastructure

## 🐛 Bug Fixes

- fix(ci): improve beta versioning logic and use GH_PAT token
- fix(ci): replace invalid --benchmark-skip flag with simple performance test
- Merge branch 'dev' into fix/performance-regression
- Merge pull request #105 from DataFog/fix/performance-regression
- fix(ci): reset benchmark baseline to resolve false regression alerts
- fix(performance): eliminate memory debugging overhead from benchmarks
- fix(performance): eliminate redundant regex calls in structured output mode
- fix(performance): eliminate redundant regex calls in structured output mode
- fix(ci): handle segfault gracefully while preserving test validation
- fix(tests): make spaCy address detection test more robust
- fix(ci): improve GLiNER validation to confirm PyTorch exclusion
- fix(ci): exclude PyTorch dependencies entirely to prevent segfault
- fix(ci): eliminate PyTorch segfaults and enhance README with GLiNER examples
- fix(ci): workaround for PyTorch segfault in CI environments
- fix(ci): split test execution to prevent memory segfault
- fix(ci): reduce coverage reporting to prevent segmentation fault
- fix(tests): resolve final GLiNER test failures
- fix(tests): update GLiNER test mocking for proper import paths
- fix(tests): resolve GLiNER dependency mocking for CI environments
- Merge pull request #99 from DataFog/fix/github-actions-workflow-fixes
- Merge branch 'dev' into fix/github-actions-workflow-fixes
- fix(deps): move pydantic-settings to core dependencies
- fix(ci): install all extras and configure pytest-asyncio in workflows
- Merge pull request #98 from DataFog/fix/github-actions-workflow-fixes
- fix(ci): resolve YAML syntax errors in GitHub Actions workflows
- Merge pull request #96 from DataFog/codex/fix-failing-github-actions-in-workflows
- fix release workflows
- Merge pull request #95 from DataFog/hotfix/readme-fix
- Merge branch 'dev' into hotfix/readme-fix
- fix(ci): remove indentation from Python code in workflow commands
- fix(text): resolve missing Span import for structured output
- fix(ci): resolve YAML syntax issues in workflow files
- fix(ci): resolve prettier pre-commit hook configuration
- fix(ci): resolve YAML syntax issues in release workflows
- fix(lint): resolve flake8 string formatting warnings
- fix(ci): restore expected job names and consolidate workflows
- fix(imports): resolve flake8 E402 import order issues

## 📚 Documentation

- docs: streamline Claude.md development guide for v4.2.0
- fixed readme

## 🔧 Other Changes

- chore: set version to 4.2.0b1 for beta testing of unreleased 4.2.0
- resolve: merge conflicts with enhanced segfault detection
- release: prepare v4.2.0 with GLiNER integration
- updated workflows
- Merge pull request #94 from DataFog/hotfix/beta-workflow-yaml-syntax
- Merge branch 'dev' into hotfix/beta-workflow-yaml-syntax
- Merge pull request #93 from DataFog/hotfix/beta-workflow-yaml-syntax

## 📥 Installation

```bash
# Core package (lightweight)
pip install datafog

# With all features
pip install datafog[all]
```

## 📊 Metrics

- Package size: ~2MB (core)
- Install time: ~10 seconds
- Tests passing: ✅
- Commits this week: 68
