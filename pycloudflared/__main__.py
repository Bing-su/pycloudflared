import subprocess
import sys
from pathlib import Path

from .util import download, get_info


def main():
    info = get_info()
    if not Path(info.command).exists():
        download(info)
    args = sys.argv[1:]
    try:
        subprocess.run([info.command, *args], stdout=sys.stdout, stderr=sys.stderr)
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
