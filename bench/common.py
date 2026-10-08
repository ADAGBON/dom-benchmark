"""Shared helpers: serve the four production builds from one local static server."""
import functools
import http.server
import socketserver
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

APPS = {
    "React": ROOT / "react-todo" / "dist",
    "Angular": ROOT / "angular-todo" / "dist" / "angular-todo" / "browser",
    "Vue": ROOT / "vue-todo" / "dist",
    "Svelte": ROOT / "svelte-todo" / "dist",
}


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True  # back-to-back runs reuse the same ports
    daemon_threads = True


def serve_all(base_port: int = 5170):
    """Start one static server per app on consecutive ports. Returns {framework: url}."""
    urls = {}
    for i, (name, path) in enumerate(APPS.items()):
        if not (path / "index.html").exists():
            raise SystemExit(f"{name} build missing at {path} — run `npm run build:all` first")
        handler = functools.partial(_Quiet, directory=str(path))
        httpd = _Server(("127.0.0.1", base_port + i), handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        urls[name] = f"http://127.0.0.1:{base_port + i}/"
    return urls


def open_app(page, url):
    page.goto(url)
    page.wait_for_function("window.__bench !== undefined")
