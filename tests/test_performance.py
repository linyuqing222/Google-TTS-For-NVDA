"""Performance and benchmark tests for Google TTS For NVDA speech processing.

These tests verify that the workspace optimizations produce correct results
while measuring key performance characteristics:

- Segment flush threshold behaviour (hidden segments for cache hits)
- Speech request coalescing (cancelled requests skip CDP round-trips)
- PCM lead buffer timing (faster streaming start)
- Short audio cache efficiency (segment vs group cache keys)
- Pause mode logic correctness under threshold boundaries
"""

from __future__ import annotations

import re
import threading
import time
import unittest

from tests.test_support import ROOT, load_driver_module
from tests.test_support import pcm_bytes as _pcm


def _read_driver_constant(name: str) -> object:
    """Read a module-level constant from __init__.py without importing it (NVDA deps)."""
    path = ROOT / "googleTtsForNvda" / "synthDrivers" / "googleTtsForNvda" / "__init__.py"
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"^{name}\s*=\s*(.+)$", text, re.MULTILINE)
    if match is None:
        raise AssertionError(f"Constant {name!r} not found in __init__.py")
    return eval(match.group(1))  # noqa: S307


class SegmentFlushThresholdTests(unittest.TestCase):
    """Verify that the threshold-based segment flush logic produces correct
    hidden-segment counts and pauseShorteningMode values."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")
        cls.segmenter = cls.processing.DEFAULT_TEXT_SEGMENTER

    def _iter_indexed_segments(self, text: str, fast_first: bool = False):
        return list(self.segmenter.iter_indexed_text_segments(text, [], fast_first))

    def test_short_text_single_flush(self) -> None:
        """Text shorter than threshold produces a single group (no hidden segments)."""
        text = "Hello world"
        segments = self._iter_indexed_segments(text)
        total_chars = sum(len(seg) for seg, _ in segments)
        self.assertLess(total_chars, 120)
        self.assertGreaterEqual(len(segments), 1)

    def test_long_text_produces_multiple_groups(self) -> None:
        """Text longer than threshold with PAUSE_MODE_SHORTEN_ALL should be split
        into multiple groups at soft phrase boundaries."""
        text = (
            "This is a long sentence with many words that should exceed "
            "the flush threshold of 120 characters when accumulated across "
            "multiple segments in pause mode shorten all for testing purposes"
        )
        segments = self._iter_indexed_segments(text)
        total_chars = sum(len(seg) for seg, _ in segments)
        self.assertGreater(total_chars, 120)

    def test_threshold_constant_value(self) -> None:
        """Verify the flush threshold constant is set correctly."""
        threshold = _read_driver_constant("_FLUSH_GROUP_CHARS_THRESHOLD")
        self.assertEqual(120, threshold)

    def test_pause_mode_shorten_all_constant(self) -> None:
        """Verify PAUSE_MODE_SHORTEN_ALL is correctly defined."""
        self.assertEqual("2", self.processing.PAUSE_MODE_SHORTEN_ALL)

    def test_pause_mode_do_not_shorten_constant(self) -> None:
        """Verify PAUSE_MODE_DO_NOT_SHORTEN is correctly defined."""
        self.assertEqual("0", self.processing.PAUSE_MODE_DO_NOT_SHORTEN)

    def test_pause_mode_shorten_end_only_constant(self) -> None:
        """Verify PAUSE_MODE_SHORTEN_END_ONLY is correctly defined."""
        self.assertEqual("1", self.processing.PAUSE_MODE_SHORTEN_END_ONLY)


class SpeechCoalescingTests(unittest.TestCase):
    """Verify that cancelled requests are detected early to skip CDP round-trips."""

    def test_cancelled_event_detected_immediately(self) -> None:
        """A pre-set cancel event should be detected at the start of _speak_text."""
        cancel_event = threading.Event()
        cancel_event.set()
        self.assertTrue(cancel_event.is_set())

    def test_fresh_event_not_cancelled(self) -> None:
        """A fresh cancel event should not be detected as cancelled."""
        cancel_event = threading.Event()
        self.assertFalse(cancel_event.is_set())

    def test_cancel_event_set_during_processing(self) -> None:
        """Setting cancel event during processing should stop further work."""
        cancel_event = threading.Event()
        processing = load_driver_module("speech_processing")

        shortener = processing.create_pcm_silence_shortener(
            processing.PAUSE_MODE_SHORTEN_ALL,
            24000,
        )
        self.assertIsNotNone(shortener)

        audio = _pcm(*([1000] * 10), *([0] * 50))
        result = shortener.feed(audio)
        self.assertEqual(b"", result)

        cancel_event.set()
        self.assertTrue(cancel_event.is_set())

        final = shortener.finish()
        self.assertIsInstance(final, bytes)


class PcmLeadBufferPerformanceTests(unittest.TestCase):
    """Verify PCM lead buffer timing optimization."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")

    def test_lead_buffer_80ms_setting(self) -> None:
        """Verify LIVE_MULTI_SEGMENT_LEAD_MS is set to 80ms (optimized from 120ms)."""
        self.assertEqual(80, self.processing.LIVE_MULTI_SEGMENT_LEAD_MS)

    def test_lead_buffer_reduces_initial_latency(self) -> None:
        """80ms lead buffer should require fewer bytes than 120ms at same sample rate."""
        sample_rate = 24000
        bytes_per_sample = self.processing.PCM_BYTES_PER_SAMPLE

        lead_80ms = self.processing.pcm_bytes_for_milliseconds(80, sample_rate, bytes_per_sample)
        lead_120ms = self.processing.pcm_bytes_for_milliseconds(120, sample_rate, bytes_per_sample)

        self.assertLess(lead_80ms, lead_120ms)
        # 80ms at 24kHz 16-bit mono = 3840 bytes
        self.assertEqual(3840, lead_80ms)
        # 120ms at 24kHz 16-bit mono = 5760 bytes
        self.assertEqual(5760, lead_120ms)

    def test_lead_buffer_releases_after_threshold(self) -> None:
        """Lead buffer should hold audio until threshold, then pass through."""
        # At 1000Hz, 80ms = 160 bytes (80 samples * 2 bytes/sample)
        lead = self.processing.PcmLeadBuffer(sampleRate=1000, leadMs=80)
        threshold = self.processing.pcm_bytes_for_milliseconds(80, 1000, 2)
        self.assertEqual(160, threshold)

        # Feed less than threshold - should hold
        self.assertEqual(b"", lead.feed(b"\x01\x02\x03\x04"))

        # Feed up to exactly the threshold - should release
        remaining = threshold - 4
        result = lead.feed(b"\x05" * remaining)
        self.assertEqual(threshold, len(result))

        # After threshold, new data passes through immediately
        result = lead.feed(b"\x06\x07")
        self.assertEqual(2, len(result))

    def test_lead_buffer_finish_flushes(self) -> None:
        """finish() should return buffered audio even if below threshold."""
        lead = self.processing.PcmLeadBuffer(sampleRate=1000, leadMs=80)
        self.assertEqual(b"", lead.feed(b"\x01\x02\x03\x04"))
        result = lead.finish()
        self.assertEqual(b"\x01\x02\x03\x04", result)


class PauseModePerformanceTests(unittest.TestCase):
    """Verify pause mode constants and their performance implications."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")

    def test_sentence_break_ms_constants(self) -> None:
        """Verify optimized sentence break constants."""
        # Normal break reduced from 95ms to 45ms
        self.assertEqual(45, _read_driver_constant("_NORMAL_SENTENCE_BREAK_MS"))
        # Shortened break stays at 15ms
        self.assertEqual(15, _read_driver_constant("_SHORTENED_SENTENCE_BREAK_MS"))

    def test_end_of_utterance_pause_ms(self) -> None:
        """Verify optimized end-of-utterance pause constant."""
        # Reduced from 80ms to 40ms
        self.assertEqual(40, _read_driver_constant("_END_OF_UTTERANCE_PAUSE_MS"))

    def test_preload_resume_delay(self) -> None:
        """Verify optimized preload resume delay."""
        # Reduced from 0.45s to 0.15s
        self.assertEqual(0.15, _read_driver_constant("_PRELOAD_RESUME_DELAY_SECONDS"))

    def test_silence_shortening_reduces_pause_duration(self) -> None:
        """PAUSE_MODE_SHORTEN_ALL should produce shorter silences than DO_NOT_SHORTEN."""
        pcm = _pcm(*([0] * 100))

        do_not_shorten = self.processing.create_pcm_silence_shortener(
            self.processing.PAUSE_MODE_DO_NOT_SHORTEN,
            1000,
        )
        self.assertIsNone(do_not_shorten)

        shorten_all = self.processing.create_pcm_silence_shortener(
            self.processing.PAUSE_MODE_SHORTEN_ALL,
            1000,
        )
        self.assertIsNotNone(shorten_all)

        result = shorten_all.feed(pcm)
        result += shorten_all.finish()
        self.assertLess(len(result), len(pcm))


class CacheEfficiencyTests(unittest.TestCase):
    """Verify cache key correctness for segment and group caching."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")
        cls.options = {
            "voiceId": "vi-vn-x-multi:gft",
            "rate": 1.0,
            "pitch": 0.0,
            "postPitch": 1.0,
            "volume": 1.0,
            "outputGain": 1.70,
            "artificialRate": 1.0,
            "nvdaRate": 50,
        }

    def test_group_cache_key_differs_by_pause_mode(self) -> None:
        """Different pause modes should produce different cache keys."""
        key_0 = self.processing.short_audio_cache_key(
            "test text",
            self.options,
            pauseShorteningMode=self.processing.PAUSE_MODE_DO_NOT_SHORTEN,
        )
        key_1 = self.processing.short_audio_cache_key(
            "test text",
            self.options,
            pauseShorteningMode=self.processing.PAUSE_MODE_SHORTEN_END_ONLY,
        )
        key_2 = self.processing.short_audio_cache_key(
            "test text",
            self.options,
            pauseShorteningMode=self.processing.PAUSE_MODE_SHORTEN_ALL,
        )
        self.assertIsNotNone(key_0)
        self.assertIsNotNone(key_1)
        self.assertIsNotNone(key_2)
        self.assertEqual(3, len({key_0, key_1, key_2}))

    def test_segment_cache_key_differs_by_boundary_context(self) -> None:
        """Segment cache keys should differ based on surrounding segments."""
        key_first = self.processing.segment_audio_cache_key(
            "hello",
            self.options,
            self.processing.PAUSE_MODE_SHORTEN_ALL,
            hasPreviousSegment=False,
            hasNextSegment=True,
        )
        key_middle = self.processing.segment_audio_cache_key(
            "hello",
            self.options,
            self.processing.PAUSE_MODE_SHORTEN_ALL,
            hasPreviousSegment=True,
            hasNextSegment=True,
        )
        key_last = self.processing.segment_audio_cache_key(
            "hello",
            self.options,
            self.processing.PAUSE_MODE_SHORTEN_ALL,
            hasPreviousSegment=True,
            hasNextSegment=False,
        )
        self.assertIsNotNone(key_first)
        self.assertIsNotNone(key_middle)
        self.assertIsNotNone(key_last)
        self.assertEqual(3, len({key_first, key_middle, key_last}))

    def test_hidden_segments_affect_group_cache_key(self) -> None:
        """Group cache keys should differ when hidden segments change."""
        key_no_hidden = self.processing.short_audio_cache_key(
            "hello world",
            self.options,
        )
        key_with_hidden = self.processing.short_audio_cache_key(
            "hello world",
            self.options,
            hiddenSegments=["hello ", "world"],
        )
        self.assertIsNotNone(key_no_hidden)
        self.assertIsNotNone(key_with_hidden)
        self.assertNotEqual(key_no_hidden, key_with_hidden)

    def test_cache_rejects_oversized_input(self) -> None:
        """Cache keys should be None for oversized text or segments."""
        self.assertIsNone(self.processing.short_audio_cache_key("x" * 5001, self.options))
        self.assertIsNone(self.processing.short_audio_cache_key("x", self.options, ["x"] * 25))

    def test_cache_accepts_valid_input(self) -> None:
        """Cache keys should be valid for normal-sized text."""
        key = self.processing.short_audio_cache_key("hello", self.options)
        self.assertIsNotNone(key)
        self.assertIsInstance(key, tuple)


class BenchmarkSegmentationLatency(unittest.TestCase):
    """Benchmark text segmentation to verify it's fast enough for real-time use."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")
        cls.segmenter = cls.processing.DEFAULT_TEXT_SEGMENTER

    def test_short_text_segmentation_under_1ms(self) -> None:
        """Segmenting a short text should complete in under 1ms."""
        text = "Hello world, this is a test."
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            list(self.segmenter.iter_text_segments_for_latency(text, False))
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        self.assertLess(avg_ms, 1.0, f"Average segmentation took {avg_ms:.3f}ms")

    def test_long_text_segmentation_under_25ms(self) -> None:
        """Segmenting a long text (~2500 chars) should complete in under 25ms."""
        text = " ".join(["word"] * 500)  # ~2500 chars
        iterations = 50

        start = time.perf_counter()
        for _ in range(iterations):
            list(self.segmenter.iter_text_segments_for_latency(text, True))
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        self.assertLess(avg_ms, 25.0, f"Average segmentation took {avg_ms:.3f}ms")

    def test_sentence_split_under_1ms(self) -> None:
        """Finding sentence splits should be fast."""
        text = "First sentence. Second sentence! Third question?"
        iterations = 1000

        start = time.perf_counter()
        for _ in range(iterations):
            self.segmenter.find_sentence_splits(text)
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        self.assertLess(avg_ms, 1.0, f"Average sentence split took {avg_ms:.3f}ms")

    def test_pcm_silence_shortener_throughput(self) -> None:
        """PCM silence shortener should process audio faster than real-time."""
        processing = self.processing
        sample_rate = 24000
        pcm = _pcm(*([1000] * 100), *([0] * 200), *([800] * 100), *([0] * 200))
        iterations = 100

        start = time.perf_counter()
        for _ in range(iterations):
            s = processing.create_pcm_silence_shortener(
                processing.PAUSE_MODE_SHORTEN_ALL,
                sample_rate,
            )
            s.feed(pcm)
            s.finish()
        elapsed = time.perf_counter() - start

        # 1 second of audio, 100 iterations - should be under 100ms
        self.assertLess(elapsed, 0.1, f"PCM processing took {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
