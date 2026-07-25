from __future__ import annotations

import atexit
import os
import re
import subprocess
from pathlib import Path
from typing import NamedTuple, NoReturn

from .util import download, get_info

DEFAULT_LINES_TO_CHECK = 50

url_pattern = re.compile(r"(?P<url>https?://\S+\.trycloudflare\.com)")
metrics_pattern = re.compile(r"(?P<url>127\.0\.0\.1:\d+/metrics)")


def get_lines_to_check() -> int:
    return int(os.getenv("PYCLOUDFLARED_LINES_TO_CHECK", DEFAULT_LINES_TO_CHECK))


class Urls(NamedTuple):
    tunnel: str
    metrics: str
    process: subprocess.Popen


class TryCloudflare:
    def __init__(self):
        self.running: dict[int, Urls] = {}

    def __call__(
        self,
        port: int | str,
        metrics_port: int | str | None = None,
        verbose: bool = True,
    ) -> Urls:
        """
        launches 'trycloudflare' cloudflared tunnel on the given port
        <https://try.cloudflare.com>

        Parameters
        ----------
        port : int | str
            port to launch the tunnel on.
        metrics_port : int | str | None, optional, default None
            port to launch the metrics server on,
            if None, cloudflared will use a random port to launch the metrics server on.
        verbose : bool, default True
            print the tunnel url and metrics url

        Returns
        -------
        Urls (NamedTuple)
            tunnel: str, tunnel url
            metrics: str, metrics url
            process: subprocess.Popen, cloudflared process Popen object

        Raises
        ------
        RuntimeError
            When cloudflared fails to start
        """
        info = get_info()
        if not Path(info.executable).exists():
            download(info)

        port = int(port)
        if port in self.running:
            urls = self.running[port]
            if verbose:
                self._print(urls.tunnel, urls.metrics)
            return urls

        args = [
            info.executable,
            "tunnel",
            "--url",
            f"http://127.0.0.1:{port}",
        ]

        if metrics_port is not None:
            args += [
                "--metrics",
                f"127.0.0.1:{metrics_port}",
            ]

        cloudflared = subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

        atexit.register(cloudflared.terminate)

        tunnel_url, metrics_url, output = self._read_urls(cloudflared)
        if not (tunnel_url and metrics_url):
            self._raise_start_failure(cloudflared, output)

        urls = Urls(tunnel_url, metrics_url, cloudflared)
        if verbose:
            self._print(urls.tunnel, urls.metrics)

        self.running[port] = urls
        return urls

    @staticmethod
    def _read_urls(process: subprocess.Popen) -> tuple[str, str, list[str]]:
        """Read cloudflared's stderr until both urls are found or it ends.

        Returns the tunnel url, the metrics url and the captured stderr lines.
        A url may be empty if it was not seen before the process ended or the
        line budget was exhausted.
        """
        tunnel_url = metrics_url = ""
        output: list[str] = []

        for _ in range(get_lines_to_check()):
            line = process.stderr.readline()  # pyright: ignore[reportOptionalMemberAccess]
            if not line:
                # An empty string means stderr reached EOF: cloudflared exited
                # before printing the url. Stop early instead of spinning over
                # the remaining iterations reading nothing.
                break
            output.append(line)

            url_match = url_pattern.search(line)
            metric_match = metrics_pattern.search(line)
            if url_match:
                tunnel_url = url_match.group("url")
            if metric_match:
                metrics_url = "http://" + metric_match.group("url")

            if tunnel_url and metrics_url:
                break

        return tunnel_url, metrics_url, output

    @staticmethod
    def _raise_start_failure(
        process: subprocess.Popen, output: list[str]
    ) -> NoReturn:
        # The process is useless without its urls; clean it up rather than
        # leaking it until interpreter exit.
        process.terminate()
        atexit.unregister(process.terminate)

        captured = "".join(output).strip()
        msg = "Cloudflared failed to start."
        if captured:
            # Surface cloudflared's own output so the caller can diagnose the
            # failure (bad port, network error, unsupported arch, ...).
            msg = f"Cloudflared failed to start. cloudflared output:\n{captured}"
        raise RuntimeError(msg)

    @staticmethod
    def _print(tunnel_url: str, metrics_url: str) -> None:
        print(f" * Running on {tunnel_url}")  # noqa: T201
        print(f" * Traffic stats available on {metrics_url}")  # noqa: T201

    def terminate(self, port: int | str) -> None:
        """
        terminates the cloudflared tunnel on the given port

        Parameters
        ----------
        port : int | str
            port to terminate the tunnel on.

        Raises
        ------
        ValueError
            When the port is not running
        """
        port = int(port)
        if port in self.running:
            self.running[port].process.terminate()
            atexit.unregister(self.running[port].process.terminate)
            del self.running[port]
        else:
            msg = f"port {port!r} is not running."
            raise ValueError(msg)


try_cloudflare = TryCloudflare()
