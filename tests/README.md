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
modules, PCM packing helpers, and shared fake helpers for bridge / engine /
process-manager tests (`FakeCdpClient`, `FakeEngine`, `FakeProcessManager`,
`make_fake_bridge`). Reuse it when adding standalone tests instead of modifying
`sys.path` or copying loaders into individual test files.

## Test files

### `test_speech_processing.py`

Covers the core speech-processing module: three pause modes, inclusive PCM noise
floor, arbitrary PCM packet boundaries, hidden-segment finalization, bounded
lead buffering, whole/segment cache identity, safe boundary-context reuse, text
segmentation, ASCII and no-space script fast-path optimizations (`sample.isascii()`
and `_FLATTENED_NO_SPACE_RANGES`), corpus schema validation, medium-text fast-first
fallback, single-letter abbreviation guards (the `isascii()` guard prevents non-Latin
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

### `test_bridge_concurrency.py`

Covers race-condition mitigations in `bridge.py`. Verifies that
`ensure_connection()` releases the lock between fallback attempts so `terminate()`
is not blocked, that `self._engine` is captured under the lock before use to
prevent stale/engine-swapped references, and that `_runtimeBusy` is protected by
its own lock. Uses shared `FakeCdpClient`, `FakeEngine`, `FakeProcessManager`,
and `make_fake_bridge` from `test_support.py`.

### `test_runtime_recovery.py`

Covers browser-reported speech failures: a request may be retried once with a
fresh runtime only before any PCM is emitted, partial audio must never be
repeated, a no-audio error never retries more than once after recycle, and only a
healthy, connected runtime with a non-busy engine and no pending recycle flag is
safe for standby release. Uses shared `FakeCdpClient` and `FakeEngine` from
`test_support.py`.

### `test_updater_security.py`

Security tests for the updater module: SHA256 hash validation, size validation,
path traversal prevention in file names, HTTPS-only enforcement for download
URLs, manifest parsing rejects invalid input, update size limits, version
comparison, manifest value stripping, version part extraction, update
availability logic, required/optional string validation, locale key
normalization, release notes selection, and update file name construction.

### `test_voice_package_lifecycle.py`

Integration tests for the voice package lifecycle: catalog loading, package
verification with SHA256, package removal, copy for import flow, and a
complete install-verify-remove-verify lifecycle.

### `test_bridge_helpers.py`

Tests for pure helper functions in `bridge.py`: path traversal prevention
(`_safe_join`), browser runtime normalization, fallback order computation,
byte formatting, CDP error classification (transient vs. recycle-required),
`_raise_if_cancelled`, `_friendly_cdp_error`, `browser_runtime_for_path`,
browser runtime snapshot, WebView2 detection, effective runtime selection,
browser executable availability, and browser choice filtering.

### `test_build_i18n_helpers.py`

Tests for pure helper functions in `build_i18n.py`: PO file parsing (simple,
multiline, untranslated entries, msgctxt), string format placeholder
extraction, PO string escaping/quoting, obsolete entry purging, manifest
value reading, language code normalization, and message preview truncation.

### `test_generate_unicode_data_helpers.py`

Tests for pure helper functions in `generate_unicode_data.py`: UCD record
parsing (single codepoints and ranges), script alias resolution, codepoint
range merging (overlapping, adjacent, unsorted), format helpers for ranges
and codepoints, and module rendering output.

### `test_standby_concurrency.py`

Tests for `_StandbyRuntimeManager` concurrency patterns: generation counter
prevents stale workers, cancelEvent propagation between refresh cycles,
`claim_bridge` returns bridge when signature matches, `release_synth_bridge`
stores bridge for reuse, and terminate shuts down cleanly.

### `test_segmentation_fuzz.py`

Fuzz tests for speech text segmentation with random Unicode input. Tests that
the segmenter never crashes, always produces non-overlapping segments that
cover the full input, and respects maximum segment lengths for a wide range of
random Unicode text including Latin, CJK, Thai, Arabic, Devanagari, emoji,
fullwidth, and extended Latin scripts.

### `test_watcher.py`

Unit tests for `DirectoryChangeWatcher`. Verifies start/stop lifecycle,
callback invocation with correct reason, edge cases (no valid paths, empty
callback), and handle cleanup. Integration tests using real Win32 kernel32
and temp directories are skipped on non-Windows platforms.

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

### `test_synth_driver_helpers.py`

Tests for pure helper functions extracted from the SynthDriver `__init__.py`
without triggering NVDA imports: rate factor interpolation (`_interpolate_rate_factor`),
break rate clamping (`_break_rate_factor`), end-of-utterance rate factor,
language word regex, Vietnamese/English word dictionaries, and backward-compatible
configuration migration (`ConfigCompatTests` covering safe default population for
legacy settings like `rateBoost` and `pauseMode`, preservation of custom settings,
and NVDA `loadSettings()` loop simulation).

### `test_performance.py`

Covers performance characteristics and optimization verification for the
workspace version. Constants from `__init__.py` and `bridgeHarness.js` are read
via regex source parsing (not imported) to avoid NVDA dependency issues.

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
- **Adaptive audio packet sizing** (`AdaptiveAudioPacketSizingTests`): verifies
  laddered audio packet constants in `bridgeHarness.js` (first 120 samples / 5ms,
  early 1200 samples / 50ms, steady 2400 samples / 100ms, long-stream 3600 samples /
  150ms) to ensure instant startup latency and reduced CDP/base64 serialization.

Cache key tests and segmentation benchmarks live in their dedicated modules
(`test_speech_processing.py` and `test_segmentation_benchmarks.py` respectively).

### `test_segmentation_benchmarks.py`

Performance benchmark tests for text segmentation and audio processing.

- **Multilingual segmentation** (`SegmentationPerformanceTests`): verifies
  sentence splits and latency segments for Latin, CJK, Thai, Arabic, Hindi,
  mixed-script, emoji-heavy, and URL-heavy text within time bounds. Runs
  isolated cache warm-up passes before timing to eliminate cold-start measurement
  noise and verifies linear scaling robustness on CI runners.
- **PCM throughput** (`PcmProcessingThroughputTests`): verifies PCM silence
  shortener processes audio faster than real-time.

### `test_audio_math.py`

Tests for pure audio mathematics and speech option calculation helpers in `audio_math.py`:
rate-to-Chrome multiplier curve, pitch-to-Chrome semitone calculation, SeaNet protected
rate detection, and speech option building for both standard and SeaNet models.

### `test_language_utils.py`

Tests for shared language and locale normalization helpers in `language_utils.py`:
language tag normalization (`normalize_language`, `normalize_language_code`),
special NVDA locale mapping (Chinese, Arabic, Tagalog), prefix lookups, fallback
resolution, and custom language display name resolution.


## Data files

### `segmentation_corpus.json`

JSON corpus for `TextSegmenterTests`. Records locale punctuation,
abbreviation, URL, emoji, CJK/Thai no-space text, and long-sentence cases.
Schema version 1; required fields, unique IDs, categories, and operations are
validated before behavioral cases run.

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
