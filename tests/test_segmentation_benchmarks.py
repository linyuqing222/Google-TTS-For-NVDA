"""Performance benchmark tests for the text segmentation engine and audio processing.

These tests verify that the segmenter handles long multilingual text
within acceptable time bounds, and that audio processing utilities meet
throughput requirements for real-time speech synthesis.
"""

from __future__ import annotations

import time
import unittest

from tests.test_support import load_driver_module
from tests.test_support import pcm_bytes as _pcm


class SegmentationPerformanceTests(unittest.TestCase):
    """Verify segmentation performance for long multilingual text."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")
        cls.segmenter = cls.processing.DEFAULT_TEXT_SEGMENTER

    def _measure_sentence_splits(self, text: str, iterations: int = 10) -> float:
        """Measure average time for find_sentence_splits over multiple iterations."""
        # Warm up caches before timing
        self.segmenter.find_sentence_splits(text)
        times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            self.segmenter.find_sentence_splits(text)
            end = time.perf_counter()
            times.append(end - start)
        return sum(times) / len(times)

    def _measure_latency_segments(self, text: str, fast_first: bool, iterations: int = 10) -> float:
        """Measure average time for iter_text_segments_for_latency."""
        # Warm up caches before timing
        list(self.segmenter.iter_text_segments_for_latency(text, fast_first))
        times: list[float] = []
        for _ in range(iterations):
            start = time.perf_counter()
            list(self.segmenter.iter_text_segments_for_latency(text, fast_first))
            end = time.perf_counter()
            times.append(end - start)
        return sum(times) / len(times)

    def test_latin_1000_chars_sentence_splits(self) -> None:
        """1000 chars of Latin text with punctuation should split in <5ms."""
        text = "This is a test sentence. " * 40  # 1000 chars
        avg_ms = self._measure_sentence_splits(text) * 1000
        self.assertLess(avg_ms, 5.0, f"Sentence splits took {avg_ms:.1f}ms for 1000 Latin chars")

    def test_latin_5000_chars_sentence_splits(self) -> None:
        """5000 chars of Latin text should split in <20ms."""
        text = "This is a test sentence with multiple words. " * 110  # ~5000 chars
        avg_ms = self._measure_sentence_splits(text) * 1000
        self.assertLess(avg_ms, 20.0, f"Sentence splits took {avg_ms:.1f}ms for 5000 Latin chars")

    def test_cjk_1000_chars_latency_segments(self) -> None:
        """1000 chars of CJK text (no spaces) should segment in <10ms."""
        text = "这是用于测试没有空格的长文本分段并保持语音尽快开始" * 20  # ~1000 chars
        avg_ms = self._measure_latency_segments(text, False) * 1000
        self.assertLess(avg_ms, 10.0, f"Latency segments took {avg_ms:.1f}ms for 1000 CJK chars")

    def test_thai_1000_chars_latency_segments(self) -> None:
        """1000 chars of Thai text (no spaces) should segment in <15ms."""
        text = "ข้อความภาษาไทยสำหรับทดสอบการแบ่งข้อความยาวโดยไม่มีช่องว่าง" * 16  # ~1000 chars
        avg_ms = self._measure_latency_segments(text, False) * 1000
        self.assertLess(avg_ms, 15.0, f"Latency segments took {avg_ms:.1f}ms for 1000 Thai chars")

    def test_arabic_1000_chars_sentence_splits(self) -> None:
        """1000 chars of Arabic text should split in <10ms."""
        text = "هذه جملة اختبار للتقسيم الطويل. " * 35  # ~1000 chars
        avg_ms = self._measure_sentence_splits(text) * 1000
        self.assertLess(avg_ms, 10.0, f"Sentence splits took {avg_ms:.1f}ms for 1000 Arabic chars")

    def test_hindi_1000_chars_latency_segments(self) -> None:
        """1000 chars of Hindi text should segment in <15ms."""
        text = "यह एक बहुत लंबा वाक्य है जिसमें बहुत सारे शब्द हैं और इसे पढ़ने में समय लगता है " * 15  # ~1000 chars
        avg_ms = self._measure_latency_segments(text, False) * 1000
        self.assertLess(avg_ms, 15.0, f"Latency segments took {avg_ms:.1f}ms for 1000 Hindi chars")

    def test_mixed_script_2000_chars_sentence_splits(self) -> None:
        """2000 chars of mixed script text should split in <15ms."""
        text = ("Hello world.这是一个测试。مرحبا بالعالم।Привет мир. ") * 60  # ~2000 chars
        avg_ms = self._measure_sentence_splits(text) * 1000
        self.assertLess(avg_ms, 15.0, f"Sentence splits took {avg_ms:.1f}ms for 2000 mixed chars")

    def test_emoji_heavy_1000_chars_latency_segments(self) -> None:
        """1000 chars with heavy emoji usage should segment in <15ms."""
        text = "family 👨‍👩‍👧‍👦 rocket 🚀 celebration 🎉 party 🎊 " * 40  # ~1000 chars
        avg_ms = self._measure_latency_segments(text, False) * 1000
        self.assertLess(avg_ms, 15.0, f"Latency segments took {avg_ms:.1f}ms for 1000 emoji chars")

    def test_url_heavy_1000_chars_latency_segments(self) -> None:
        """1000 chars with many URLs should segment in <10ms."""
        text = "Visit https://example.com/docs/v1.2/index.html?zoom=1.5 now. " * 17  # ~1000 chars
        avg_ms = self._measure_latency_segments(text, False) * 1000
        self.assertLess(avg_ms, 10.0, f"Latency segments took {avg_ms:.1f}ms for 1000 URL chars")

    def test_fast_first_segment_1000_chars(self) -> None:
        """Fast first segmentation of 1000 chars should complete in <15ms."""
        text = "This medium length announcement deliberately contains no punctuation " * 15  # ~1000 chars
        avg_ms = self._measure_latency_segments(text, True) * 1000
        self.assertLess(avg_ms, 15.0, f"Fast first segments took {avg_ms:.1f}ms for 1000 chars")

    def test_segmentation_scales_linearly(self) -> None:
        """Segmentation time should scale roughly linearly with text length."""
        short_text = "This is a test sentence. " * 4  # ~100 chars
        long_text = "This is a test sentence. " * 40  # ~1000 chars

        short_ms = self._measure_sentence_splits(short_text, iterations=30) * 1000
        long_ms = self._measure_sentence_splits(long_text, iterations=30) * 1000

        # Long text is 10x longer, should scale within bounded ratio
        # with a minimum noise floor of 0.05ms for short text on high-speed CPUs
        effective_short_ms = max(short_ms, 0.05)
        ratio = long_ms / effective_short_ms
        self.assertLess(ratio, 20.0, f"Non-linear scaling: {ratio:.1f}x for 10x text length")


class PcmProcessingThroughputTests(unittest.TestCase):
    """Verify audio processing throughput meets real-time requirements."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.processing = load_driver_module("speech_processing")

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

        # 600 samples (25ms) of audio at 24kHz, 100 iterations (2.5s audio total) - should be under 100ms
        self.assertLess(elapsed, 0.1, f"PCM processing took {elapsed:.3f}s")


if __name__ == "__main__":
    unittest.main()
