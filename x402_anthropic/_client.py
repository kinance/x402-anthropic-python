"""x402-enabled Anthropic client wrappers."""

from __future__ import annotations

import asyncio
import httpx
import anthropic

from ._transport import X402Transport, AsyncX402Transport
from ._wallet import Wallet


class X402Anthropic(anthropic.Anthropic):
    """
    Anthropic client with transparent HTTP 402 payment handling.

    Usage::

        from x402_anthropic import X402Anthropic, EVMWallet

        wallet = EVMWallet(private_key="0x...")
        client = X402Anthropic(wallet=wallet, base_url="https://your-x402-gateway.com")
        msg = client.messages.create(model="claude-opus-4-5", max_tokens=1024, messages=[...])
    """

    def __init__(self, wallet: Wallet, policies: list | None = None, **kwargs: object) -> None:
        x402_http = wallet.build_sync(policies=policies)
        inner = httpx.HTTPTransport()
        transport = X402Transport(x402_http, inner)
        self._x402_http_client = httpx.Client(transport=transport)
        kwargs.setdefault("api_key", "x402")
        super().__init__(http_client=self._x402_http_client, **kwargs)

    def close(self) -> None:
        self._x402_http_client.close()
        super().close()

    def __enter__(self) -> "X402Anthropic":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


class _LazyAsyncX402Transport(httpx.AsyncBaseTransport):
    """Wraps AsyncX402Transport with deferred wallet initialization.

    x402 wallet registration may be async (e.g. SVM keypair fetch), so it
    cannot happen in __init__. This transport initializes the real x402 HTTP
    client on first request, then delegates all subsequent calls to it.
    """

    def __init__(self, wallet: Wallet, policies: list | None, inner: httpx.AsyncBaseTransport) -> None:
        self._wallet = wallet
        self._policies = policies
        self._inner = inner
        self._transport: AsyncX402Transport | None = None
        self._lock = asyncio.Lock()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if self._transport is None:
            async with self._lock:
                if self._transport is None:
                    x402_http = await self._wallet.build_async(policies=self._policies)
                    self._transport = AsyncX402Transport(x402_http, self._inner)
        return await self._transport.handle_async_request(request)

    async def aclose(self) -> None:
        await self._inner.aclose()


class AsyncX402Anthropic(anthropic.AsyncAnthropic):
    """
    Async Anthropic client with transparent HTTP 402 payment handling.

    The x402 transport is wired at construction time; wallet initialization is
    deferred to the first request (inside the event loop). Use as a context
    manager to ensure the underlying httpx client is properly closed::

        from x402_anthropic import AsyncX402Anthropic, EVMWallet
        import asyncio

        async def main():
            wallet = EVMWallet(private_key="0x...")
            async with AsyncX402Anthropic(
                wallet=wallet,
                base_url="https://your-x402-gateway.com",
            ) as client:
                msg = await client.messages.create(...)
                async with client.messages.stream(...) as stream:
                    async for text in stream.text_stream:
                        print(text, end="", flush=True)

        asyncio.run(main())
    """

    def __init__(self, wallet: Wallet, policies: list | None = None, **kwargs: object) -> None:
        inner = httpx.AsyncHTTPTransport()
        self._lazy_transport = _LazyAsyncX402Transport(wallet, policies, inner)
        self._x402_http_client = httpx.AsyncClient(transport=self._lazy_transport)
        kwargs.setdefault("api_key", "x402")
        super().__init__(http_client=self._x402_http_client, **kwargs)
