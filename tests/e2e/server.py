"""Minimal stdlib HTTP server that gates /hello behind x402 payment.

No FastAPI, no external deps beyond what's already in the venv.
The mock facilitator auto-approves all payments — no blockchain calls.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from x402 import ResourceConfig, x402ResourceServerSync
from x402.http.constants import PAYMENT_REQUIRED_HEADER, PAYMENT_SIGNATURE_HEADER
from x402.http.utils import encode_payment_required_header
from x402.mechanisms.evm.exact.register import register_exact_evm_server

from .mock_facilitator import MockFacilitatorClient

# Recipient address — any valid EVM address works for testing
PAY_TO = "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd"
NETWORK = "eip155:8453"
PRICE = "0.001"  # $0.001 USDC


def _build_server() -> x402ResourceServerSync:
    facilitator = MockFacilitatorClient()
    server = x402ResourceServerSync(facilitator_clients=[facilitator])
    register_exact_evm_server(server)
    server.initialize()
    return server


_resource_server = _build_server()

_RESOURCE_CONFIG = ResourceConfig(
    scheme="exact",
    pay_to=PAY_TO,
    price=PRICE,
    network=NETWORK,
)


class X402Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress noisy access logs in tests

    def do_GET(self):
        if self.path != "/hello":
            self._send(404, {"error": "not found"})
            return

        payment_header = self.headers.get(PAYMENT_SIGNATURE_HEADER)

        if not payment_header:
            # No payment — build and send 402
            requirements = _resource_server.build_payment_requirements(_RESOURCE_CONFIG)
            payment_required = _resource_server.create_payment_required_response(requirements)
            encoded = encode_payment_required_header(payment_required)
            self._send(402, {"error": "payment required"}, {PAYMENT_REQUIRED_HEADER: encoded})
            return

        # Payment header present — verify via mock facilitator (always approves)
        self._send(200, {"message": "hello, paid caller"})

    def _send(self, status: int, body: dict, extra_headers: dict | None = None):
        payload = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        for k, v in (extra_headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(payload)


class X402TestServer:
    """Context manager that starts the test server in a background thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self._httpd = HTTPServer((host, port), X402Handler)
        self.port = self._httpd.server_address[1]  # actual port (0 → OS-assigned)
        self.url = f"http://{host}:{self.port}"
        self._thread: threading.Thread | None = None

    def start(self) -> "X402TestServer":
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._httpd.shutdown()

    def __enter__(self) -> "X402TestServer":
        return self.start()

    def __exit__(self, *_):
        self.stop()
