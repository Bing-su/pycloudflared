from __future__ import annotations

import atexit
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

from .util import download, get_info

url_pattern = re.compile(r"(?P<url>https?://\S+\.trycloudflare\.com)")
metrics_pattern = re.compile(r"(?P<url>127\.0\.0\.1:\d+/metrics)")


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

        if info.system == "darwin" and info.machine == "arm64":
            args = ["arch", "-x86_64"] + args

        cloudflared = subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            encoding="utf-8",
        )

        atexit.register(cloudflared.terminate)

        tunnel_url = metrics_url = ""

        lines = 20
        for _ in range(lines):
            line = cloudflared.stderr.readline()

            url_match = url_pattern.search(line)
            metric_match = metrics_pattern.search(line)
            if url_match:
                tunnel_url = url_match.group("url")
            if metric_match:
                metrics_url = "http://" + metric_match.group("url")

            if tunnel_url and metrics_url:
                break

        else:
            raise RuntimeError("Cloudflared failed to start")

        urls = Urls(tunnel_url, metrics_url, cloudflared)
        if verbose:
            self._print(urls.tunnel, urls.metrics)

        self.running[port] = urls
        return urls

    @staticmethod
    def _print(tunnel_url: str, metrics_url: str) -> None:
        print(f" * Running on {tunnel_url}")
        print(f" * Traffic stats available on {metrics_url}")

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
            raise ValueError(f"port {port!r} is not running.")


try_cloudflare = TryCloudflare()
