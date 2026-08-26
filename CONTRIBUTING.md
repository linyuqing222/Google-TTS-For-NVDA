# Contributing to Google TTS For NVDA

Thanks for your interest in helping out! Whether you're fixing a bug, adding a feature, improving translations, or just cleaning up docs, every contribution counts.

This guide covers what happens when you push code or open a pull request, and how to catch problems locally before CI does.

---

## How CI Works

Every push and every pull request triggers the **Tests** workflow on GitHub Actions (`.github/workflows/test.yml`). It runs on **Windows** (`windows-latest`) against two Python versions in parallel: **Python 3.11** and **Python 3.12**. Both must pass for a PR to be mergeable.

The workflow uses `fail-fast: false`, so if Python 3.11 fails, 3.12 still finishes running — you'll see all failures at once instead of having to fix them one at a time.

### CI Steps (in order)

The workflow runs these checks in sequence:

1. **Ruff lint** — `python -m ruff check` catches unused imports, undefined names, common bugs, and style issues. The config in `ruff.toml` excludes vendored directories (`websocketClientRepo`, `WasmTtsEngine`, `cld2`, `web`) and targets Python 3.11.

2. **Ruff format** — `python -m ruff format --check` verifies code formatting. If your code isn't formatted, the check fails. Run `python -m ruff format` to fix it automatically.

3. **Mypy type check** — catches type inconsistencies across `synthDrivers/`, `tests/`, and all six `globalPlugins/` files (including `__init__.py`). The `--explicit-package-bases` flag prevents a duplicate module name conflict between the two `googleTtsForNvda` packages. Missing imports are ignored (`ignore_missing_imports = true` in `mypy.ini`), and many common error codes are disabled (`name-defined`, `attr-defined`, `arg-type`, `index`, `assignment`, `return`, `union-attr`, `operator`, `var-annotated`, `no-redef`). Mypy catches the remaining type inconsistencies — actual errors within checked modules will fail the build.

4. **Unit tests** — `python -m unittest discover -s tests -v` runs all standalone tests. These don't need NVDA installed, so they work on any Windows machine (and Linux/macOS with the right setup).

After all checks finish, CI runs `git clean -fdX` to remove all files listed in `.gitignore` (caches, build artifacts, etc.). This keeps the workspace clean without hardcoding paths — when you add a new entry to `.gitignore`, cleanup follows automatically.

### When does CI run?

| Event | Branch | Runs? |
|---|---|---|
| Push | `main` or `master` | Yes |
| Pull request (any branch) | — | Yes |

---

## Running Checks Locally

You don't need to push just to find out if your code passes. Run these locally first — they're fast and catch most issues before you even open a PR.

### Opening a terminal in the project folder

The quickest way:

1. Open the project folder in **File Explorer** (the folder containing `CONTRIBUTING.md`).
2. Press **Alt + D** to focus the address bar.
3. Type `powershell` and press **Enter**. A PowerShell window opens in that folder.

### Install the tools

```powershell
pip install ruff mypy
```

You only need to do this once (or when the project updates its tool versions).

### Run all checks at once

The mypy command is long, so here's a helper you can paste into PowerShell first:

```powershell
$mypy = "python -m mypy --config-file mypy.ini --explicit-package-bases --exclude websocketClientRepo googleTtsForNvda/synthDrivers/ tests/ googleTtsForNvda/globalPlugins/googleTtsForNvda/__init__.py googleTtsForNvda/globalPlugins/googleTtsForNvda/settings.py googleTtsForNvda/globalPlugins/googleTtsForNvda/updateGui.py googleTtsForNvda/globalPlugins/googleTtsForNvda/uiUtils.py googleTtsForNvda/globalPlugins/googleTtsForNvda/updater.py googleTtsForNvda/globalPlugins/googleTtsForNvda/voiceManager.py"
```

Then run all CI checks in one go:

```powershell
python -m ruff check ; python -m ruff format --check ; $mypy ; python -m unittest discover -s tests -v ; git clean -fdX
```

Or without the helper, the full command:

```powershell
python -m ruff check ; python -m ruff format --check ; python -m mypy --config-file mypy.ini --explicit-package-bases --exclude "websocketClientRepo" googleTtsForNvda/synthDrivers/ tests/ googleTtsForNvda/globalPlugins/googleTtsForNvda/__init__.py googleTtsForNvda/globalPlugins/googleTtsForNvda/settings.py googleTtsForNvda/globalPlugins/googleTtsForNvda/updateGui.py googleTtsForNvda/globalPlugins/googleTtsForNvda/uiUtils.py googleTtsForNvda/globalPlugins/googleTtsForNvda/updater.py googleTtsForNvda/globalPlugins/googleTtsForNvda/voiceManager.py ; python -m unittest discover -s tests -v ; git clean -fdX
```

### Individual checks

Run any single check by typing the command and pressing **Enter**:

```powershell
python -m ruff check            # lint
python -m ruff format --check   # format
python -m mypy --config-file mypy.ini --explicit-package-bases --exclude "websocketClientRepo" googleTtsForNvda/synthDrivers/ tests/ googleTtsForNvda/globalPlugins/googleTtsForNvda/__init__.py googleTtsForNvda/globalPlugins/googleTtsForNvda/settings.py googleTtsForNvda/globalPlugins/googleTtsForNvda/updateGui.py googleTtsForNvda/globalPlugins/googleTtsForNvda/uiUtils.py googleTtsForNvda/globalPlugins/googleTtsForNvda/updater.py googleTtsForNvda/globalPlugins/googleTtsForNvda/voiceManager.py   # types
python -m unittest discover -s tests -v   # tests
```

If `ruff format --check` fails, fix formatting with:

```powershell
python -m ruff format
```

---

## What the Tests Cover

These tests run **without NVDA installed**, so they're safe in any environment:

| Test file | What it covers |
|---|---|
| `test_speech_processing.py` | PCM audio processing, text segmentation, cache keys, pause modes, Unicode coverage |
| `test_dependency_isolation.py` | Vendored WebSocket isolation, private module anchoring |
| `test_language_redirect.py` | Language redirect, CLDR alias, cross-variant matching |
| `test_watcher.py` | File system change watcher behavior |
| `test_unicode_data.py` | Generated Unicode script data integrity |
| `test_build_i18n.py` | Translation template and i18n build logic |
| `test_runtime_recovery.py` | Browser-reported speech failure recovery |

---

## Pull Request Checklist

Before opening a PR, run through this:

1. **All checks pass locally.** Run the [all-in-one command](#run-all-checks-at-once) or each step individually — all should be clean.
2. **No NVDA-specific imports** are added to standalone modules like `speech_processing.py`, `language_detector.py`, `language_profiles.py`, or `unicode_data.py`. Those must remain runnable without NVDA. (CI will catch this with `ModuleNotFoundError` failures.)
3. **New tests are added** for any new standalone functionality.
4. **Build succeeds** — run `build.bat` (Windows) or `build.sh` (Linux/macOS) and verify no errors.
5. **Code matches the existing style.** Ruff handles most of this, but also check naming conventions, docstrings, and comment style against nearby code.
6. **User-facing strings use `_()` for translation** where applicable in NVDA UI code.

---

## What Happens After You Open a PR

1. **CI runs automatically.** You'll see the workflow status directly on your PR page (a checkmark or red X).
2. **Both Python versions must pass.** With `fail-fast: false`, both 3.11 and 3.12 run to completion even if one fails, so you'll see all issues at once.
3. **Reviewers will check** that the workflow is green before approving.
4. **If CI fails**, read the logs from the failed job, fix it locally, and push again — CI re-runs on every new push.

---

## Common CI Failures and Fixes

| Failure | Likely cause | Fix |
|---|---|---|
| `ruff check` finds unused imports | Import added but not used, or used only in NVDA code | Remove the unused import; move NVDA-only imports into the driver code |
| `ruff format` shows differences | Code not formatted | Run `python -m ruff format` and commit the result |
| `mypy` reports type errors | New code doesn't match expected types | Check the type annotation and fix it, or add a `# type: ignore` with a comment if it's a known NVDA quirk |
| `ModuleNotFoundError` in tests | New import added to a standalone module | Remove NVDA-only imports from standalone modules; keep them in driver code only |
| `AssertionError` in segmentation tests | Segmenter behavior changed | Update the expected values in `segmentation_corpus.json` or fix the segmenter logic |
| `AssertionError` in dependency isolation | A new top-level import leaks | Ensure vendored modules remain private and anchored |
| Unicode / script test failure | `unicode_data.py` regenerated incorrectly | Re-run `generate_unicode_data.py` and commit the updated file |
| Build error | Syntax error or missing file | Run `build.bat` / `build.sh` locally to reproduce and fix |

---

## Running NVDA API Contract Checks

If you have a local NVDA source checkout, you can verify static API contracts:

```powershell
python tests\check_nvda_api_contracts.py
```

The script looks for a sibling `NVDA source code` directory by default. Point it elsewhere if needed:

```powershell
python tests\check_nvda_api_contracts.py "C:\path\to\NVDA source code"
```

This is optional for most contributions, but recommended when you're touching the synth driver, audio output, or other NVDA integration points. The script checks contracts across several categories: synth driver, global plugin, speech hooks, settings dialog, voice manager, updater, browser runtime, and shared NVDA state.

---

## Additional Resources

- [TRANSLATING.md](TRANSLATING.md) — localization workflow and translation quality guidance
- [UPDATER_RELEASE_GUIDE.md](UPDATER_RELEASE_GUIDE.md) — release packaging and update manifest generation
- [tests/README.md](tests/README.md) — detailed standalone test documentation
- [readme.md](readme.md) — full add-on documentation, features, and configuration
- [AGENTS.md](AGENTS.md) — comprehensive engineering guide for coding agents (useful reference for human contributors too)

---

## Questions?

Open an issue or reach out via the contact information in [readme.md](readme.md).
