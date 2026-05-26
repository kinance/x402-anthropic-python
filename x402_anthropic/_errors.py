"""Public exception types for x402-anthropic."""

from __future__ import annotations


class X402PaymentError(Exception):
    """Raised when the x402 payment signing or retry step fails.

    Distinguishes payment-layer failures from Anthropic API errors so callers
    can handle them separately.
    """
