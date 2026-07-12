from __future__ import annotations

import atexit
import os
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

from .util import download, get_info

DEFAULT_LINES_TO_CHECK = 50

url_pattern = re.compile(r"(?P<url>https?://\S+\.trycloudflare\.com)")
metrics_pattern = re.compile(r"(?P<url>127\.0\.0\.1:\d+/metrics)")


def get_lines_to_check() -> int:
    return int(os.getenv("PYCLOUDFLARED_LINES_TO_CHECK", DEFAULT_LINES_TO_CHECK))


class TunnelUrls(NamedTuple):
    tunnel: str
    metrics: str
    process: subprocess.Popen

class AccessUrls(NamedTuple):
    tunnel: str
    local_address: str
    process: subprocess.Popen


class TryCloudflare:
    def __init__(self):
        self.running: dict[int, TunnelUrls] = {}
        self.running_access: dict[int, AccessUrls] = {}

    def tunnel(
        self,
        port: int | str,
        scheme: str,
        host: str = 'localhost',
        metrics_port: int | str | None = None,
        verbose: bool = True,
    ) -> TunnelUrls:
        """
        `cloudflared tunnel ...` to expose a local service to a public URL
        <https://try.cloudflare.com>

        Parameters
        ----------
        port : int | str
            port to launch the tunnel on.
        scheme : str
            the protocol scheme to use for the tunnel (e.g. "http", "tcp").
        host : str, optional, default 'localhost'
            the local host/address the service is running on.
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
        local_address = f"{scheme}://{host}:{port}"
        if port in self.running:
            urls = self.running[port]
            if verbose:
                self._print_tunnel(local_address, urls.tunnel, urls.metrics)
            return urls

        args = [
            info.executable,
            "tunnel",
            "--url",
            local_address,
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

        tunnel_url = metrics_url = ""

        lines = get_lines_to_check()
        for _ in range(lines):
            line = cloudflared.stderr.readline()  # pyright: ignore[reportOptionalMemberAccess]

            url_match = url_pattern.search(line)
            metric_match = metrics_pattern.search(line)
            if url_match:
                tunnel_url = url_match.group("url")
            if metric_match:
                metrics_url = "http://" + metric_match.group("url")

            if tunnel_url and metrics_url:
                break

        else:
            msg = "Cloudflared failed to start"
            raise RuntimeError(msg)

        urls = TunnelUrls(tunnel_url, metrics_url, cloudflared)
        if verbose:
            self._print_tunnel(local_address, urls.tunnel, urls.metrics)

        self.running[port] = urls
        return urls

    def access(
        self,
        cloudflare_hostname: str,
        port: int | str,
        host: str = "localhost",
        scheme: str = 'tcp',
        verbose: bool = True,
    ) -> AccessUrls:
        """
        `cloudflared access ...` to connect to an existing tunnel and expose it
        as a local address.
        <https://try.cloudflare.com>

        Parameters
        ----------
        cloudflare_hostname : str
            the public hostname of the existing cloudflare tunnel to connect to.
        port : int | str
            local port that cloudflared will bind to, proxying traffic to
            the remote tunnel.
        host : str, optional, default 'localhost'
            local host/address that cloudflared will bind to.
        scheme : str, optional, default 'tcp'
            protocol label for clarity/logging only has no functional effect
            options: tcp, rdp, ssh, smb
            Note: does not support http or https
        verbose : bool, default True
            print the local address and remote hostname being connected

        Returns
        -------
        AccessUrls (NamedTuple)
            cloudflare_hostname: str, the remote tunnel hostname
            local_address: str, the local "host:port" cloudflared is bound to
            process: subprocess.Popen, cloudflared process Popen object
        """
        info = get_info()
        if not Path(info.executable).exists():
            download(info)

        port = int(port)
        if port in self.running_access:
            urls = self.running_access[port]
            if verbose:
                self._print_access(urls.tunnel, urls.local_address)
            return urls

        local_address = f"{scheme}://{host}:{port}"

        args = [
            info.executable,
            "access",
            scheme,
            "--hostname",
            cloudflare_hostname,
            "--url",
            local_address,
        ]

        cloudflared = subprocess.Popen(  # noqa: S603
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        atexit.register(cloudflared.terminate)

        urls = AccessUrls(cloudflare_hostname, local_address, cloudflared)
        if verbose:
            self._print_access(urls.tunnel, urls.local_address)

        self.running_access[port] = urls
        return urls

    @staticmethod
    def _print_access(tunnel_url: str, local_address: str) -> None:
        print(f" * Proxying [{tunnel_url}] -> [{local_address}]")  # noqa: T201

    @staticmethod
    def _print_tunnel(local_address: str, tunnel_url: str, metrics_url: str) -> None:
        print(f" * Forwarding [{local_address}] -> [{tunnel_url}]")  # noqa: T201
        print(f"   Traffic statistics: [{metrics_url}]")  # noqa: T201

    def terminate(self, port: int | str) -> None:
        """
        terminates the cloudflared tunnel or access process on the given port

        Parameters
        ----------
        port : int | str
            port to terminate the tunnel or access process on.

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
        elif port in self.running_access:
            self.running_access[port].process.terminate()
            atexit.unregister(self.running_access[port].process.terminate)
            del self.running_access[port]
        else:
            msg = f"port {port!r} is not running."
            raise ValueError(msg)


try_cloudflare = TryCloudflare()
