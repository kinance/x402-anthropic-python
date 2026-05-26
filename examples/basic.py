"""Basic synchronous usage example."""

import os
from x402_anthropic import X402Anthropic, EVMWallet

wallet = EVMWallet(private_key=os.environ["EVM_PRIVATE_KEY"])
client = X402Anthropic(
    wallet=wallet,
    base_url=os.environ.get("X402_BASE_URL", "https://your-x402-gateway.example.com"),
)

message = client.messages.create(
    model="claude-opus-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello!"}],
)
print(message.content[0].text)
