"""Streaming usage example."""

import asyncio
from x402_anthropic import AsyncX402Anthropic, EVMWallet


async def main() -> None:
    wallet = EVMWallet(private_key="0x_YOUR_PRIVATE_KEY")
    async with AsyncX402Anthropic(
        wallet=wallet,
        base_url="https://your-x402-gateway.example.com",
    ) as client:
        async with client.messages.stream(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Tell me a short story."}],
        ) as stream:
            async for text in stream.text_stream:
                print(text, end="", flush=True)
    print()


asyncio.run(main())
