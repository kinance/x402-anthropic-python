"""Unit tests for X402Transport and AsyncX402Transport."""

from __future__ import annotations

import asyncio
import pytest
import httpx

from unittest.mock import MagicMock, AsyncMock


def make_402_response() -> httpx.Response:
    return httpx.Response(402, headers={"x-payment-required": "true"}, content=b"payment required")


def make_200_response() -> httpx.Response:
    return httpx.Response(200, json={"ok": True})


# ---------------------------------------------------------------------------
# Sync transport
# ---------------------------------------------------------------------------

class TestX402Transport:
    def _make_transport(self, payment_headers: dict):
        from x402_anthropic._transport import X402Transport

        x402_mock = MagicMock()
        x402_mock.handle_402_response.return_value = (payment_headers, {})

        inner_mock = MagicMock(spec=httpx.BaseTransport)
        inner_mock.handle_request.side_effect = [make_402_response(), make_200_response()]

        return X402Transport(x402_mock, inner_mock), x402_mock, inner_mock

    def test_passthrough_non_402(self):
        from x402_anthropic._transport import X402Transport

        inner = MagicMock(spec=httpx.BaseTransport)
        inner.handle_request.return_value = make_200_response()
        transport = X402Transport(MagicMock(), inner)

        resp = transport.handle_request(httpx.Request("GET", "https://example.com"))
        assert resp.status_code == 200
        assert inner.handle_request.call_count == 1

    def test_retries_on_402(self):
        transport, x402_mock, inner_mock = self._make_transport({"x-payment": "signed"})

        resp = transport.handle_request(httpx.Request("POST", "https://example.com", content=b"body"))
        assert resp.status_code == 200
        assert inner_mock.handle_request.call_count == 2
        x402_mock.handle_402_response.assert_called_once()

    def test_retry_includes_payment_headers(self):
        transport, _, inner_mock = self._make_transport({"x-payment": "abc123"})

        transport.handle_request(httpx.Request("POST", "https://example.com", content=b"body"))
        retry_req = inner_mock.handle_request.call_args_list[1][0][0]
        assert retry_req.headers.get("x-payment") == "abc123"

    def test_original_headers_preserved_on_retry(self):
        transport, _, inner_mock = self._make_transport({"x-payment": "signed"})

        req = httpx.Request("POST", "https://example.com", headers={"authorization": "Bearer tok"}, content=b"body")
        transport.handle_request(req)
        retry_req = inner_mock.handle_request.call_args_list[1][0][0]
        assert retry_req.headers.get("authorization") == "Bearer tok"

    def test_single_retry_only_returns_second_402_to_caller(self):
        """Transport retries exactly once; a second 402 is returned as-is."""
        from x402_anthropic._transport import X402Transport

        x402_mock = MagicMock()
        x402_mock.handle_402_response.return_value = ({"x-payment": "p"}, {})

        inner_mock = MagicMock(spec=httpx.BaseTransport)
        inner_mock.handle_request.side_effect = [make_402_response(), make_402_response()]
        transport = X402Transport(x402_mock, inner_mock)

        resp = transport.handle_request(httpx.Request("POST", "https://example.com", content=b"body"))
        assert resp.status_code == 402
        assert inner_mock.handle_request.call_count == 2

    def test_body_replayed_on_retry(self):
        transport, _, inner_mock = self._make_transport({"x-payment": "p"})

        transport.handle_request(httpx.Request("POST", "https://example.com", content=b"original-body"))
        retry_req = inner_mock.handle_request.call_args_list[1][0][0]
        assert retry_req.content == b"original-body"

    def test_close_delegates_to_inner(self):
        from x402_anthropic._transport import X402Transport

        inner = MagicMock(spec=httpx.BaseTransport)
        transport = X402Transport(MagicMock(), inner)
        transport.close()
        inner.close.assert_called_once()

    def test_raises_x402_payment_error_on_signing_failure(self):
        from x402_anthropic._transport import X402Transport
        from x402_anthropic._errors import X402PaymentError

        x402_mock = MagicMock()
        x402_mock.handle_402_response.side_effect = RuntimeError("key not found")

        inner_mock = MagicMock(spec=httpx.BaseTransport)
        inner_mock.handle_request.return_value = make_402_response()
        transport = X402Transport(x402_mock, inner_mock)

        with pytest.raises(X402PaymentError) as exc_info:
            transport.handle_request(httpx.Request("POST", "https://example.com", content=b"body"))
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "key not found" in str(exc_info.value.__cause__)


# ---------------------------------------------------------------------------
# Async transport
# ---------------------------------------------------------------------------

class TestAsyncX402Transport:
    def _make_transport(self, payment_headers: dict):
        from x402_anthropic._transport import AsyncX402Transport

        x402_mock = MagicMock()
        x402_mock.handle_402_response = AsyncMock(return_value=(payment_headers, {}))

        inner_mock = MagicMock(spec=httpx.AsyncBaseTransport)
        inner_mock.handle_async_request = AsyncMock(
            side_effect=[make_402_response(), make_200_response()]
        )

        return AsyncX402Transport(x402_mock, inner_mock), x402_mock, inner_mock

    def test_passthrough_non_402(self):
        from x402_anthropic._transport import AsyncX402Transport

        inner = MagicMock(spec=httpx.AsyncBaseTransport)
        inner.handle_async_request = AsyncMock(return_value=make_200_response())
        transport = AsyncX402Transport(MagicMock(), inner)

        resp = asyncio.run(
            transport.handle_async_request(httpx.Request("GET", "https://example.com"))
        )
        assert resp.status_code == 200
        assert inner.handle_async_request.call_count == 1

    def test_retries_on_402(self):
        transport, x402_mock, inner_mock = self._make_transport({"x-payment": "signed"})

        resp = asyncio.run(
            transport.handle_async_request(httpx.Request("POST", "https://example.com", content=b"body"))
        )
        assert resp.status_code == 200
        assert inner_mock.handle_async_request.call_count == 2
        x402_mock.handle_402_response.assert_awaited_once()

    def test_retry_includes_payment_headers(self):
        transport, _, inner_mock = self._make_transport({"x-payment": "abc123"})

        asyncio.run(
            transport.handle_async_request(httpx.Request("POST", "https://example.com", content=b"body"))
        )
        retry_req = inner_mock.handle_async_request.call_args_list[1][0][0]
        assert retry_req.headers.get("x-payment") == "abc123"

    def test_single_retry_only_returns_second_402_to_caller(self):
        from x402_anthropic._transport import AsyncX402Transport

        x402_mock = MagicMock()
        x402_mock.handle_402_response = AsyncMock(return_value=({"x-payment": "p"}, {}))

        inner_mock = MagicMock(spec=httpx.AsyncBaseTransport)
        inner_mock.handle_async_request = AsyncMock(
            side_effect=[make_402_response(), make_402_response()]
        )
        transport = AsyncX402Transport(x402_mock, inner_mock)

        resp = asyncio.run(
            transport.handle_async_request(httpx.Request("POST", "https://example.com", content=b"body"))
        )
        assert resp.status_code == 402
        assert inner_mock.handle_async_request.call_count == 2

    def test_raises_x402_payment_error_on_signing_failure(self):
        from x402_anthropic._transport import AsyncX402Transport
        from x402_anthropic._errors import X402PaymentError

        x402_mock = MagicMock()
        x402_mock.handle_402_response = AsyncMock(side_effect=RuntimeError("bad signer"))

        inner_mock = MagicMock(spec=httpx.AsyncBaseTransport)
        inner_mock.handle_async_request = AsyncMock(return_value=make_402_response())
        transport = AsyncX402Transport(x402_mock, inner_mock)

        async def run():
            return await transport.handle_async_request(
                httpx.Request("POST", "https://example.com", content=b"body")
            )

        with pytest.raises(X402PaymentError) as exc_info:
            asyncio.run(run())
        assert isinstance(exc_info.value.__cause__, RuntimeError)
        assert "bad signer" in str(exc_info.value.__cause__)


# ---------------------------------------------------------------------------
# Wallet registration
# ---------------------------------------------------------------------------

def _v2_networks(schemes_by_version: dict) -> set[str]:
    """Extract V2 network IDs from get_registered_schemes() return value."""
    return {entry["network"] for entry in schemes_by_version.get(2, [])}


class TestEVMWallet:
    def test_register_sync_registers_eip155_wildcard(self):
        from x402_anthropic._wallet import EVMWallet
        from x402 import x402ClientSync

        wallet = EVMWallet("0x" + "aa" * 32)
        client = x402ClientSync()
        wallet.register_sync(client)
        assert "eip155:*" in _v2_networks(client.get_registered_schemes())

    def test_network_restriction(self):
        from x402_anthropic._wallet import EVMWallet
        from x402 import x402ClientSync

        wallet = EVMWallet("0x" + "bb" * 32, networks=["eip155:8453"])
        client = x402ClientSync()
        wallet.register_sync(client)
        v2 = _v2_networks(client.get_registered_schemes())
        assert "eip155:8453" in v2
        assert "eip155:*" not in v2
