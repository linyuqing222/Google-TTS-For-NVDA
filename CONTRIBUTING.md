# Contributing to Google TTS For NVDA

Thank you for your interest in contributing! This guide explains how the CI pipeline works so you know what to expect when you commit code or submit a pull request.

---

## CI Workflow Overview

Every push and pull request triggers an automated test suite via **GitHub Actions** (`.github/workflows/test.yml`). The workflow ensures your changes do not break existing functionality before code is merged.

### When does CI run?

| Event | Branch | Runs? |
|---|---|---|
| Push | `main` or `master` | Yes |
| Pull request (any branch) | — | Yes |

### What does CI test?

The workflow runs on **Windows** (`windows-latest`) against two Python versions in parallel:

- **Python 3.11**
- **Python 3.12**

It discovers and executes all standalone tests inside the `tests/` directory using `unittest`:

```
python -m unittest discover -s tests -v
```

These tests run **without NVDA installed**, so they are safe to run in any environment. They cover:

| Test file | What it covers |
|---|---|
| `test_speech_processing.py` | PCM audio, text segmentation, cache, pause modes, Unicode coverage |
| `test_dependency_isolation.py` | Vendored WebSocket isolation, private module anchoring |
| `test_language_redirect.py` | Language redirect, CLDR alias, cross-variant matching |
| `test_watcher.py` | Watcher file monitoring behavior |
| `test_unicode_data.py` | Generated Unicode script data integrity |
| `test_build_i18n.py` | Translation template and i18n build logic |
| `test_runtime_recovery.py` | Browser-reported speech failure recovery |
| `check_nvda_api_contracts.py` | Static NVDA API contract checks (against local NVDA source) |

---

## Running Tests Locally

Before pushing, run the same tests CI will run:

```powershell
python -m unittest discover -s tests -v
```

All tests should pass. If a test fails locally, it will also fail in CI — fix it before submitting your pull request.

---

## Pull Request Checklist

Before opening a PR, confirm the following:

1. **All tests pass locally.**
2. **No NVDA-specific imports** are added to files under `speech_processing.py`, `language_detector.py`, or other standalone modules — those must remain runnable without NVDA.
3. **New tests are added** for any new standalone functionality.
4. **Build succeeds** — run `build.bat` (Windows) or `build.sh` (Linux/macOS) and verify no errors.
5. **Code style matches the existing codebase.**

---

## What Happens After You Open a PR

1. **CI runs automatically.** You will see the workflow status directly on your PR page (a checkmark or red X).
2. **Both Python versions must pass.** If Python 3.11 passes but 3.12 fails (or vice-versa), the PR is not ready to merge.
3. **Reviewers will check** that the workflow is green before approving.
4. **If CI fails**, read the logs from the failed job, fix the issue locally, and push again — CI re-runs on every new push.

---

## Common CI Failures and Fixes

| Failure | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError` | New import added to a standalone module | Remove NVDA-only imports from standalone modules; keep them in driver code only |
| `AssertionError` in segmentation tests | Segmenter behavior changed | Update the expected values in `segmentation_corpus.json` or fix the segmenter logic |
| `AssertionError` in dependency isolation | A new top-level import leaks | Ensure vendored modules remain private and anchored |
| Unicode / script test failure | `unicode_data.py` regenerated incorrectly | Re-run `generate_unicode_data.py` and commit the updated file |
| Build error | Syntax error or missing file | Run `build.bat` / `build.sh` locally to reproduce and fix |

---

## Running NVDA API Contract Checks

If you have a local NVDA source checkout, verify static API contracts:

```powershell
python tests\check_nvda_api_contracts.py
```

Or point to a specific NVDA source directory:

```powershell
python tests\check_nvda_api_contracts.py "C:\path\to\NVDA source code"
```

This is optional for most contributions but recommended for changes touching the synth driver, audio output, or NVDA integration points.

---

## Additional Resources

- [TRANSLATING.md](TRANSLATING.md) — localization workflow and translation quality guidance
- [UPDATER_RELEASE_GUIDE.md](UPDATER_RELEASE_GUIDE.md) — release packaging and update manifest generation
- [tests/README.md](tests/README.md) — detailed standalone test documentation
- [readme.md](readme.md) — full add-on documentation, features, and configuration

---

## Questions?

Open an issue or reach out via the contact information in [readme.md](readme.md).
