# pycloudflared

python cloudflared wrapper

## Install

```sh
pip install pycloudflared
```

Cloudflare binaries will be downloaded the first time you run it.

## Usage

```sh
❯ pycloudflared --help
NAME:
   cloudflared - Cloudflare's command-line tool and agent

USAGE:
   cloudflared [global options] [command] [command options]

VERSION:
   2023.2.1 (built 2023-02-03-1038 UTC)

DESCRIPTION:
   cloudflared connects your machine or user identity to Cloudflare's global network.
     You can use it to authenticate a session to reach an API behind Access, route web traffic to this machine,
     and configure access control.

     See https://developers.cloudflare.com/cloudflare-one/connections/connect-apps for more in-depth documentation.
```

All arguments are passed directly to cloudflared.

Since there is no binary for arm mac, you may need Rosetta 2.


### try_cloudflared

```py
from pycloudflared import try_cloudflare

try_cloudflare(port=7860)
```

A simple function to run trycloudflare within python.
