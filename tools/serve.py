#!/usr/bin/env python3
"""Tool 3: host the page locally.

    python tools/serve.py            # then open http://127.0.0.1:8000
    python tools/serve.py --port 9000

Serves the `web/` folder. The page's "Actualizar datos" button calls
POST /api/refresh, which fetches governors and senators again from the sources
(at most once a minute) and rewrites web/data/politicians.json.
"""
import argparse
import json
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from informate.live import ThrottledRefresh  # noqa: E402
from informate.refresh import new_session, refresh_politicians  # noqa: E402

WEB = ROOT / "web"
refresh = ThrottledRefresh(
    lambda: refresh_politicians(
        WEB / "data" / "politicians.json", new_session(), cache_dir=ROOT / ".cache",
        catalog_path=WEB / "data" / "municipios.topojson",
    )
)


class Handler(SimpleHTTPRequestHandler):
    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/status":
            self._json(200, {"live": True})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != "/api/refresh":
            self._json(404, {"error": "No existe."})
            return
        try:
            self._json(200, refresh())
        except Exception as error:  # report any source failure to the page
            self._json(502, {"error": f"{type(error).__name__}: {error}"})

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache")  # always check for the newest page and data
        super().end_headers()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1", help="default: this computer only")
    args = parser.parse_args()

    missing = [name for name in ("municipios.topojson", "map_source.json", "politicians.json")
               if not (WEB / "data" / name).exists()]
    if missing:
        print(f"Faltan datos ({', '.join(missing)}). Ejecuta primero:")
        print("  python tools/build_map.py\n  python tools/fetch_politicians.py")
        sys.exit(1)

    server = ThreadingHTTPServer((args.host, args.port), partial(Handler, directory=str(WEB)))
    print(f"México en datos en http://{args.host}:{args.port}  (Ctrl+C para detener)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
