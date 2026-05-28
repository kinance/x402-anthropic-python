# x402-anthropic-python

[![PyPI](https://img.shields.io/pypi/v/x402-anthropic)](https://pypi.org/project/x402-anthropic/)
[![Python](https://img.shields.io/pypi/pyversions/x402-anthropic)](https://pypi.org/project/x402-anthropic/)
[![License](https://img.shields.io/pypi/l/x402-anthropic)](https://github.com/kinance/x402-anthropic-python/blob/main/LICENSE)
[![CI](https://github.com/kinance/x402-anthropic-python/actions/workflows/python.yml/badge.svg)](https://github.com/kinance/x402-anthropic-python/actions)

x402 payment transport for the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python).

Wrap the standard `anthropic.Anthropic` client with a crypto wallet. When the server responds with **HTTP 402**, the library automatically signs a USDC payment and retries — zero code changes needed. Follows the pattern introduced by [qntx/x402-openai-python](https://github.com/qntx/x402-openai-python).

## Install

```bash
pip install "x402-anthropic[evm]"   # EVM (Base, Ethereum)
pip install "x402-anthropic[svm]"   # SVM (Solana)
pip install "x402-anthropic[all]"   # all chains
```

## Quick start

```python
from x402_anthropic import X402Anthropic, EVMWallet

wallet = EVMWallet(private_key="0x...")
client = X402Anthropic(wallet=wallet, base_url="https://your-x402-gateway.example.com")

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}],
)
print(message.content[0].text)
```

Swap `EVMWallet` for `SVMWallet` to pay on Solana — the API is identical.

## Usage

### Async + streaming

```python
from x402_anthropic import AsyncX402Anthropic, EVMWallet
import asyncio

async def main():
    wallet = EVMWallet(private_key="0x...")
    async with AsyncX402Anthropic(wallet=wallet, base_url="...") as client:
        async with client.messages.stream(...) as stream:
            async for text in stream.text_stream:
                print(text, end="", flush=True)

asyncio.run(main())
```

### Payment policies

```python
from x402 import prefer_network, max_amount

client = X402Anthropic(
    wallet=wallet,
    policies=[prefer_network("eip155:8453"), max_amount(1_000_000)],  # Base, max $1 USDC
    base_url="...",
)
```

> **Safety**: use a dedicated wallet with limited funds and always set a `max_amount` policy before pointing this at an untrusted gateway.

## API reference

### `X402Anthropic` / `AsyncX402Anthropic`

Drop-in replacement for `anthropic.Anthropic` / `anthropic.AsyncAnthropic`.

| Parameter | Type | Description |
| :-- | :-- | :-- |
| `wallet` | `Wallet` | Wallet adapter for signing payments |
| `policies` | `list[Policy]` | Payment policies (chain preference, amount cap) |
| `base_url` | `str` | Gateway URL (required — points at your x402 server) |

All standard Anthropic kwargs (`timeout`, `max_retries`, `api_key`, …) are forwarded.

### Wallet adapters

| Class | Chain | Extra |
| :-- | :-- | :-- |
| `EVMWallet(private_key=…)` | Base, Ethereum, any EVM | `x402-anthropic[evm]` |
| `SVMWallet(private_key=…)` | Solana | `x402-anthropic[svm]` |

Implement the `Wallet` base class to add a new chain.

### Low-level transports

`X402Transport` / `AsyncX402Transport` — httpx transports for manual wiring:

```python
import httpx
from x402_anthropic._transport import X402Transport

x402_http = wallet.build_sync()
transport = X402Transport(x402_http, httpx.HTTPTransport())
client = httpx.Client(transport=transport)
```

## Examples

```bash
EVM_PRIVATE_KEY="0x..."        python examples/basic.py
EVM_PRIVATE_KEY="0x..."        python examples/streaming.py
```

## Related

- [qntx/x402-openai-python](https://github.com/qntx/x402-openai-python) — OpenAI SDK equivalent
- [coinbase/x402](https://github.com/coinbase/x402) — x402 protocol spec and reference implementation
- [@x402/fetch](https://www.npmjs.com/package/@x402/fetch) — TypeScript equivalent

## License

MIT
