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

## The model: leave it always on

mitmproxy is cheap — ~0% CPU idle, ~130 MB RAM. There is no resource reason to
toggle it. And toggling the *plumbing* is exactly what bites you (see below), so
the recommended setup is **always-on**: mitmproxy runs as a launchd service, and
you never tear it down.

This version captures **browser & GUI-app** traffic — anything that honors the
macOS system proxy, which `collector on/off` arms and disarms. (Browsers are the
main target; other native/Electron apps that read the system proxy get captured
too.)

CLI tools and non-browser apps don't follow the system proxy (they use
`HTTP_PROXY`/`HTTPS_PROXY` env vars instead), so they go direct and aren't
captured. That's out of scope here — see [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md) if
you ever want to add it.

## Setup from scratch

```bash
brew install mitmproxy
git clone <this-repo> ~/Code/chat-collector    # or anywhere — paths auto-resolve
cd ~/Code/chat-collector
./collector install
```

`collector install` does the mechanical parts — puts `collector` on your PATH,
generates the launchd service with the right paths for wherever you cloned it,
and starts it — then prints **3 manual steps** to finish (they need admin, so
you do them yourself):

1. **Allow the proxy toggle** — paste the printed rule into
   `sudo visudo -f /etc/sudoers.d/chat-collector` (the username is filled in for
   you). Required, since `collector on/off` flip the system proxy.
2. **Start capturing** — `collector on`.
3. **Trust the cert** — open [mitm.it](http://mitm.it) with the proxy on,
   install the cert, mark it **Always Trust**. Without this, HTTPS won't decrypt.

Then `collector doctor` should show all ●. Dumps land in
`~/chat-dumps/<service>/<id>.json`; log at `/tmp/chat-collector.log`.

## `collector` — manage the system-proxy (browser) layer

```bash
collector install         # from-scratch setup (PATH, launchd service) + next steps
collector on              # arm the system proxy (browser/app traffic -> mitmproxy)
collector off             # disarm it (traffic direct again)
collector status          # compact: is mitm up? is capture on?
collector status -v       # verbose: styled breakdown + a plain verdict
collector doctor          # one-time setup health: cert / service / rule / port
collector where           # map of every file this tool touches
```

`status` answers "what's happening **now**" (runtime). `doctor` answers "is it
**set up** right" — each check prints ● ok (with its related file) or ✗ with a
fix command. `where` prints the file map: code, system installs, and outputs.

Compact `status` is a quick glance:

```
mitmproxy  ● up · 12345
browser    ● capturing
cli        ○ direct
```

`status -v` (or `--verbose`) spells out both layers and a one-line verdict so
you always know whether killing mitmproxy would break anything.

**Fail-safe.** `on` arms the proxy then makes a real request through it and
auto-disarms if nothing flows. `off` disarms and confirms it read back off
*before* touching anything. With always-on launchd you rarely need `off` at all
— it's here for when you want the browser to go direct without stopping the
service.

### The admin gate

Flipping the system proxy needs admin. Install a one-time passwordless rule
scoped to *only* the proxy subcommands so `collector` runs silently:

```bash
sudo visudo -f /etc/sudoers.d/chat-collector
# paste sudoers.snippet (edit the username), save — visudo syntax-checks it
```

Without it, `on` aborts cleanly (never hangs, never half-applies).

### Localhost gotcha

The proxy also intercepts `localhost`, which can break local dev apps
(websockets, etc.). `collector` sets a bypass for `localhost, 127.0.0.1, *.local`
automatically.

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
