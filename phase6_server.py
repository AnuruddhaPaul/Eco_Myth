"""
EcoMyth-VLM Phase 6 — Annotation Server
========================================
Run from your EcoMyth project root:

    python phase6_server.py

Then open: http://localhost:8080

What it does:
  - Serves all project files (images, JSON, HTML)
  - Auto-loads stories + ground truth from outputs/ folder
  - Saves annotations directly to outputs/phase6/ on disk
  - No manual file picking needed
"""

import json
import csv
import os
import threading
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import webbrowser

# ── Paths (relative to project root) ─────────────────────────
PROJECT_ROOT   = Path(__file__).parent
STORIES_FILE   = PROJECT_ROOT / "outputs" / "phase6" / "phase6_annotation_stories.json"
GT_FILE        = PROJECT_ROOT / "outputs" / "phase3" / "species_ground_truth.json"
ANNO_FILE      = PROJECT_ROOT / "outputs" / "phase6" / "phase6_annotations.csv"
TOOL_HTML      = PROJECT_ROOT / "EcoMyth_Phase6_AnnotationTool_v4.html"

PORT = 8080

ANNO_COLS = [
    "serial_number","manifest_id","scientific_name","common_name",
    "tier","model_key","format","tradition","temperature","response_idx","pool",
    "r_species","r_habitat","r_diet","r_iucn","r_overall","notes","saved_at",
]

# ── MIME types ────────────────────────────────────────────────
MIME = {
    ".html": "text/html",
    ".js":   "application/javascript",
    ".css":  "text/css",
    ".json": "application/json",
    ".csv":  "text/csv",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".gif":  "image/gif",
    ".webp": "image/webp",
    ".ico":  "image/x-icon",
}

class Handler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        # Suppress noisy access logs except errors
        if args and str(args[1]) not in ("200", "304"):
            print(f"  [{args[1]}] {args[0]}")

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, status=200, ctype="text/plain"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── GET handler ───────────────────────────────────────────
    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.lstrip("/")

        # ── API routes ────────────────────────────────────────

        # Root → serve the tool HTML
        if path in ("", "index.html"):
            if TOOL_HTML.exists():
                self._serve_file(TOOL_HTML)
            else:
                self.send_text("Tool HTML not found. Place EcoMyth_Phase6_AnnotationTool_v4.html in project root.", 404)
            return

        # /api/stories — load the 500 stories
        if path == "api/stories":
            if STORIES_FILE.exists():
                data = json.loads(STORIES_FILE.read_text(encoding="utf-8"))
                self.send_json({"ok": True, "stories": data, "count": len(data)})
            else:
                self.send_json({"ok": False,
                    "error": f"Stories file not found: {STORIES_FILE}\nRun select_phase6_stories_fixed.py first."}, 404)
            return

        # /api/groundtruth — load species ground truth
        if path == "api/groundtruth":
            if GT_FILE.exists():
                data = json.loads(GT_FILE.read_text(encoding="utf-8"))
                self.send_json({"ok": True, "groundtruth": data, "count": len(data)})
            else:
                self.send_json({"ok": False,
                    "error": f"Ground truth not found: {GT_FILE}"}, 404)
            return

        # /api/annotations — load existing saved annotations
        if path == "api/annotations":
            if ANNO_FILE.exists():
                annos = {}
                with open(ANNO_FILE, encoding="utf-8", newline="") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        annos[row["serial_number"]] = row
                self.send_json({"ok": True, "annotations": annos,
                                "count": len(annos)})
            else:
                self.send_json({"ok": True, "annotations": {}, "count": 0})
            return

        # /api/status — server status check
        if path == "api/status":
            self.send_json({
                "ok":           True,
                "stories_file": str(STORIES_FILE),
                "stories_exist":STORIES_FILE.exists(),
                "gt_file":      str(GT_FILE),
                "gt_exists":    GT_FILE.exists(),
                "anno_file":    str(ANNO_FILE),
                "anno_exist":   ANNO_FILE.exists(),
            })
            return

        # ── Static file serving ───────────────────────────────
        # Resolve path relative to project root (for images etc.)
        file_path = PROJECT_ROOT / path
        if file_path.exists() and file_path.is_file():
            self._serve_file(file_path)
        else:
            self.send_text(f"Not found: {path}", 404)

    def _serve_file(self, path: Path):
        suffix = path.suffix.lower()
        ctype  = MIME.get(suffix, "application/octet-stream")
        try:
            data = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", len(data))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            self.send_text(f"Error reading file: {e}", 500)

    # ── POST handler ──────────────────────────────────────────
    def do_POST(self):
        parsed = urlparse(self.path)
        path   = parsed.path.lstrip("/")

        length  = int(self.headers.get("Content-Length", 0))
        body    = self.rfile.read(length)

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception as e:
            self.send_json({"ok": False, "error": f"Bad JSON: {e}"}, 400)
            return

        # /api/save — save one annotation record
        if path == "api/save":
            try:
                anno = payload.get("annotation", {})
                if not anno.get("serial_number"):
                    self.send_json({"ok": False, "error": "Missing serial_number"}, 400)
                    return

                # Load existing annotations
                existing = {}
                if ANNO_FILE.exists():
                    with open(ANNO_FILE, encoding="utf-8", newline="") as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            existing[row["serial_number"]] = row

                # Update or insert
                existing[anno["serial_number"]] = {
                    col: anno.get(col, "") for col in ANNO_COLS
                }

                # Write back
                ANNO_FILE.parent.mkdir(parents=True, exist_ok=True)
                with open(ANNO_FILE, "w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=ANNO_COLS,
                                           extrasaction="ignore")
                    writer.writeheader()
                    writer.writerows(existing.values())

                self.send_json({
                    "ok":    True,
                    "saved": anno["serial_number"],
                    "total": len(existing),
                })

            except Exception as e:
                self.send_json({"ok": False, "error": str(e)}, 500)
            return

        self.send_json({"ok": False, "error": f"Unknown POST route: {path}"}, 404)


def main():
    print("=" * 56)
    print("  EcoMyth-VLM Phase 6 — Annotation Server")
    print("=" * 56)
    print()

    # Startup checks
    checks = [
        (TOOL_HTML,    "Annotation HTML",   True),
        (STORIES_FILE, "Stories JSON",      False),
        (GT_FILE,      "Ground truth JSON", False),
    ]
    all_ok = True
    for fpath, label, required in checks:
        exists = fpath.exists()
        icon   = "OK" if exists else ("MISSING (required)" if required else "MISSING")
        print(f"  {label:<25}: {icon}")
        print(f"    {fpath}")
        if required and not exists:
            all_ok = False

    if not all_ok:
        print()
        print("  ERROR: Required files missing. Fix above before retrying.")
        return

    if not STORIES_FILE.exists():
        print()
        print("  WARNING: Stories file not found.")
        print("  Run: python select_phase6_stories_fixed.py")

    print()

    # Annotations status
    if ANNO_FILE.exists():
        with open(ANNO_FILE, encoding="utf-8", newline="") as f:
            n = sum(1 for _ in csv.DictReader(f))
        print(f"  Existing annotations : {n} records (will resume)")
    else:
        print(f"  Annotations file     : new (starting fresh)")
        print(f"  Will save to         : {ANNO_FILE}")

    print()
    print(f"  Server starting on http://localhost:{PORT}")
    print(f"  Opening browser...")
    print()
    print("  Press Ctrl+C to stop")
    print("=" * 56)

    server = HTTPServer(("", PORT), Handler)

    # Open browser after short delay
    def open_browser():
        import time
        time.sleep(0.8)
        webbrowser.open(f"http://localhost:{PORT}")

    threading.Thread(target=open_browser, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n  Server stopped.")
        if ANNO_FILE.exists():
            with open(ANNO_FILE, encoding="utf-8", newline="") as f:
                n = sum(1 for _ in csv.DictReader(f))
            print(f"  Annotations saved: {n} records --> {ANNO_FILE}")
        print()


if __name__ == "__main__":
    main()
