"""Basic synchronous usage example."""

import anthropic
from x402_anthropic import X402Anthropic, EVMWallet

wallet = EVMWallet(private_key="0x_YOUR_PRIVATE_KEY")
client = X402Anthropic(
    wallet=wallet,
    base_url="https://your-x402-gateway.example.com",
)

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude!"}],
)
print(message.content[0].text)
