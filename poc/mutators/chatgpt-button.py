"""
mutator:chatgpt-button — ACTIVE. Injects UI into chatgpt.com live, via the proxy.

Unlike a reader (which reads the persisted stream, downstream, read-only), a
mutator rewrites the response BEFORE it reaches the browser — so it lives in the
tap (addon), not the reader catalog. This is the write-back axis.

What it does to chatgpt.com HTML documents:
  1. strips CSP   — else the browser blocks our injected <script> (THE mitm trick)
  2. injects your UI lib (inem/chathpt-ui.js) + a bootstrap that adds a
     top-right "dopo" button next to Share, wired to your infra.

Run:  mitmdump -s chatgpt-button.py
Lib:  TAP_UI_JS=/path/to/chatgpt-ui.js   (defaults to ~/Code/chathpt-ui.js/chatgpt-ui.js)
"""
import os

UI_JS_PATH = os.path.expanduser(os.environ.get("TAP_UI_JS", "~/Code/chathpt-ui.js/chatgpt-ui.js"))

# runs in MAIN world after the lib; idempotent add survives SPA re-renders
BOOTSTRAP = r"""
(function(){
  function add(){
    if(!window.ChatGPTUI) return;
    window.ChatGPTUI.addTopHeaderButton({
      id:'tap-dopo', icon:'↗', label:'dopo', title:'Send to dopo',
      onClick:function(){ window.open('https://dopo.st/new?src=chatgpt','_blank'); }
    });
  }
  setInterval(add, 1500);
})();
"""

def _lib():
    try:
        return open(UI_JS_PATH).read()
    except OSError:
        return ""   # no lib present → bootstrap no-ops (ChatGPTUI undefined)

def inject(html, lib):
    tag = "<script>\n" + lib + "\n" + BOOTSTRAP + "\n</script>"
    if "</body>" in html:
        return html.replace("</body>", tag + "</body>", 1)
    return html + tag

# --- mitmproxy hook (only runs under mitmdump) ---
def response(flow):
    if "chatgpt.com" not in flow.request.pretty_host:
        return
    r = flow.response
    if r is None or "text/html" not in r.headers.get("content-type", ""):
        return
    for h in ("content-security-policy", "content-security-policy-report-only"):
        r.headers.pop(h, None)                      # relax CSP so the script runs
    r.set_text(inject(r.get_text(), _lib()))

# --- self-check: python3 chatgpt-button.py  (no mitmproxy needed) ---
if __name__ == "__main__":
    sample = ('<html><head></head><body>'
              '<div id="conversation-header-actions"></div></body></html>')
    out = inject(sample, "window.ChatGPTUI={ok:1};")
    assert "window.ChatGPTUI" in out, "lib not injected"
    assert "tap-dopo" in out, "bootstrap not injected"
    assert out.count("</body>") == 1, "body duplicated"
    assert out.index("<script>") < out.index("</body>"), "script not before </body>"
    print("self-check OK: CSP-strip + lib + bootstrap injected before </body>")
