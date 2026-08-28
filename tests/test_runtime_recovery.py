from __future__ import annotations

import unittest

from tests.test_support import FakeEngine, load_driver_module, make_fake_bridge

bridgeModule = load_driver_module("bridge")


class _FailingEngine:
    def __init__(self, error: BaseException) -> None:
        self.error = error
        self.calls = 0
        self.runtime_busy = False

    def speak(self, *args: object, **kwargs: object) -> dict[str, object]:
        self.calls += 1
        raise self.error


def _browser_speech_error(*, audioStarted: bool) -> BaseException:
    return bridgeModule._BrowserSpeechError(
        "Could not speak",
        "Browser harness reported a speech error",
        audioStarted=audioStarted,
    )


def _runtime_bridge(engine: object) -> object:
    b = make_fake_bridge(engine=engine)
    b.ensure_connection = lambda cancelEvent=None: None
    return b


class RuntimeRecoveryTests(unittest.TestCase):
    def test_browser_speech_errors_require_runtime_recycle(self) -> None:
        error = _browser_speech_error(audioStarted=False)
        self.assertTrue(bridgeModule._runtime_error_requires_recycle(error))

    def test_no_audio_browser_error_retries_once_after_recycle(self) -> None:
        failedEngine = _FailingEngine(_browser_speech_error(audioStarted=False))
        successfulEngine = FakeEngine()
        bridge = _runtime_bridge(failedEngine)
        recycleCalls = 0

        def maybe_recycle_runtime(*, allowIdleRecycle: bool = True, checkMemory: bool = True) -> bool:
            nonlocal recycleCalls
            if not allowIdleRecycle:
                return False
            recycleCalls += 1
            bridge._engine = successfulEngine
            bridge._needsRecycle = False
            return True

        bridge.maybe_recycle_runtime = maybe_recycle_runtime
        result = bridge.speak("text", {}, lambda _audio: None)

        self.assertEqual({"success": True}, result)
        self.assertEqual(1, failedEngine.calls)
        self.assertEqual(1, successfulEngine.calls)
        self.assertEqual(1, recycleCalls)

    def test_partial_audio_browser_error_recycles_without_retry(self) -> None:
        error = _browser_speech_error(audioStarted=True)
        failedEngine = _FailingEngine(error)
        successfulEngine = FakeEngine()
        bridge = _runtime_bridge(failedEngine)
        recycleCalls = 0

        def maybe_recycle_runtime(*, allowIdleRecycle: bool = True, checkMemory: bool = True) -> bool:
            nonlocal recycleCalls
            if not allowIdleRecycle:
                return False
            recycleCalls += 1
            bridge._engine = successfulEngine
            bridge._needsRecycle = False
            return True

        bridge.maybe_recycle_runtime = maybe_recycle_runtime
        with self.assertRaises(bridgeModule._BrowserSpeechError):
            bridge.speak("text", {}, lambda _audio: None)

        self.assertEqual(1, failedEngine.calls)
        self.assertEqual(0, successfulEngine.calls)
        self.assertEqual(1, recycleCalls)

    def test_browser_error_is_never_retried_more_than_once(self) -> None:
        failedEngine = _FailingEngine(_browser_speech_error(audioStarted=False))
        bridge = _runtime_bridge(failedEngine)
        recycleCalls = 0

        def maybe_recycle_runtime(*, allowIdleRecycle: bool = True, checkMemory: bool = True) -> bool:
            nonlocal recycleCalls
            if not allowIdleRecycle:
                return False
            recycleCalls += 1
            bridge._needsRecycle = False
            return True

        bridge.maybe_recycle_runtime = maybe_recycle_runtime
        with self.assertRaises(bridgeModule._BrowserSpeechError):
            bridge.speak("text", {}, lambda _audio: None)

        self.assertEqual(2, failedEngine.calls)
        self.assertEqual(2, recycleCalls)

    def test_only_healthy_connected_runtime_is_safe_for_standby(self) -> None:
        bridge = _runtime_bridge(FakeEngine())
        bridge._cdp_client.connected = True
        self.assertTrue(bridge.safe_for_standby_release())

        bridge._needsRecycle = True
        self.assertFalse(bridge.safe_for_standby_release())
        bridge._needsRecycle = False
        bridge._engine.runtime_busy = True
        self.assertFalse(bridge.safe_for_standby_release())
        bridge._engine.runtime_busy = False
        bridge._cdp_client.connected = False
        self.assertFalse(bridge.safe_for_standby_release())


if __name__ == "__main__":
    unittest.main()
