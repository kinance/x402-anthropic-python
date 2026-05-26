"""Mock FacilitatorClientSync — auto-approves all payments, no blockchain calls."""

from __future__ import annotations

from x402.http.facilitator_client import FacilitatorClientSync
from x402.schemas import (
    SettleResponse,
    SupportedKind,
    SupportedResponse,
    VerifyResponse,
)

MOCK_PAYER = "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
MOCK_TX = "0x" + "00" * 32


class MockFacilitatorClient(FacilitatorClientSync):
    """Drop-in FacilitatorClientSync that always approves payments.

    Satisfies the FacilitatorClientSync Protocol without any HTTP calls.
    Safe for local testing — never touches a real blockchain.
    """

    def get_supported(self) -> SupportedResponse:
        return SupportedResponse(
            kinds=[
                SupportedKind(x402_version=2, scheme="exact", network="eip155:8453"),
            ],
            extensions=[],
            signers={"eip155:*": [MOCK_PAYER]},
        )

    def verify(self, payload, requirements) -> VerifyResponse:
        return VerifyResponse(is_valid=True, payer=MOCK_PAYER)

    def settle(self, payload, requirements) -> SettleResponse:
        return SettleResponse(
            success=True,
            transaction=MOCK_TX,
            network="eip155:8453",
            payer=MOCK_PAYER,
        )
