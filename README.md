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

COMMANDS:
   update     Update the agent if a new version exists
   version    Print the version
   proxy-dns  Run a DNS over HTTPS proxy server.
   service    Manages the cloudflared Windows service
   help, h    Shows a list of commands or help for one command
   Access:
     access, forward  access <subcommand>
   Tunnel:
     tunnel  Use Cloudflare Tunnel to expose private services to the Internet or to Cloudflare connected private users.

GLOBAL OPTIONS:
   --credentials-file value, --cred-file value  Filepath at which to read/write the tunnel credentials [%TUNNEL_CRED_FILE%]
   --region value                               Cloudflare Edge region to connect to. Omit or set to empty to connect to the global region. [%TUNNEL_REGION%]
   --edge-ip-version value                      Cloudflare Edge ip address version to connect with. {4, 6, auto} (default: "4") [%TUNNEL_EDGE_IP_VERSION%]
   --post-quantum, --pq                         When given creates an experimental post-quantum secure tunnel (default: false) [%TUNNEL_POST_QUANTUM%]
   --overwrite-dns, -f                          Overwrites existing DNS records with this hostname (default: false) [%TUNNEL_FORCE_PROVISIONING_DNS%]
   --help, -h                                   show help (default: false)
   --version, -v, -V                            Print the version (default: false)

COPYRIGHT:
   (c) 2023 Cloudflare Inc.
   Your installation of cloudflared software constitutes a symbol of your signature indicating that you accept
   the terms of the Apache License Version 2.0 (https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/license),
   Terms (https://www.cloudflare.com/terms/) and Privacy Policy (https://www.cloudflare.com/privacypolicy/).
```

All arguments are passed directly to cloudflared.

Since there is no binary for arm mac, you may need Rosetta 2.


### try_cloudflared

```py
from pycloudflared import try_cloudflare

try_cloudflare(port=7860)
```

A simple function to run trycloudflare within python.
