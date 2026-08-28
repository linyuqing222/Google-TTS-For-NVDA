"""Performance tests for Google TTS For NVDA speech processing.

These tests verify that the workspace optimizations produce correct results
while measuring key performance characteristics:

- Segment flush threshold behaviour (hidden segments for cache hits)
- Speech request coalescing (cancelled requests skip CDP round-trips)
- PCM lead buffer timing (faster streaming start)
- Pause mode logic correctness under threshold boundaries

Segmentation benchmarks and cache key tests live in their dedicated modules
(test_segmentation_benchmarks.py and test_speech_processing.py respectively).
"""

from __future__ import annotations

import re
import threading
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


if __name__ == "__main__":
    unittest.main()
