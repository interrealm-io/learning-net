"""HTTP server for the web explorer.

Serves the same nine tools as the MCP server — the handler table is imported
from server.py, not reimplemented, so the two surfaces cannot drift — plus the
built React bundle as static files.

Standard library only, like the rest of the core. ThreadingHTTPServer is
enough for a classroom or a district box, and the bundle is read through
importlib.resources so the same code serves from a wheel, an editable
checkout, or inside the zipapp, where there is no filesystem path to serve
from.
"""

from __future__ import annotations

import json
import mimetypes
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from urllib.parse import parse_qs, urlparse

from .graph import Graph, GraphError
from .server import _handlers, _prune

DEFAULT_PORT = 8788

# The only integer-typed params in the tool schemas; everything else is text.
_INT_PARAMS = {"limit", "maxDepth", "childLimit"}


def _coerce(query_string):
    out = {}
    for k, vals in parse_qs(query_string).items():
        v = vals[-1]
        # Strict: a bad int (limit=1.5, limit=abc) raises ValueError here and
        # becomes a 400 in _api, instead of reaching SQL as a string.
        out[k] = int(v) if k in _INT_PARAMS else v
    return out


class _ThreadGraphs:
    """One read-only connection per server thread.

    A single sqlite3 connection shared across ThreadingHTTPServer threads
    raises InterfaceError under concurrent reads (the detail page fires five
    at once). Read-only connections are cheap, so each thread opens its own
    on first use instead of sharing one behind a lock.
    """

    def __init__(self, db_path):
        Graph(db_path).close()  # fail fast at startup if the mirror is missing
        self.db_path = db_path
        self._local = threading.local()

    def handlers(self):
        if not hasattr(self._local, "handlers"):
            self._local.handlers = _handlers(Graph(self.db_path))
        return self._local.handlers


class _Handler(BaseHTTPRequestHandler):
    graphs = None  # bound per-server in make_server

    # Keep-alive matters here: ThreadingHTTPServer threads live per connection,
    # so without it every request would open a fresh sqlite connection and the
    # per-thread cache in _ThreadGraphs would never get a second hit.
    # (_send always sets Content-Length, which HTTP/1.1 requires.)
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass  # the CLI prints the URL; per-request logging is noise for a kiosk

    def do_GET(self):
        url = urlparse(self.path)
        if url.path.startswith("/api/"):
            self._api(url.path[len("/api/"):], url.query)
        else:
            self._static(url.path)

    def _send(self, code, body, ctype, cache="no-store"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        # Default no-store: API answers must not outlive a sync, and a cached
        # index.html would keep serving a bundle that no longer exists.
        # Hashed assets are the exception — their name changes with content.
        self.send_header("Cache-Control", cache)
        self.end_headers()
        self.wfile.write(body)

    def _api(self, name, query_string):
        fn = self.graphs.handlers().get(name)
        if not fn:
            body = json.dumps({"error": f"unknown tool: {name}"}).encode()
            self._send(404, body, "application/json")
            return
        try:
            result = _prune(fn(**_coerce(query_string)))
            self._send(200, json.dumps(result).encode(), "application/json")
        except (GraphError, TypeError, ValueError) as e:
            body = json.dumps({"error": f"{type(e).__name__}: {e}"}).encode()
            self._send(400, body, "application/json")

    def _static(self, path):
        parts = [p for p in path.split("/") if p and p != "."]
        # ".." covers POSIX; the backslash check covers Windows, where
        # pathlib's joinpath splits on "\" and "..\..\x" would escape.
        if any(p == ".." or "\\" in p for p in parts):
            self._send(404, b"not found", "text/plain")
            return
        root = resources.files("learningnet") / "static"
        target = root.joinpath(*parts) if parts else root / "index.html"
        # Filesystem traversables raise OSError; zipapp ones KeyError/ValueError.
        missing = (OSError, KeyError, ValueError)
        try:
            data = target.read_bytes()
            name = parts[-1] if parts else "index.html"
        except missing:
            # Unknown paths get the app shell; the client router takes it from
            # there. If the shell itself is missing, the bundle was never built.
            try:
                data, name = (root / "index.html").read_bytes(), "index.html"
            except missing:
                self._send(
                    404,
                    b"web bundle missing - build it with `make ui` or reinstall",
                    "text/plain",
                )
                return
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        immutable = parts[:1] == ["assets"] and name != "index.html"
        self._send(
            200, data, ctype,
            cache="public, max-age=31536000, immutable" if immutable else "no-store",
        )


def make_server(db_path, host="127.0.0.1", port=DEFAULT_PORT):
    handler = type("_BoundHandler", (_Handler,), {"graphs": _ThreadGraphs(db_path)})
    return ThreadingHTTPServer((host, port), handler)


def web(db_path, host="127.0.0.1", port=DEFAULT_PORT, open_browser=False):
    srv = make_server(db_path, host, port)
    url = f"http://{host}:{srv.server_address[1]}"
    print(f"  mirror  {db_path}")
    print(f"  {url}")
    if open_browser:
        threading.Timer(0.3, webbrowser.open, (url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  stopped")
    finally:
        srv.server_close()
