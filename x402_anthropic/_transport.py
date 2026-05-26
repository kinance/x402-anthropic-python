"""httpx transport layers that intercept HTTP 402 and sign x402 payments."""

from __future__ import annotations

import httpx
from x402.http import x402HTTPClientSync, x402HTTPClient

from ._errors import X402PaymentError


class X402Transport(httpx.BaseTransport):
    def __init__(self, x402_client: x402HTTPClientSync, inner: httpx.BaseTransport) -> None:
        self._x402 = x402_client
        self._inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self._inner.handle_request(request)
        if response.status_code != 402:
            return response

        try:
            body = request.content
        except httpx.RequestNotRead:
            body = request.read()

        response.read()
        response.close()

        try:
            payment_headers, _ = self._x402.handle_402_response(
                dict(response.headers), response.content
            )
        except Exception as exc:
            raise X402PaymentError(f"Payment signing failed: {exc}") from exc

        merged = list(request.headers.items()) + list(payment_headers.items())
        retry = httpx.Request(
            request.method, request.url, headers=merged, content=body
        )
        return self._inner.handle_request(retry)

    def close(self) -> None:
        self._inner.close()


class AsyncX402Transport(httpx.AsyncBaseTransport):
    def __init__(self, x402_client: x402HTTPClient, inner: httpx.AsyncBaseTransport) -> None:
        self._x402 = x402_client
        self._inner = inner

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        response = await self._inner.handle_async_request(request)
        if response.status_code != 402:
            return response

        try:
            body = request.content
        except httpx.RequestNotRead:
            body = await request.aread()

        await response.aread()
        await response.aclose()

        try:
            payment_headers, _ = await self._x402.handle_402_response(
                dict(response.headers), response.content
            )
        except Exception as exc:
            raise X402PaymentError(f"Payment signing failed: {exc}") from exc

        merged = list(request.headers.items()) + list(payment_headers.items())
        retry = httpx.Request(
            request.method, request.url, headers=merged, content=body
        )
        return await self._inner.handle_async_request(retry)

    async def aclose(self) -> None:
        await self._inner.aclose()
