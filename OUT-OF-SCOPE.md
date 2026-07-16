# Out of scope (this version)

What this version **does**: captures **browser** chat sessions (ChatGPT, Claude)
by routing the browser through an always-on mitmproxy. That's the whole product.

Everything below is deliberately left out — noted here so the boundary is
explicit and the recipes aren't lost.

## CLI / app capture (the env-var layer)

Terminal tools (`curl`, `git`, `node`, `python`) and non-browser apps ignore the
system proxy. They only follow the `HTTP_PROXY` / `HTTPS_PROXY` environment
variables. So they go direct — nothing captures them unless you opt in.

**Why it's not in this version:** it caused every connectivity break during
development, and it's fiddly — each tool has its own CA trust store, so routing
alone isn't enough; you also have to point each one at mitmproxy's cert, or it
errors with `certificate verify failed`.

**If you ever want it**, both blocks are required:

```bash
# 1. route CLI traffic through mitmproxy
export HTTPS_PROXY=http://127.0.0.1:8899
export HTTP_PROXY=http://127.0.0.1:8899
export NO_PROXY=localhost,127.0.0.1,::1,.local

# 2. make each tool trust mitmproxy's cert (no shared trust store)
export SSL_CERT_FILE=~/.mitmproxy/mitmproxy-ca-cert.pem        # curl, openssl
export REQUESTS_CA_BUNDLE=~/.mitmproxy/mitmproxy-ca-cert.pem   # python
export NODE_EXTRA_CA_CERTS=~/.mitmproxy/mitmproxy-ca-cert.pem  # node
git config --global http.sslCAInfo ~/.mitmproxy/mitmproxy-ca-cert.pem
```

Put block 1+2 in `~/.zshenv` to make it permanent (new shells only; running
processes pick it up on restart). Caveat: those tools now depend on mitmproxy
being up before they start.

## Cert trust is manual

`doctor` confirms the cert is *in a keychain*, not that it's *trusted*. Marking
it Always Trust is a manual step (open `mitm.it` with the proxy on). Automating
it needs `security add-trusted-cert` with admin.

## launchd handoff needs a clean moment

Activating the always-on service while a mitmproxy is already on 8899 requires
stopping the running one first — which breaks anything currently routed through
it. There's no seamless in-place handoff.

## Housekeeping not handled

- **Log rotation** — `/tmp/chat-collector.log` grows unbounded.
- **Dump retention** — `~/chat-dumps/` keeps the latest snapshot per conversation
  forever; no pruning.
- **More services** — only ChatGPT and Claude regexes ship. Add a row to
  `SERVICES` in `chat_collector.py` for others.
