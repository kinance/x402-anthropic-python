"""End-to-end tests: X402Anthropic client against a local x402 test server.

The server returns HTTP 402 on /hello without payment, 200 with payment.
The mock facilitator auto-approves all signatures — no blockchain calls.
"""

from __future__ import annotations

import httpx
import pytest

from x402_anthropic import X402Anthropic, EVMWallet
from .server import X402TestServer

# A throwaway key — mock facilitator never verifies the actual signature
TEST_PRIVATE_KEY = "0x" + "aa" * 32


@pytest.fixture(scope="module")
def server():
    with X402TestServer() as s:
        yield s


@pytest.fixture(scope="module")
def client(server):
    wallet = EVMWallet(TEST_PRIVATE_KEY)
    return X402Anthropic(wallet=wallet, base_url=server.url)


class TestE2E:
    def test_server_returns_402_without_payment(self, server):
        """Baseline: raw httpx request with no payment header gets 402."""
        resp = httpx.get(f"{server.url}/hello")
        assert resp.status_code == 402

    def test_client_transparently_pays_and_gets_200(self, client, server):
        """Core: X402Anthropic intercepts 402, signs, retries, returns 200."""
        resp = client._client.get(f"{server.url}/hello")
        assert resp.status_code == 200
        assert resp.json()["message"] == "hello, paid caller"

    def test_client_makes_exactly_two_requests(self, server):
        """Transport makes exactly 2 inner requests: the 402 and the paid retry."""
        from x402_anthropic._transport import X402Transport

        sent_requests: list[httpx.Request] = []

        class CapturingTransport(httpx.BaseTransport):
            def __init__(self, inner):
                self._inner = inner

            def handle_request(self, req):
                sent_requests.append(req)
                return self._inner.handle_request(req)

        wallet = EVMWallet(TEST_PRIVATE_KEY)
        x402_http = wallet.build_sync()
        transport = X402Transport(x402_http, CapturingTransport(httpx.HTTPTransport()))
        httpx.Client(transport=transport).get(f"{server.url}/hello")

        assert len(sent_requests) == 2

    def test_404_path_passes_through_untouched(self, client, server):
        """Non-existent path returns 404 without triggering payment logic."""
        resp = client._client.get(f"{server.url}/nonexistent")
        assert resp.status_code == 404

    def test_payment_signature_header_present_on_retry(self, server):
        """The retry request carries the PAYMENT-SIGNATURE header.

        Verified by wrapping the inner httpx transport to capture outgoing requests.
        """
        from x402.http.constants import PAYMENT_SIGNATURE_HEADER
        from x402_anthropic._transport import X402Transport
        import httpx

        sent_requests: list[httpx.Request] = []

        class CapturingTransport(httpx.BaseTransport):
            def __init__(self, inner):
                self._inner = inner

            def handle_request(self, req):
                sent_requests.append(req)
                return self._inner.handle_request(req)

        wallet = EVMWallet(TEST_PRIVATE_KEY)
        x402_http = wallet.build_sync()
        inner = CapturingTransport(httpx.HTTPTransport())
        transport = X402Transport(x402_http, inner)
        http_client = httpx.Client(transport=transport)

        http_client.get(f"{server.url}/hello")

        assert len(sent_requests) == 2, f"Expected 2 requests, got {len(sent_requests)}"
        retry_req = sent_requests[1]
        assert PAYMENT_SIGNATURE_HEADER.lower() in {k.lower() for k in retry_req.headers}, (
            f"PAYMENT-SIGNATURE missing from retry headers: {dict(retry_req.headers)}"
        )
