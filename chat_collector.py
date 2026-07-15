"""
chat-collector — mitmproxy addon.

Passively dumps full chat-session JSON as it flies past the browser.
When you switch to a conversation, the web app itself fetches the full
tree; we catch that response and write it to disk. Overwrite = latest
full snapshot of the session ("re-download the whole thing").

Add a service = add one row to SERVICES.

Run:   mitmdump -s chat_collector.py
Output: ~/chat-dumps/{service}/{conversation-id}.json
"""

import json
import os
import re
import sys

BASE = os.path.expanduser("~/chat-dumps")

UUID = r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"

# (service-name, url-regex with named group 'id')
# regex must match ONLY the full-conversation GET, not list/subpath endpoints.
SERVICES = [
    ("chatgpt", re.compile(r"/backend-api/conversation/(?P<id>" + UUID + r")(?:$|\?)")),
    ("claude",  re.compile(r"/chat_conversations/(?P<id>" + UUID + r")(?:$|\?|/)")),
]


def match(url):
    for name, rx in SERVICES:
        m = rx.search(url)
        if m:
            return name, m.group("id")
    return None


def response(flow):
    hit = match(flow.request.url)
    if not hit:
        return
    name, cid = hit
    r = flow.response
    if r is None or r.status_code != 200:
        return
    if "application/json" not in r.headers.get("content-type", ""):
        return
    try:
        data = json.loads(r.get_text())
    except Exception:
        return  # ponytail: skip anything that isn't clean JSON, don't crash the proxy

    d = os.path.join(BASE, name)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, cid + ".json")
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[chat-collector] {name} {cid} -> {path}", file=sys.stderr)


# --- self-check: run `python3 chat_collector.py` (no mitmproxy needed) ---
if __name__ == "__main__":
    U = "1e6f6f6a-1111-2222-3333-444455556666"
    hits = {
        "https://chatgpt.com/backend-api/conversation/" + U: ("chatgpt", U),
        "https://chatgpt.com/backend-api/conversation/" + U + "?foo=1": ("chatgpt", U),
        "https://claude.ai/api/organizations/aaaa/chat_conversations/" + U + "?tree=True": ("claude", U),
    }
    misses = [
        "https://chatgpt.com/backend-api/conversations?offset=0&limit=28",  # list, no id
        "https://chatgpt.com/backend-api/conversation/" + U + "/textdocs",  # subpath
        "https://claude.ai/api/organizations/aaaa/chat_conversations",      # list, no id
        "https://chatgpt.com/backend-api/me",
    ]
    for url, want in hits.items():
        assert match(url) == want, f"expected {want} for {url}, got {match(url)}"
    for url in misses:
        assert match(url) is None, f"expected no match for {url}, got {match(url)}"
    print("self-check OK:", len(hits), "hits,", len(misses), "non-matches")
