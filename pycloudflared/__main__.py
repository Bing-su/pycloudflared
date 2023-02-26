import subprocess
import sys
from pathlib import Path

from .util import download, get_info


def main():
    "main cli entrypoint"
    info = get_info()
    if not Path(info.executable).exists():
        download(info)
    args = sys.argv[1:]
    try:
        subprocess.run([info.executable, *args])
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
