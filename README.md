# chat-collector

Passive collector for full chat-session JSON. It sits as a mitmproxy addon on
your own traffic: when you open a conversation, the web app itself fetches the
whole message tree — this catches that response and writes it to disk.
Overwrite = latest full snapshot. Domain-agnostic: add a service, add a row.

## Why a proxy (not an extension / not CDP)

- **Extension** is per-site — you rewrite it for every app's DOM and fetch shape.
- **CDP** is domain-agnostic but needs the browser started with
  `--remote-debugging-port`. Arc strips that flag, so CDP is dead there.
- **mitmproxy** is the one layer that's domain-agnostic *and* survives a
  hostile browser: it sees every response, you just filter by URL.

## Install

```bash
brew install mitmproxy
```

## On / off

```bash
collector on       # start mitmdump, confirm it's up, THEN arm the proxy
collector off      # disarm the proxy, confirm it's off, THEN stop mitmdump
collector status   # process up? proxy armed or direct?
```

**Fail-safe by construction.** The only way a proxy setup breaks your net is
"proxy armed at a port with no live proxy behind it". So the handle enforces
strict ordering and never trusts `networksetup`'s exit code — it reads the
state back:

- `on` won't arm the proxy until mitmdump is actually listening on the port.
- `off` won't kill mitmdump until it has **confirmed** the proxy read back off.
  Can't confirm? It refuses to kill and tells you — your net stays up.

`off` means *truly off*: proxy disarmed, traffic direct, mitmproxy out of the
path. Dumps land in `~/chat-dumps/<service>/<id>.json`; log `/tmp/chat-collector.log`.
Edit `SVC` if your network service isn't `Wi-Fi`
(`networksetup -listnetworkserviceorder`).

### The one admin gate

macOS requires admin to flip the system proxy. Out of the box, on/off show the
**native password popup** (one dialog per toggle, whole batch at once) — zero
setup.

Tired of the popup? Add a one-time passwordless rule scoped to *only* the proxy
subcommands, and on/off go silent:

```bash
sudo visudo -f /etc/sudoers.d/chat-collector
# paste sudoers.snippet (edit the username), save — visudo syntax-checks it
```

The script tries the silent `sudo -n` path first and falls back to the popup,
so the rule is a pure upgrade — never required.

The CA cert must also be trusted **once** (below) before `on` captures TLS.

## Run it by hand instead

```bash
mitmdump -s ~/Code/chat-collector/chat_collector.py -p 8899
```

...then set the proxy yourself. Each caught dump prints
`[chat-collector] <service> <id> -> ...`.

## One-time setup (yours — needs admin)

1. **Point the browser at the proxy** — set HTTP/HTTPS proxy to `127.0.0.1:8899`
   (System Settings → Network → your interface → Proxies, or per-app).
2. **Trust the CA cert** — first run generates `~/.mitmproxy/mitmproxy-ca-cert.pem`.
   Add it to the login keychain and mark it trusted, or visit
   [mitm.it](http://mitm.it) while the proxy runs.

Without both, TLS won't decrypt and nothing gets captured.

### Localhost gotcha

The proxy will also intercept `localhost` traffic and can break local dev apps
(websockets, etc.). Add a proxy bypass for `localhost, 127.0.0.1, *.local`.

## Adding a service

One row in `SERVICES` in `chat_collector.py`. The regex must match **only** the
full-conversation GET (with the id), not list or subpath endpoints:

```python
SERVICES = [
    ("chatgpt", re.compile(r"/backend-api/conversation/(?P<id>" + UUID + r")(?:$|\?)")),
    ("claude",  re.compile(r"/chat_conversations/(?P<id>" + UUID + r")(?:$|\?|/)")),
]
```

## Test

No mitmproxy needed — the matcher self-checks:

```bash
python3 chat_collector.py
# self-check OK: 3 hits, 4 non-matches
```

Captures only `200` JSON responses; anything else is skipped without crashing
the proxy.
