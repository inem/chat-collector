"""
capture (dumb) — mitmproxy addon. Knows NOTHING about services.
Writes every text/json response as one jsonl record to the stream.
Readers downstream decide what's interesting.

Run:  mitmdump -s capture.py
"""
import json, os, time

STREAM = os.path.expanduser("~/.chat-collector/stream.jsonl")

def response(flow):
    r = flow.response
    if r is None:
        return
    ctype = r.headers.get("content-type", "")
    # generic reduction only (by content-type) — NOT service knowledge
    if not any(t in ctype for t in ("application/json", "text/")):
        return
    rec = {
        "ts": time.time(),
        "method": flow.request.method,
        "url": flow.request.url,
        "status": r.status_code,
        "ctype": ctype,
        "body": r.get_text(),
    }
    os.makedirs(os.path.dirname(STREAM), exist_ok=True)
    with open(STREAM, "a") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
