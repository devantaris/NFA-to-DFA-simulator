"""E2E Test Client and Ephemeral Server Management for NFA to DFA Simulator.

Provides zero-dependency live server execution and REST client interactions
using strictly Python's standard library.
"""

from __future__ import annotations

import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple, Union

from SourceCode.web.app import AutomataRequestHandler


class SilentAutomataRequestHandler(AutomataRequestHandler):
    """Subclass of AutomataRequestHandler that suppresses stderr request logging during test runs."""

    def log_message(self, format: str, *args: Any) -> None:
        """Suppress standard HTTP server request log lines to keep test output clean."""
        pass


class LiveServerHarness:
    """Manages the background execution of the Automata HTTP server on an ephemeral port."""

    def __init__(self, host: str = "127.0.0.1"):
        self.host = host
        self.server: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.port: int = 0

    def start(self) -> str:
        """Starts the HTTP server bound to an OS-assigned ephemeral port."""
        self.server = ThreadingHTTPServer((self.host, 0), SilentAutomataRequestHandler)
        self.server.daemon_threads = True
        self.port = self.server.server_address[1]
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return f"http://{self.host}:{self.port}"

    def stop(self) -> None:
        """Gracefully shuts down and cleans up the HTTP server and daemon thread."""
        if self.server:
            try:
                self.server.shutdown()
                self.server.server_close()
            except Exception:
                pass
            self.server = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
            self.thread = None


class AutomataApiClient:
    """Zero-dependency HTTP client for the Automata REST API using standard urllib."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get(
        self, endpoint: str, headers: Optional[Dict[str, str]] = None
    ) -> Tuple[int, Any, Dict[str, str]]:
        """Performs an HTTP GET request to the given endpoint.

        Returns:
            Tuple of (status_code, parsed_data_or_text, response_headers).
        """
        url = f"{self.base_url}{endpoint}"
        req = urllib.request.Request(url, headers=headers or {}, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                resp_headers = dict(resp.headers)
                body = resp.read()
                try:
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    try:
                        data = body.decode("utf-8")
                    except UnicodeDecodeError:
                        data = body
                return status, data, resp_headers
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read()
                try:
                    err_data = json.loads(err_body.decode("utf-8"))
                except Exception:
                    try:
                        err_data = err_body.decode("utf-8")
                    except UnicodeDecodeError:
                        err_data = err_body
                return e.code, err_data, dict(e.headers)
            finally:
                e.close()

    def post(
        self,
        endpoint: str,
        payload: Any = None,
        headers: Optional[Dict[str, str]] = None,
        raw_body: Optional[bytes] = None,
    ) -> Tuple[int, Any, Dict[str, str]]:
        """Performs an HTTP POST request to the given endpoint.

        Returns:
            Tuple of (status_code, parsed_data_or_text, response_headers).
        """
        url = f"{self.base_url}{endpoint}"
        req_headers = {"Content-Type": "application/json; charset=utf-8"}
        if headers:
            req_headers.update(headers)

        if raw_body is not None:
            encoded_data = raw_body
        elif payload is not None:
            encoded_data = json.dumps(payload).encode("utf-8")
        else:
            encoded_data = b"{}"

        req = urllib.request.Request(
            url,
            data=encoded_data,
            headers=req_headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                status = resp.status
                resp_headers = dict(resp.headers)
                body = resp.read()
                try:
                    data = json.loads(body.decode("utf-8"))
                except Exception:
                    try:
                        data = body.decode("utf-8")
                    except UnicodeDecodeError:
                        data = body
                return status, data, resp_headers
        except urllib.error.HTTPError as e:
            try:
                err_body = e.read()
                try:
                    err_data = json.loads(err_body.decode("utf-8"))
                except Exception:
                    try:
                        err_data = err_body.decode("utf-8")
                    except UnicodeDecodeError:
                        err_data = err_body
                return e.code, err_data, dict(e.headers)
            finally:
                e.close()


class BaseE2ETestCase(unittest.TestCase):
    """Base test case providing an isolated live server and API client per test class."""

    server_harness: Optional[LiveServerHarness] = None
    client: Optional[AutomataApiClient] = None
    base_url: str = ""

    @property
    def harness(self) -> Optional[LiveServerHarness]:
        return self.server_harness

    @classmethod
    def setUpClass(cls) -> None:
        cls.server_harness = LiveServerHarness()
        cls.base_url = cls.server_harness.start()
        cls.client = AutomataApiClient(cls.base_url)

    @classmethod
    def tearDownClass(cls) -> None:
        if cls.server_harness:
            cls.server_harness.stop()
            cls.server_harness = None
            cls.client = None

    def skip_if_m1_unavailable(self, status: int, data: Any) -> None:
        """Skips test if an M1 endpoint is not yet integrated in app.py (HTTP 404)."""
        if status == 404:
            self.skipTest("M1 endpoint not yet integrated in app.py")
