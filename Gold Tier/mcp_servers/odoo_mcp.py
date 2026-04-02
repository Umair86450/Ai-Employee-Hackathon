"""Odoo 19 JSON-2 MCP server.

Tools:
    - search_records
    - create_invoice
    - post_payment
    - read_transactions
    - generate_summary

Required environment variables:
    ODOO_URL
    ODOO_DB
    ODOO_API_KEY
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Optional
from urllib import error, parse, request

from mcp.server.fastmcp import FastMCP

from env_utils import load_project_dotenv

LOGGER = logging.getLogger("odoo_mcp")

load_project_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


@dataclass(frozen=True)
class OdooConfig:
    url: str
    database: str
    api_key: str
    timeout_seconds: int


class OdooConfigError(ValueError):
    """Raised when Odoo environment configuration is invalid."""


class OdooAPIError(RuntimeError):
    """Raised when the Odoo JSON-2 API returns an error."""


def _load_config() -> OdooConfig:
    url = os.getenv("ODOO_URL", "").strip().rstrip("/")
    database = os.getenv("ODOO_DB", "").strip()
    api_key = os.getenv("ODOO_API_KEY", "").strip()

    if not url:
        raise OdooConfigError("ODOO_URL is required")
    if not database:
        raise OdooConfigError("ODOO_DB is required")
    if not api_key:
        raise OdooConfigError("ODOO_API_KEY is required")

    return OdooConfig(
        url=url,
        database=database,
        api_key=api_key,
        timeout_seconds=int(os.getenv("ODOO_MCP_TIMEOUT", "30")),
    )


def _clean_payload(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    return {key: value for key, value in body.items() if value is not None}


def _as_list_of_ids(value: Any) -> list[int]:
    if isinstance(value, int):
        return [value]
    if isinstance(value, list):
        if value and all(isinstance(item, int) for item in value):
            return value
        if value and all(isinstance(item, dict) and "id" in item for item in value):
            return [int(item["id"]) for item in value]
    raise OdooAPIError(f"Unexpected Odoo id payload: {value!r}")


class OdooClient:
    def __init__(self, config: OdooConfig) -> None:
        self.config = config

    def call(self, model: str, method: str, payload: Optional[dict[str, Any]] = None) -> Any:
        encoded_model = parse.quote(model, safe=".")
        encoded_method = parse.quote(method, safe="_")
        url = f"{self.config.url}/json/2/{encoded_model}/{encoded_method}"
        body = json.dumps(_clean_payload(payload)).encode("utf-8")

        req = request.Request(
            url=url,
            data=body,
            method="POST",
            headers={
                "Authorization": f"bearer {self.config.api_key}",
                "X-Odoo-Database": self.config.database,
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "gold-tier-odoo-mcp/1.0",
            },
        )

        try:
            with request.urlopen(req, timeout=self.config.timeout_seconds) as response:
                raw = response.read()
        except error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                payload = {"message": raw}
            message = payload.get("message") or str(payload)
            raise OdooAPIError(f"Odoo API error [{exc.code}] {message}") from exc
        except error.URLError as exc:
            raise OdooAPIError(f"Unable to reach Odoo at {url}: {exc.reason}") from exc

        if not raw:
            return None
        return json.loads(raw.decode("utf-8"))

    def search_read(
        self,
        *,
        model: str,
        domain: Optional[list[list[Any]]] = None,
        fields: Optional[list[str]] = None,
        limit: Optional[int] = None,
        offset: int = 0,
        order: str = "",
        context: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        payload = {
            "domain": domain or [],
            "fields": fields or [],
            "limit": limit,
            "offset": offset,
            "order": order or None,
            "context": context or None,
        }
        result = self.call(model, "search_read", payload)
        if not isinstance(result, list):
            raise OdooAPIError(f"Expected list result from {model}/search_read, got {type(result)!r}")
        return result


def _client() -> OdooClient:
    return OdooClient(_load_config())


def _resolve_partner(client: OdooClient, *, partner_id: int = 0, customer_name: str = "") -> dict[str, Any]:
    if partner_id > 0:
        records = client.call(
            "res.partner",
            "read",
            {"ids": [partner_id], "fields": ["id", "name", "email"]},
        )
        if not records:
            raise ValueError(f"Partner id {partner_id} not found")
        return records[0]

    name = customer_name.strip()
    if not name:
        raise ValueError("Either 'partner_id' or 'customer_name' is required")

    exact = client.search_read(
        model="res.partner",
        domain=[["name", "=", name], ["is_company", "=", True]],
        fields=["id", "name", "email"],
        limit=1,
    )
    if exact:
        return exact[0]

    fuzzy = client.search_read(
        model="res.partner",
        domain=[["name", "ilike", name], ["is_company", "=", True]],
        fields=["id", "name", "email"],
        limit=1,
    )
    if not fuzzy:
        raise ValueError(f"Customer not found: {name}")
    return fuzzy[0]


def _resolve_product(client: OdooClient, item: dict[str, Any]) -> dict[str, Any]:
    product_id = int(item.get("product_id") or 0)
    if product_id > 0:
        records = client.call(
            "product.product",
            "read",
            {"ids": [product_id], "fields": ["id", "display_name"]},
        )
        if not records:
            raise ValueError(f"Product id {product_id} not found")
        return records[0]

    name = str(item.get("product_name") or item.get("name") or "").strip()
    if not name:
        raise ValueError("Each line item must include 'product_id' or 'product_name'")

    exact = client.search_read(
        model="product.product",
        domain=[["display_name", "=", name]],
        fields=["id", "display_name"],
        limit=1,
    )
    if exact:
        return exact[0]

    fuzzy = client.search_read(
        model="product.product",
        domain=[["display_name", "ilike", name]],
        fields=["id", "display_name"],
        limit=1,
    )
    if not fuzzy:
        raise ValueError(f"Product not found: {name}")
    return fuzzy[0]


def _resolve_journal(client: OdooClient, *, journal_type: str) -> dict[str, Any]:
    journals = client.search_read(
        model="account.journal",
        domain=[["type", "=", journal_type]],
        fields=["id", "name", "type"],
        limit=1,
    )
    if not journals:
        raise ValueError(f"No journal found for type {journal_type!r}")
    return journals[0]


mcp = FastMCP(
    "odoo",
    instructions=(
        "Interact with a self-hosted Odoo 19 instance through the JSON-2 API. "
        "Authentication uses ODOO_URL, ODOO_DB, and ODOO_API_KEY."
    ),
)


@mcp.tool()
def search_records(
    model: str,
    domain: Optional[list[list[Any]]] = None,
    fields: Optional[list[str]] = None,
    limit: int = 20,
    offset: int = 0,
    order: str = "",
    context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Search Odoo records using search_read."""

    if not model.strip():
        raise ValueError("'model' is required")
    if limit <= 0:
        raise ValueError("'limit' must be greater than 0")

    records = _client().search_read(
        model=model.strip(),
        domain=domain or [],
        fields=fields or [],
        limit=limit,
        offset=offset,
        order=order,
        context=context or {},
    )
    return {
        "model": model.strip(),
        "count": len(records),
        "records": records,
    }


@mcp.tool()
def create_invoice(
    customer_name: str = "",
    partner_id: int = 0,
    line_items: Optional[list[dict[str, Any]]] = None,
    ref: str = "",
    invoice_date: str = "",
    due_date: str = "",
    journal_type: str = "sale",
    post_immediately: bool = True,
) -> dict[str, Any]:
    """Create an Odoo customer invoice and optionally post it."""

    items = line_items or []
    if not items:
        raise ValueError("'line_items' must contain at least one item")

    client = _client()
    partner = _resolve_partner(client, partner_id=partner_id, customer_name=customer_name)
    journal = _resolve_journal(client, journal_type=journal_type)

    invoice_lines: list[list[Any]] = []
    for item in items:
        product = _resolve_product(client, item)
        quantity = float(item.get("quantity", 1))
        price_unit = float(item.get("price_unit", item.get("price", 0)))
        if quantity <= 0:
            raise ValueError("Invoice line quantity must be greater than 0")

        invoice_lines.append(
            [
                0,
                0,
                {
                    "product_id": product["id"],
                    "name": str(item.get("description") or product["display_name"]),
                    "quantity": quantity,
                    "price_unit": price_unit,
                },
            ]
        )

    vals: dict[str, Any] = {
        "move_type": "out_invoice",
        "partner_id": partner["id"],
        "journal_id": journal["id"],
        "invoice_line_ids": invoice_lines,
    }
    if ref.strip():
        vals["ref"] = ref.strip()
    if invoice_date.strip():
        vals["invoice_date"] = invoice_date.strip()
    if due_date.strip():
        vals["invoice_date_due"] = due_date.strip()

    created = client.call("account.move", "create", {"vals_list": [vals]})
    invoice_id = _as_list_of_ids(created)[0]

    if post_immediately:
        client.call("account.move", "action_post", {"ids": [invoice_id]})

    invoice = client.call(
        "account.move",
        "read",
        {
            "ids": [invoice_id],
            "fields": [
                "id",
                "name",
                "ref",
                "state",
                "payment_state",
                "amount_total",
                "amount_residual",
                "invoice_date",
                "invoice_date_due",
            ],
            "load": None,
        },
    )[0]

    return {
        "status": "posted" if post_immediately else "draft_created",
        "partner": partner,
        "journal": journal,
        "invoice": invoice,
    }


@mcp.tool()
def post_payment(
    invoice_id: int = 0,
    invoice_ref: str = "",
    amount: Optional[float] = None,
    payment_date: str = "",
    journal_type: str = "bank",
    memo: str = "",
) -> dict[str, Any]:
    """Register and post a payment against an invoice using Odoo's payment wizard."""

    client = _client()

    if invoice_id > 0:
        invoice_records = client.call(
            "account.move",
            "read",
            {
                "ids": [invoice_id],
                "fields": ["id", "name", "ref", "state", "payment_state", "amount_residual"],
                "load": None,
            },
        )
    else:
        if not invoice_ref.strip():
            raise ValueError("Either 'invoice_id' or 'invoice_ref' is required")
        invoice_records = client.search_read(
            model="account.move",
            domain=[["ref", "=", invoice_ref.strip()], ["move_type", "=", "out_invoice"]],
            fields=["id", "name", "ref", "state", "payment_state", "amount_residual"],
            limit=1,
        )

    if not invoice_records:
        raise ValueError("Invoice not found")

    invoice = invoice_records[0]
    if invoice["state"] != "posted":
        raise ValueError("Invoice must be posted before payment")

    amount_to_pay = float(amount if amount is not None else invoice["amount_residual"])
    if amount_to_pay <= 0:
        raise ValueError("Payment amount must be greater than 0")

    journal = _resolve_journal(client, journal_type=journal_type)
    wizard_vals = {
        "journal_id": journal["id"],
        "amount": amount_to_pay,
        "payment_date": payment_date.strip() or str(date.today()),
        "communication": memo.strip() or invoice.get("ref") or invoice.get("name"),
    }
    context = {"active_model": "account.move", "active_ids": [invoice["id"]]}

    wizard_created = client.call(
        "account.payment.register",
        "create",
        {"context": context, "vals_list": [wizard_vals]},
    )
    wizard_id = _as_list_of_ids(wizard_created)[0]
    payment_result = client.call(
        "account.payment.register",
        "action_create_payments",
        {"ids": [wizard_id], "context": context},
    )

    refreshed_invoice = client.call(
        "account.move",
        "read",
        {
            "ids": [invoice["id"]],
            "fields": ["id", "name", "ref", "state", "payment_state", "amount_total", "amount_residual"],
            "load": None,
        },
    )[0]

    return {
        "status": "payment_posted",
        "journal": journal,
        "invoice": refreshed_invoice,
        "payment_result": payment_result,
        "wizard_id": wizard_id,
    }


@mcp.tool()
def read_transactions(
    days: int = 30,
    partner_name: str = "",
    limit: int = 20,
) -> dict[str, Any]:
    """Read recent posted invoices and payments."""

    if days <= 0:
        raise ValueError("'days' must be greater than 0")
    if limit <= 0:
        raise ValueError("'limit' must be greater than 0")

    client = _client()
    date_from = str(date.today() - timedelta(days=days))

    invoice_domain: list[list[Any]] = [["state", "=", "posted"], ["move_type", "=", "out_invoice"]]
    payment_domain: list[list[Any]] = [["state", "=", "posted"]]
    invoice_domain.append(["invoice_date", ">=", date_from])
    payment_domain.append(["date", ">=", date_from])

    if partner_name.strip():
        invoice_domain.append(["partner_id.name", "ilike", partner_name.strip()])
        payment_domain.append(["partner_id.name", "ilike", partner_name.strip()])

    invoices = client.search_read(
        model="account.move",
        domain=invoice_domain,
        fields=["id", "name", "ref", "invoice_date", "partner_id", "amount_total", "amount_residual", "payment_state"],
        limit=limit,
        order="invoice_date desc, id desc",
    )
    payments = client.search_read(
        model="account.payment",
        domain=payment_domain,
        fields=["id", "name", "payment_reference", "date", "partner_id", "amount", "state", "journal_id"],
        limit=limit,
        order="date desc, id desc",
    )

    return {
        "days": days,
        "partner_name": partner_name.strip(),
        "invoice_count": len(invoices),
        "payment_count": len(payments),
        "invoices": invoices,
        "payments": payments,
    }


@mcp.tool()
def generate_summary(days: int = 30) -> dict[str, Any]:
    """Generate a lightweight accounting summary from recent invoices and payments."""

    transactions = read_transactions(days=days, partner_name="", limit=100)
    invoices = transactions["invoices"]
    payments = transactions["payments"]

    total_invoiced = round(sum(float(item.get("amount_total", 0) or 0) for item in invoices), 2)
    total_outstanding = round(sum(float(item.get("amount_residual", 0) or 0) for item in invoices), 2)
    total_paid = round(sum(float(item.get("amount", 0) or 0) for item in payments), 2)
    open_invoices = [item for item in invoices if item.get("payment_state") != "paid"]

    top_open = sorted(
        open_invoices,
        key=lambda item: float(item.get("amount_residual", 0) or 0),
        reverse=True,
    )[:5]

    return {
        "days": days,
        "invoice_count": len(invoices),
        "payment_count": len(payments),
        "total_invoiced": total_invoiced,
        "total_paid": total_paid,
        "total_outstanding": total_outstanding,
        "open_invoice_count": len(open_invoices),
        "top_open_invoices": top_open,
        "latest_invoices": invoices[:5],
        "latest_payments": payments[:5],
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=os.getenv("ODOO_MCP_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    mcp.run(transport="stdio")
