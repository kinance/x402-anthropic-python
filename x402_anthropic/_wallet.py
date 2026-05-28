"""Wallet helpers for x402 payment signing — wraps x402 2.x mechanism registration."""

from __future__ import annotations

from x402 import x402ClientSync, x402Client
from x402.http import x402HTTPClientSync, x402HTTPClient


class Wallet:
    """Base wallet — subclass for EVM or SVM."""

    def register_sync(self, client: x402ClientSync) -> None:
        raise NotImplementedError

    async def register_async(self, client: x402Client) -> None:
        raise NotImplementedError

    def build_sync(self, policies: list | None = None) -> x402HTTPClientSync:
        c = x402ClientSync()
        self.register_sync(c)
        for policy in (policies or []):
            c.register_policy(policy)
        return x402HTTPClientSync(c)

    async def build_async(self, policies: list | None = None) -> x402HTTPClient:
        c = x402Client()
        await self.register_async(c)
        for policy in (policies or []):
            c.register_policy(policy)
        return x402HTTPClient(c)


class EVMWallet(Wallet):
    """EVM (Base/Ethereum) wallet using an eth_account private key.

    Args:
        private_key: Hex private key string (e.g. "0x...").
        networks: Optional list of CAIP-2 network IDs to restrict registration
            (default: wildcard "eip155:*" covering all EVM chains).
    """

    def __init__(self, private_key: str, networks: list[str] | None = None) -> None:
        self._private_key = private_key
        self._networks = networks

    def __repr__(self) -> str:
        return f"EVMWallet(address={self._make_signer().address!r}, networks={self._networks!r})"

    def _make_signer(self):
        from eth_account import Account
        from x402.mechanisms.evm.signers import EthAccountSigner
        return EthAccountSigner(Account.from_key(self._private_key))

    def register_sync(self, client: x402ClientSync) -> None:
        from x402.mechanisms.evm.exact.register import register_exact_evm_client
        register_exact_evm_client(client, self._make_signer(), networks=self._networks)

    async def register_async(self, client: x402Client) -> None:
        from x402.mechanisms.evm.exact.register import register_exact_evm_client
        register_exact_evm_client(client, self._make_signer(), networks=self._networks)


class SVMWallet(Wallet):
    """Solana wallet using a base58-encoded private key.

    Requires: pip install x402[svm]
    """

    def __init__(self, private_key: str) -> None:
        self._private_key = private_key

    def __repr__(self) -> str:
        return f"SVMWallet(pubkey={self._make_signer().keypair.pubkey()!r})"

    def _make_signer(self):
        from solders.keypair import Keypair
        from x402.mechanisms.svm.signers import KeypairSigner
        return KeypairSigner(Keypair.from_base58_string(self._private_key))

    def register_sync(self, client: x402ClientSync) -> None:
        from x402.mechanisms.svm.exact.register import register_exact_svm_client
        register_exact_svm_client(client, self._make_signer())

    async def register_async(self, client: x402Client) -> None:
        from x402.mechanisms.svm.exact.register import register_exact_svm_client
        register_exact_svm_client(client, self._make_signer())
