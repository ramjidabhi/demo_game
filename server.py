"""
Backend Web Server for the Game Application.
Serves static frontend files and exposes a RESTful JSON API
backed by SQLite database.
Multi-threaded, robust against browser socket disconnections,
and requires zero external dependencies.
"""

from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import os
import sys
import urllib.parse
from typing import Any
import database

PORT = int(os.environ.get("PORT", 8000))
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# Enable UTF-8 for console output on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

class GameRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler supporting API endpoints and static file serving."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=STATIC_DIR, **kwargs)

    def _set_headers(self, status_code: int = 200, content_type: str = "application/json"):
        self.send_response(status_code)
        self.send_header("Content-Type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self._set_headers(204)

    def _send_json(self, data: Any, status_code: int = 200):
        try:
            payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self._set_headers(status_code, "application/json; charset=utf-8")
            self.wfile.write(payload)
        except (ConnectionResetError, BrokenPipeError):
            pass

    def _send_error(self, message: str, status_code: int = 400):
        self._send_json({"error": message, "success": False}, status_code)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query_params = urllib.parse.parse_qs(parsed.query)

        # Health check endpoint for Kubernetes liveness & readiness probes
        if path in ("/health", "/healthz"):
            self._send_json({"status": "healthy", "service": "cyber-viper"}, 200)
            return

        # Handle favicon request cleanly
        if path in ("/favicon.ico", "/favicon.svg"):
            icon_path = os.path.join(STATIC_DIR, "favicon.svg")
            if os.path.exists(icon_path):
                try:
                    with open(icon_path, "rb") as f:
                        data = f.read()
                    self._set_headers(200, "image/svg+xml")
                    self.wfile.write(data)
                except Exception:
                    self._set_headers(204)
            else:
                self._set_headers(204)
            return

        # API: Get game history
        if path == "/api/history":
            try:
                limit = int(query_params.get("limit", [50])[0])
                mode = query_params.get("mode", [None])[0]
                history = database.get_history(limit=limit, mode=mode)
                self._send_json({"success": True, "history": history})
            except Exception as e:
                self._send_error(str(e), 500)
            return

        # API: Get leaderboard
        if path == "/api/leaderboard":
            try:
                limit = int(query_params.get("limit", [10])[0])
                leaderboard = database.get_leaderboard(limit=limit)
                self._send_json({"success": True, "leaderboard": leaderboard})
            except Exception as e:
                self._send_error(str(e), 500)
            return

        # API: Get aggregate statistics
        if path == "/api/stats":
            try:
                stats = database.get_stats()
                self._send_json({"success": True, "stats": stats})
            except Exception as e:
                self._send_error(str(e), 500)
            return

        # Fallback to serving static files (index.html, style.css, app.js, etc.)
        try:
            super().do_GET()
        except (ConnectionResetError, BrokenPipeError):
            pass

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # Read JSON body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else ""

        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            self._send_error("Invalid JSON format", 400)
            return

        # API: Record new game result
        if path == "/api/history":
            try:
                player_name = data.get("player_name", "Player 1")
                game_mode = data.get("game_mode", "Classic")
                difficulty = data.get("difficulty", "Normal")
                score = int(data.get("score", 0))
                apples_eaten = int(data.get("apples_eaten", 0))
                duration_seconds = float(data.get("duration_seconds", 0.0))
                result = data.get("result", "Game Over")

                record = database.insert_game(
                    player_name=player_name,
                    game_mode=game_mode,
                    difficulty=difficulty,
                    score=score,
                    apples_eaten=apples_eaten,
                    duration_seconds=duration_seconds,
                    result=result
                )
                self._send_json({"success": True, "record": record}, 201)
            except Exception as e:
                self._send_error(str(e), 500)
            return

        # API: Clear match history
        if path == "/api/clear":
            try:
                database.clear_history()
                self._send_json({"success": True, "message": "History cleared successfully"})
            except Exception as e:
                self._send_error(str(e), 500)
            return

        self._send_error("Endpoint not found", 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/history":
            try:
                database.clear_history()
                self._send_json({"success": True, "message": "History cleared successfully"})
            except Exception as e:
                self._send_error(str(e), 500)
            return
        self._send_error("Endpoint not found", 404)

    def log_message(self, format, *args):
        # Suppress verbose favicon logging
        if len(args) > 0 and "favicon" in str(args[0]):
            return
        super().log_message(format, *args)

class RobustServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def handle_error(self, request, client_address):
        # Suppress socket reset / disconnect exceptions when browser closes
        exc_type, exc_val, _ = sys.exc_info()
        if exc_type in (ConnectionResetError, BrokenPipeError):
            return
        super().handle_error(request, client_address)

def run_server(port: int = PORT):
    database.init_db()
    
    server_address = ("", port)
    try:
        httpd = RobustServer(server_address, GameRequestHandler)
    except OSError as e:
        print(f"[ERROR] Port {port} could not be bound: {e}")
        print(f"[HINT] Trying fallback port {port + 1}...")
        httpd = RobustServer(("", port + 1), GameRequestHandler)
        port = port + 1

    print("=" * 65)
    print(f" [CYBER VIPER] Server is RUNNING at: http://localhost:{port}")
    print(f" [DATABASE] SQLite ready at: {database.DB_FILE}")
    print("=" * 65)
    print(" > Keep this window OPEN while playing the game.")
    print(" > To stop the server, press Ctrl+C in this window.")
    print("=" * 65)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down gracefully...")
        httpd.shutdown()
        httpd.server_close()

if __name__ == "__main__":
    run_server()
