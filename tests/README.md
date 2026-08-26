# Standalone regression tests

All tests run without importing NVDA. The production `speech_processing.py`
module is loaded directly, so tests exercise the real implementation rather
than an AST copy.

## Running

```powershell
python -m unittest discover -s tests -v
```

## Test support

`test_support.py` provides repository paths, isolated loading of pure driver
modules, and PCM packing helpers. Reuse it when adding standalone tests instead
of modifying `sys.path` or copying loaders into individual test files.

## Test files

### `test_speech_processing.py`

Covers the core speech-processing module: three pause modes, inclusive PCM noise
floor, arbitrary PCM packet boundaries, hidden-segment finalization, bounded
lead buffering, whole/segment cache identity, safe boundary-context reuse, text
segmentation, corpus schema validation, medium-text fast-first fallback,
single-letter abbreviation guards (the `isascii()` guard prevents non-Latin
single-letter words from blocking splits), and Unicode sentence terminal
coverage across ASCII, CJK, Arabic, Devanagari, Thai, Meetei Mayek, Greek, and
the tailored ellipsis.

Corpus data lives in `segmentation_corpus.json` and records locale punctuation,
abbreviation, URL, emoji, CJK/Thai no-space text, and long-sentence cases.
Expected results describe this add-on's segmenter rather than claiming
byte-for-byte parity with Java `BreakIterator`. Corpus schema version 1,
required fields, unique IDs, categories, and operations are validated before
behavioral cases run.

### `test_dependency_isolation.py`

Verifies that the browser bridge loads Google TTS For NVDA's private vendored
WebSocket client even when another add-on has already registered a top-level
`websocket` module. Also prevents optional third-party imports from leaking into
the vendored client, keeps pure driver helpers free of NVDA-only dependencies,
and checks that CLD2, browser files, and the pinned WASM engine stay anchored to
this add-on's own directories.

### `test_build_i18n.py`

Covers translation-template versioning from `manifest.ini`, single-locale and
all-locale menu selection, all-locale and repeated-locale command options,
removal of obsolete PO blocks, preservation of exact existing translations, and
the requirement that newly merged source strings remain empty for translators.

### `test_runtime_recovery.py`

Covers browser-reported speech failures: a request may be retried once with a
fresh runtime only before any PCM is emitted, partial audio must never be
repeated, a no-audio error never retries more than once after recycle, and only a
healthy, connected runtime with a non-busy engine and no pending recycle flag is
safe for standby release.

### `test_language_redirect.py`

Covers language redirect and consolidated matching helpers in
`language_detector.py`. Verifies explicit dialect redirects (french-canadian to
fr-FR, portuguese-european to pt-BR, spanish-spain to es-MX, etc.),
root-language fallback when no explicit redirect exists, CLDR alias resolution
(fil/tl, he/iw), Chinese-family cross-variant matching, underscore
normalization, and edge cases with None and empty inputs.

### `test_unicode_data.py`

Verifies that every language root in the bundled `voices.json` has generated
script data and that the pinned Unicode sentence-terminal table is complete.
Imports the production `language_profiles.py` fallback directly. Covers:

- Every bundled language root has expected script map
- Every mapped script exercises a disjoint candidate
- Shared-script language pairs remain ambiguous
- Unicode 17 script ranges outside old blocks are present
- Script ranges are sorted and non-overlapping
- Language ranges are exactly composed from their mapped scripts
- Sentence-terminal tailoring is minimal and disjoint from the official table

`unicode_data.py` is generated from UCD 17.0 and CLDR 48.2 with:

```powershell
python generate_unicode_data.py --ucd-dir <ucd-directory> `
  --likely-subtags <cldr-likelySubtags.xml> --cldr-version 48.2
```

### `test_performance.py`

Covers performance characteristics and optimization verification for the
workspace version. Constants from `__init__.py` are read via regex source
parsing (not imported) to avoid NVDA dependency issues.

- **Segment flush threshold** (`SegmentFlushThresholdTests`): verifies that
  `_FLUSH_GROUP_CHARS_THRESHOLD` (120 chars) controls when soft phrase boundaries
  trigger intermediate flushes for `PAUSE_MODE_SHORTEN_ALL`.
- **Speech request coalescing** (`SpeechCoalescingTests`): verifies that a
  pre-set `cancelEvent` is detected immediately at the top of `_speak_text()` to
  skip CDP round-trips for already-cancelled requests.
- **PCM lead buffer** (`PcmLeadBufferPerformanceTests`): verifies
  `LIVE_MULTI_SEGMENT_LEAD_MS` is set to 80ms (from 120ms), lead buffer holds
  audio until threshold, and `finish()` flushes remaining buffered audio.
- **Pause mode constants** (`PauseModePerformanceTests`): verifies optimized
  timing constants: sentence break 45ms (from 95ms), end-of-utterance pause 40ms
  (from 80ms), and preload resume delay 0.15s (from 0.45s).
- **Cache efficiency** (`CacheEfficiencyTests`): verifies cache keys differ by
  pause mode, hidden segments, boundary context, and oversized inputs are
  rejected.
- **Segmentation benchmarks** (`BenchmarkSegmentationLatency`): verifies
  short-text segmentation under 1ms, long-text (~2500 chars) under 25ms,
  sentence splitting under 1ms, and PCM silence shortening faster than
  real-time.

## NVDA compatibility and runtime testing

Static API contracts can be checked against a local NVDA checkout:

```powershell
python tests\check_nvda_api_contracts.py
```

The default looks for a sibling `NVDA source code` directory. A different parent
can be supplied explicitly:

```powershell
python tests\check_nvda_api_contracts.py <NVDA-source-directory>
```

Covers synth driver, audio output, global plugin, speech hooks, language
profiles, Settings category, Voice Manager, updater, browser runtime/standby,
and shared NVDA state. Reports high-risk `setSynth`, `WavePlayer`,
`nvwave.isInError`, output-device configuration, and
`AutoSettingsMixin.refreshGui` contracts.

Static inspection cannot validate WASM/browser startup, audible PCM quality, or
screen-reader focus announcements. Use `NVDA_CHROMIUM_MANUAL_CHECKLIST.md` for
those release tests.
