# x402-anthropic-python

![PyPI](https://img.shields.io/pypi/v/x402-anthropic)
![Python](https://img.shields.io/pypi/pyversions/x402-anthropic)
![License](https://img.shields.io/pypi/l/x402-anthropic)

x402 payment transport for the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python).

Server returns 402 → client signs a USDC authorization → retries with payment header. Your code doesn't change. Follows the pattern introduced by [qntx/x402-openai-python](https://github.com/qntx/x402-openai-python).

## Install

```bash
pip install "x402-anthropic[evm]"   # EVM (Base, Ethereum)
pip install "x402-anthropic[svm]"   # SVM (Solana)
```

## Usage

```python
from x402_anthropic import X402Anthropic, EVMWallet

wallet = EVMWallet(private_key="0x...")
client = X402Anthropic(wallet=wallet, base_url="https://your-x402-gateway.example.com")

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude!"}],
)
print(message.content[0].text)
```

Async + streaming:

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

## Policy configuration

```python
from x402 import preferNetwork, maxAmount

client = X402Anthropic(
    wallet=wallet,
    policies=[preferNetwork("eip155:8453"), maxAmount(1_000_000)],  # Base, max $1 USDC
    base_url="...",
)
```

## Related

- [qntx/x402-openai-python](https://github.com/qntx/x402-openai-python) — OpenAI SDK equivalent
- [coinbase/x402](https://github.com/coinbase/x402) — x402 protocol spec and reference implementation
- [@x402/fetch](https://www.npmjs.com/package/@x402/fetch) — TypeScript equivalent

## License

MIT
