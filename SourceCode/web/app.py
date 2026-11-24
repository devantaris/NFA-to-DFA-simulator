"""Lightweight, zero-dependency Web Server for Automata Theory Simulator.

Uses standard library http.server to provide an interactive browser dashboard
for viva presentations and visual demonstrations.
"""

from __future__ import annotations
import json
import mimetypes
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Any, Dict

from ..converter import NFAtoDFAConverter
from ..dfa import DFA
from ..minimizer import DFAMinimizer
from ..models import EPSILON
from ..nfa import NFA
from ..visualizer import Visualizer

STATIC_DIR = Path(__file__).parent / "static"
SAMPLES_DIR = Path(__file__).parent.parent.parent / "TestCases" / "definitions"


class AutomataRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        """Suppress noisy request logging."""
        pass

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._serve_file(STATIC_DIR / "index.html", "text/html")
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
            file_path = STATIC_DIR / rel
            mime, _ = mimetypes.guess_type(str(file_path))
            self._serve_file(file_path, mime or "application/octet-stream")
        elif path == "/api/samples":
            self._handle_samples()
        else:
            self.send_error(404, "Not Found")

    def do_POST(self) -> None:
        path = self.path.split("?")[0]
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            self._send_json({"error": "Malformed JSON payload"}, status=400)
            return

        try:
            if path == "/api/convert":
                self._handle_convert(data)
            elif path == "/api/simulate":
                self._handle_simulate(data)
            else:
                self.send_error(404, "Unknown API Endpoint")
        except Exception as e:
            self._send_json({"error": str(e)}, status=400)

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404, "File Not Found")
            return
        with open(file_path, "rb") as f:
            content = f.read()
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(self, obj: Any, status: int = 200) -> None:
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(payload)

    def _handle_samples(self) -> None:
        samples = []
        if SAMPLES_DIR.exists():
            for f in sorted(SAMPLES_DIR.glob("*.json")):
                try:
                    with open(f, "r", encoding="utf-8") as s_file:
                        samples.append(json.load(s_file))
                except Exception:
                    pass
        self._send_json({"samples": samples})

    def _handle_convert(self, data: Dict[str, Any]) -> None:
        nfa_dict = data.get("nfa")
        if not nfa_dict:
            self._send_json({"error": "Missing 'nfa' object in request"}, status=400)
            return

        nfa = NFA.from_dict(nfa_dict)
        conv = NFAtoDFAConverter(nfa).convert()
        minimizer = DFAMinimizer(conv.dfa)
        min_res = minimizer.minimize()

        response = {
            "nfa": nfa.to_dict(),
            "nfa_dot": Visualizer.to_dot(nfa, "Original NFA"),
            "nfa_table": Visualizer.nfa_transition_table(nfa),
            "conversion_steps": [s.to_dict() for s in conv.steps],
            "state_mapping": conv.state_mapping,
            "epsilon_closures": conv.epsilon_closures,
            "converted_dfa": conv.dfa.to_dict(),
            "converted_dfa_dot": Visualizer.to_dot(conv.dfa, "Converted DFA"),
            "converted_dfa_table": Visualizer.dfa_transition_table(conv.dfa),
            "minimal_dfa": min_res.minimal_dfa.to_dict(),
            "minimal_dfa_dot": Visualizer.to_dot(min_res.minimal_dfa, "Minimal DFA"),
            "minimal_dfa_table": Visualizer.dfa_transition_table(min_res.minimal_dfa),
            "distinguishable_table": min_res.distinguishable_table,
            "min_state_mapping": min_res.state_mapping,
            "unreachable_states": sorted(list(min_res.unreachable_states)),
        }
        self._send_json(response)

    def _handle_simulate(self, data: Dict[str, Any]) -> None:
        nfa_dict = data.get("nfa")
        input_string = data.get("input_string", "")

        nfa = NFA.from_dict(nfa_dict)
        conv = NFAtoDFAConverter(nfa).convert()
        min_res = DFAMinimizer(conv.dfa).minimize()

        nfa_sim = nfa.simulate(input_string)
        converted_dfa_sim = conv.dfa.simulate(input_string)
        minimal_dfa_sim = min_res.minimal_dfa.simulate(input_string)

        self._send_json({
            "input_string": input_string,
            "nfa_simulation": nfa_sim.to_dict(),
            "converted_dfa_simulation": converted_dfa_sim.to_dict(),
            "minimal_dfa_simulation": minimal_dfa_sim.to_dict(),
            "is_equivalent": (nfa_sim.accepted == minimal_dfa_sim.accepted),
        })


def run_web_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    server_address = (host, port)
    httpd = HTTPServer(server_address, AutomataRequestHandler)
    print(f"\n========================================================================")
    print(f" CSET302 Automata Theory Simulator Web Interface is running!")
    print(f" Access in your browser: http://{host}:{port}")
    print(f" Press Ctrl+C to terminate.")
    print(f"========================================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server.")
        httpd.server_close()
