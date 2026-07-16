# Architecture — as A—r—B triples

The whole setup, read as relation triples. They fall into three orthogonal
axes that meet at exactly one point: port `8899`.

## Lifecycle — who keeps the process alive

```
launchd    —keeps-alive→   mitmdump
mitmdump   —listens-on→     :8899
mitmdump   —loads→          chat_collector.py  (the addon)
CA cert    —enables→        mitmdump to decrypt TLS
```

## Collection — what the process does

```
addon   —matches→   the full-conversation GET
addon   —writes→    ~/chat-dumps/<service>/<id>.json
```

## Routing — what points traffic at the hub

```
system-proxy   —routes→   browser / GUI-app traffic   ──→   :8899 (mitmdump)
```

**In scope:** one route — the macOS system proxy, carrying browser and GUI-app
traffic.

**Out of scope:** a second route via `HTTP_PROXY`/`HTTPS_PROXY` env vars
(CLI tools, non-browser apps). Deferred — it was the source of every
connectivity break during development. See [OUT-OF-SCOPE.md](OUT-OF-SCOPE.md).

## Control — who manages what

```
collector   —arms/disarms→   system-proxy          (the one routing knob)
collector   —⊥ (leaves)→      mitmdump lifecycle     (that's launchd's job)
collector   —⊥ (leaves)→      env-var routing        (out of scope)
```

## The high-level reading

Three orthogonal axes that used to be fused inside `collector` — which is why
it kept blowing up:

```
   KEEP-ALIVE    ⊥    ROUTING     ⊥    COLLECTION
   (launchd)        (system proxy)     (addon → dumps)
                         │
                 they meet at exactly
                    one point: :8899
```

**Δ — what the whole saga distilled to:** the pain came from `collector` trying
to be all three axes at once — holding the process, steering the route, and
tearing it down in one move. Killing along the *lifecycle* axis severed the
*routing* axis for anything pinned to `:8899`. Separate the axes and they
intersect only at the port → each can be touched without disturbing the others.
`mitmdump` is now a standalone service (launchd's), and `collector` is just one
client of the hub, not its owner.
