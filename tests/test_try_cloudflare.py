from __future__ import annotations

import sys
from contextlib import ExitStack, contextmanager
from unittest import mock

import pytest

from pycloudflared.try_cloudflare import TryCloudflare


class FakeStderr:
    """Minimal stand-in for a process' text-mode stderr pipe."""

    def __init__(self, lines: list[str]):
        # Real readline() returns "" only at EOF; emulate that here.
        self._lines = [*lines]

    def readline(self) -> str:
        if self._lines:
            return self._lines.pop(0)
        return ""


class FakeProcess:
    def __init__(self, lines: list[str]):
        self.stderr = FakeStderr(lines)
        self.terminated = False

    def terminate(self) -> None:
        self.terminated = True


@contextmanager
def patched(lines: list[str]):
    proc = FakeProcess(lines)
    info = mock.Mock()
    # sys.executable always exists, so download() is never triggered.
    info.executable = sys.executable
    with ExitStack() as stack:
        stack.enter_context(
            mock.patch("pycloudflared.try_cloudflare.get_info", return_value=info)
        )
        stack.enter_context(
            mock.patch(
                "pycloudflared.try_cloudflare.subprocess.Popen", return_value=proc
            )
        )
        stack.enter_context(mock.patch("pycloudflared.try_cloudflare.atexit"))
        yield TryCloudflare(), proc


def test_parses_tunnel_and_metrics_urls():
    lines = [
        "INF starting tunnel\n",
        "INF |  https://random-words.trycloudflare.com  |\n",
        "INF Metrics server on 127.0.0.1:41785/metrics\n",
    ]
    with patched(lines) as (tc, proc):
        urls = tc(8000, verbose=False)

    assert urls.tunnel == "https://random-words.trycloudflare.com"
    assert urls.metrics == "http://127.0.0.1:41785/metrics"
    assert urls.process is proc


def test_early_exit_surfaces_cloudflared_output():
    # cloudflared prints an error and exits before emitting a tunnel url.
    lines = [
        "INF starting tunnel\n",
        "ERR failed to request quick tunnel: bad gateway\n",
    ]
    with patched(lines) as (tc, proc), pytest.raises(RuntimeError) as exc_info:
        tc(8000, verbose=False)

    message = str(exc_info.value)
    assert "Cloudflared failed to start" in message
    # The real cloudflared error is surfaced to the caller for diagnosis.
    assert "bad gateway" in message
    # The dead process is cleaned up rather than leaked.
    assert proc.terminated is True


def test_failure_without_output_still_raises():
    err = "Cloudflared failed to start"
    with patched([]) as (tc, proc), pytest.raises(RuntimeError, match=err):
        tc(8000, verbose=False)
    assert proc.terminated is True
