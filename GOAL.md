# Goal

**A passive observatory of your own digital exchange.**

An always-on point on the wire between your apps and the network that quietly
writes down a full, decrypted transcript of everything that passes through it.

The near task: save your **browser chat sessions** (ChatGPT, Claude…) whole —
not a screenshot, not a fragment, the entire conversation graph as the app
itself fetches it.

The deeper point: by *just observing* your real traffic, you accumulate an exact
map of how the services you touch actually work — their API contract, auth,
pagination, error shapes — for free, invisibly, from live use rather than from
probing or docs. The recorder is always on, costs nothing, and grows with you.

## What it is *not*

- Not active reverse-engineering — nothing is probed or fuzzed; the two parties
  already speak the full protocol in front of you, you just read it.
- Not a complete API map — you only see what actually flows. Endpoints you never
  hit stay dark. The map mirrors your **usage**, not the whole service.

## How the intent got here

It started narrower and climbed:

```
"can you sniff traffic?"            → object was: traffic
"dump ChatGPT sessions"             → object was: completeness
"an external script isn't ChatGPT-only?" → object was: any domain
"dump your own session too"         → object was: my own trail
```

Three shifts upward in abstraction: not *traffic*, not *ChatGPT*, not *someone
else's* — but a total passive capture of your own exchange, of which chat
sessions are the first view.
