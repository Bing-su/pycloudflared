from __future__ import annotations

import platform
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen

from tqdm.auto import tqdm

try:
    import tomllib
except ImportError:
    import tomli as tomllib


download_url_file = Path(__file__).parent / "download_url.toml"
with download_url_file.open("rb") as f:
    download_url = tomllib.load(f)


@dataclass
class Info:
    system: str
    machine: str

    def __post_init__(self):
        self.system = self.system.lower()
        self.machine = self.machine.lower()

        if self.system not in download_url:
            msg = f"{self.system!r} is not supported."
            raise RuntimeError(msg)

        urls = download_url[self.system]
        if self.machine not in urls:
            msg = f"{self.machine!r} is not supported on {self.system}."
            raise RuntimeError(msg)

        self.url: str = urls[self.machine]["url"]
        root = Path(__file__).parent

        if self.system == "darwin":
            self.executable = str(root / "cloudflared")
        else:
            self.executable = str(root / self.url.split("/")[-1])


def get_info() -> Info:
    return Info(platform.system(), platform.machine())


def download(info: Info | None = None) -> str:
    """
    Downloads the cloudflared binary from the official cloudflared github.

    Parameters
    ----------
        info: Info | None
            information about the system and machine architecture

    Returns
    -------
        str
            The path to the cloudflared excutable file
    """
    if info is None:
        info = get_info()

    dest = Path(__file__).parent / info.url.split("/")[-1]

    with urlopen(info.url) as resp:  # noqa: S310
        total = int(resp.headers.get("Content-Length", 0))
        with tqdm.wrapattr(
            resp, "read", total=total, desc="Download cloudflared..."
        ) as src, dest.open("wb") as dst:
            shutil.copyfileobj(src, dst)

    if info.system == "darwin":
        # macOS file is a tgz archive
        shutil.unpack_archive(dest, dest.parent)
        dest.unlink()
        excutable = dest.parent / "cloudflared"
    else:
        excutable = dest
    excutable.chmod(0o777)

    return str(excutable)


def remove_executable(info: Info | None = None) -> None:
    """
    Removes the cloudflared executable
    """
    if info is None:
        info = get_info()
    if Path(info.executable).exists():
        Path(info.executable).unlink()
