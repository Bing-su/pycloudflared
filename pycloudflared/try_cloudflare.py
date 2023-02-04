from __future__ import annotations

import atexit
import re
import subprocess
from pathlib import Path

from .util import download, get_info

url_pattern = re.compile(r"(?P<url>https?://\S+.trycloudflare.com)")
metrics_pattern = re.compile(r"(?P<url>127.0.0.1:\d+/metrics)")


def try_cloudflare(
    port: int | str, metrics_port: int | str | None = None, verbose: bool = True
) -> str:
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
    str
        tunnel url

    Raises
    ------
    RuntimeError
        When cloudflared fails to start
    """
    info = get_info()
    if not Path(info.executable).exists():
        download(info)

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

    lines = 0
    tunnel_url = metrics_url = ""

    while lines < 20:
        lines += 1
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

    if verbose:
        print(f" * Running on {tunnel_url}")
        print(f" * Traffic stats available on {metrics_url}")
    return tunnel_url
