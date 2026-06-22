#!/usr/bin/env python3
"""Live-reloading static server for the Petoskey Pit web viewer.

Serves ``web_viewer/`` over HTTP and pushes a browser reload whenever the
files it depends on change — so the viewer stays in sync with edits in real
time. Pairs with the ``amphitheatre`` cloudflared tunnel
(``amphitheatre.scarrow.net`` -> ``127.0.0.1:8788``) for a private/unlisted URL;
see scripts/serve_viewer.sh.

Mechanism (no third-party deps — pure stdlib):
  - any ``.html`` response gets a tiny EventSource client injected before
    ``</body>``; it listens on ``/__livereload`` and calls ``location.reload()``
    on a ``reload`` event.
  - ``GET /__livereload`` is a long-lived Server-Sent-Events stream. A single
    background watcher thread polls file (path, mtime, size) signatures and
    bumps a version counter on change; open SSE streams notice and emit.

Two watch sets:
  1. ``web_viewer/`` itself (always). Catches direct edits to index.html and,
     crucially, regeneration of ``web_viewer/data/site_data.js`` — the viewer's
     entire data payload. A reload re-fetches it.
  2. upstream sources (only with ``--rebuild``): the GeoJSON / DEM / validation
     files that ``scripts/build_truth_package.py`` reads. On change, the build
     is re-run (blocking, debounced); it rewrites site_data.js, and we then fire
     exactly one reload. So "edit a source -> viewer updates" works end to end.

Usage:
    python scripts/serve_viewer.py                 # serve + live reload on web_viewer/
    python scripts/serve_viewer.py --rebuild       # also rebuild on source edits
    python scripts/serve_viewer.py --port 8788 --rebuild
    python scripts/serve_viewer.py --host 100.64.0.32 --port 8788   # tailnet-only, read-only
    python scripts/serve_viewer.py --root /srv/petoskey/web_viewer  # served root outside the repo
"""
from __future__ import annotations

import argparse
import functools
import os
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_ROOT = os.path.join(REPO, "web_viewer")

# Source files build_truth_package.py consumes; edits here trigger a rebuild
# under --rebuild. Globs are resolved relative to the repo root.
SOURCE_GLOBS = [
    "vectors_geojson/*.geojson",
    "design_open_low/stage_floor.geojson",
    "analysis/tier_emission/Scenario_E_baseline_reemit/validation.json",
    "analysis/decision_packet/decision_table.csv",
    "dem/*.tif",
    "dem/in_situ_grading_manifest.json",
    "scripts/build_truth_package.py",
    "scripts/in_situ_common.py",
]

# ── live-reload client, injected into every HTML response ────────────────────
LIVERELOAD_SNIPPET = b"""
<script>
(function () {
  var es, retry = 0;
  function connect() {
    es = new EventSource("/__livereload");
    es.addEventListener("reload", function () { location.reload(); });
    es.onopen = function () { retry = 0; };
    es.onerror = function () {
      es.close();
      retry = Math.min(retry + 1, 10);
      setTimeout(connect, 250 * retry);   // backoff, also reconnects after a server restart
    };
  }
  connect();
})();
</script>
"""

# Bumped by the watcher thread on any observed change; read by SSE handlers.
_version = 0
_version_lock = threading.Condition()


def _bump_version() -> None:
    global _version
    with _version_lock:
        _version += 1
        _version_lock.notify_all()


def _iter_files(root: str):
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            yield os.path.join(dirpath, name)


def _signature(paths) -> tuple:
    sig = []
    for path in paths:
        try:
            st = os.stat(path)
            sig.append((path, int(st.st_mtime_ns), st.st_size))
        except OSError:
            sig.append((path, 0, -1))  # missing — still part of the signature
    return tuple(sorted(sig))


def _resolve_globs(globs) -> list:
    import glob

    out = []
    for g in globs:
        out.extend(glob.glob(os.path.join(REPO, g)))
    return out


def _run_build() -> bool:
    """Re-run build_truth_package.py with the repo venv if present. Returns ok."""
    py = os.path.join(REPO, ".venv", "bin", "python")
    if not os.path.exists(py):
        py = sys.executable
    script = os.path.join(REPO, "scripts", "build_truth_package.py")
    print(f"[serve_viewer] source changed -> rebuilding ({os.path.basename(py)})", flush=True)
    t0 = time.time()
    try:
        proc = subprocess.run(
            [py, script], cwd=REPO, capture_output=True, text=True, timeout=600
        )
    except subprocess.TimeoutExpired:
        print("[serve_viewer] BUILD TIMEOUT (>600s)", file=sys.stderr, flush=True)
        return False
    if proc.returncode != 0:
        print(
            f"[serve_viewer] BUILD FAILED rc={proc.returncode}:\n{proc.stderr.strip()[-1500:]}",
            file=sys.stderr,
            flush=True,
        )
        return False
    tail = (proc.stdout.strip().splitlines() or ["(no output)"])[-1]
    print(f"[serve_viewer] rebuilt in {time.time() - t0:.1f}s — {tail}", flush=True)
    return True


def _watch(interval: float, rebuild: bool, web_root: str = WEB_ROOT) -> None:
    """Background poller: bump the reload version when watched files change."""
    src_paths = _resolve_globs(SOURCE_GLOBS) if rebuild else []
    wv_sig = _signature(_iter_files(web_root))
    src_sig = _signature(src_paths) if rebuild else ()
    first = True
    while True:
        time.sleep(interval)
        if rebuild:
            # Re-resolve globs so newly created source files are picked up.
            src_paths = _resolve_globs(SOURCE_GLOBS)
            new_src = _signature(src_paths)
            if new_src != src_sig and not first:
                src_sig = new_src
                if _run_build():
                    # Sync the web_viewer baseline so the build's own write to
                    # site_data.js doesn't also fire a second reload, then bump.
                    wv_sig = _signature(_iter_files(web_root))
                    _bump_version()
                continue
            src_sig = new_src
        new_wv = _signature(_iter_files(web_root))
        if new_wv != wv_sig and not first:
            wv_sig = new_wv
            print("[serve_viewer] web_viewer changed -> reload", flush=True)
            _bump_version()
        else:
            wv_sig = new_wv
        first = False


class Handler(SimpleHTTPRequestHandler):
    """Static handler that injects live-reload into HTML and serves the SSE feed."""

    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # quieter than the default per-request spew
        if "/__livereload" not in (self.path or ""):
            sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    # ---- SSE live-reload endpoint ----
    def do_GET(self):  # noqa: N802 (stdlib casing)
        if self.path.split("?")[0] == "/__livereload":
            return self._serve_sse()
        return super().do_GET()

    def _serve_sse(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            with _version_lock:
                last = _version
            self.wfile.write(b"retry: 1000\n\n")
            self.wfile.flush()
            while True:
                with _version_lock:
                    if not _version_lock.wait_for(lambda: _version != last, timeout=15):
                        # heartbeat comment keeps the connection (and tunnel) alive
                        self.wfile.write(b": ping\n\n")
                        self.wfile.flush()
                        continue
                    last = _version
                self.wfile.write(b"event: reload\ndata: 1\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            return

    # ---- HTML injection ----
    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            # let the parent handle directory-index redirect / listing,
            # except when an index.html exists (the common case) we inject.
            index = os.path.join(path, "index.html")
            if os.path.exists(index):
                path = index
            else:
                return super().send_head()
        if path.endswith(".html") and os.path.exists(path):
            return self._send_html_with_reload(path)
        return super().send_head()

    def _send_html_with_reload(self, path: str):
        try:
            with open(path, "rb") as fh:
                body = fh.read()
        except OSError:
            self.send_error(404, "File not found")
            return None
        marker = b"</body>"
        idx = body.rfind(marker)
        if idx == -1:
            body = body + LIVERELOAD_SNIPPET
        else:
            body = body[:idx] + LIVERELOAD_SNIPPET + body[idx:]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8788, help="listen port (default 8788, matches the tunnel)")
    ap.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1; use the tailnet IP for a tailnet-only listener)")
    ap.add_argument("--root", default=None,
                    help="static directory to serve read-only (default: the repo's web_viewer/). "
                         "Set this when serve_viewer.py is deployed outside the repo tree.")
    ap.add_argument("--interval", type=float, default=0.5, help="file-poll interval seconds (default 0.5)")
    ap.add_argument("--rebuild", action="store_true", help="also re-run build_truth_package.py on source edits")
    args = ap.parse_args()

    # Resolve the served root. Defaults to the repo's web_viewer/; --root lets the
    # same stdlib server be relocated (e.g. an LXC that only has web_viewer/ copied
    # in, not the whole repo). The server is GET/HEAD-only and SimpleHTTPRequestHandler
    # confines every request under this directory (translate_path strips '..'), so the
    # root is the hard read-only sandbox boundary.
    serve_root = os.path.abspath(args.root) if args.root else WEB_ROOT
    if not os.path.isdir(serve_root):
        print(f"[serve_viewer] root not found / not a directory: {serve_root}", file=sys.stderr)
        return 2
    if not os.path.exists(os.path.join(serve_root, "data", "site_data.js")):
        print("[serve_viewer] NOTE: data/site_data.js missing under the served root — "
              "run scripts/build_truth_package.py (or pass --rebuild and edit a source).",
              file=sys.stderr)

    watcher = threading.Thread(target=_watch, args=(args.interval, args.rebuild, serve_root), daemon=True)
    watcher.start()

    handler = functools.partial(Handler, directory=serve_root)
    httpd = ThreadingHTTPServer((args.host, args.port), handler)
    httpd.daemon_threads = True
    mode = "live-reload + rebuild-on-source-edit" if args.rebuild else "live-reload"
    print(f"[serve_viewer] serving (read-only, GET/HEAD) {serve_root}", flush=True)
    print(f"[serve_viewer] http://{args.host}:{args.port}/  ({mode})", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve_viewer] shutting down", flush=True)
        httpd.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
