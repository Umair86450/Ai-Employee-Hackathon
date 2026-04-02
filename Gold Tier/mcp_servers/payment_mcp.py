"""Payment MCP server (HITL-safe stub).

This server provides `process_payment` for Silver Tier HITL orchestration.
By design it does not execute real transfers; it returns a review-required result.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

LOGGER = logging.getLogger("payment_mcp")

mcp = FastMCP(
    "payment",
    instructions=(
        "Review and process payment requests in a HITL-safe way. "
        "This stub validates payload and returns manual-review status."
    ),
)


@mcp.tool()
def process_payment(
    payee: str,
    amount: float,
    currency: str = "USD",
    reference: str = "",
    note: str = "",
) -> dict[str, Any]:
    """Validate payment payload and return manual-review response.

    Args:
        payee: Recipient/payee identifier.
        amount: Positive payment amount.
        currency: ISO currency code.
        reference: Optional invoice/reference id.
        note: Optional note.
    """

    if not payee.strip():
        raise ValueError("'payee' is required")
    if amount <= 0:
        raise ValueError("'amount' must be greater than 0")
    if not currency.strip():
        raise ValueError("'currency' is required")

    payload = {
        "status": "approved_for_manual_execution",
        "payee": payee.strip(),
        "amount": round(float(amount), 2),
        "currency": currency.strip().upper(),
        "reference": reference.strip(),
        "note": note.strip(),
    }
    LOGGER.info("Payment request accepted for manual execution: %s", payload)
    return payload


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("PAYMENT_MCP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")
