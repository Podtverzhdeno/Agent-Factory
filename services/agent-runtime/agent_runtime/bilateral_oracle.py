"""Independent evidence-based quotation validator. No A2A transport dependencies."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass(frozen=True)
class RFQ:
    buyer: str
    supplier: str
    sku: str
    quantity: int | None
    unit: str
    currency: str
    buyer_max_total: str
    supplier_min_unit_price: str


@dataclass(frozen=True)
class Quote:
    buyer: str
    supplier: str
    sku: str
    quantity: int
    unit: str
    currency: str
    unit_price: str
    total: str
    catalog_ref: str
    catalog_digest: str
    catalog_updated_at: int
    sharing_authorized: bool
    disclosed_private_fields: tuple[str, ...] = ()

    def digest(self) -> str:
        body = json.dumps(asdict(self), sort_keys=True, separators=(',', ':'),
                          ensure_ascii=True, allow_nan=False)
        return 'sha256:' + hashlib.sha256(body.encode()).hexdigest()


@dataclass(frozen=True)
class Event:
    actor: str
    kind: str
    data: dict[str, Any]


@dataclass(frozen=True)
class Verdict:
    passed: bool
    code: str
    buyer_pass: bool
    supplier_pass: bool
    quote_digest: str | None = None


def _money(raw: object) -> Decimal | None:
    # Neither binary floats nor locale-dependent strings are valid price evidence.
    if not isinstance(raw, str):
        return None
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    if not value.is_finite() or value < 0 or value.as_tuple().exponent < -2:
        return None
    return value


def evaluate_quote(rfq: RFQ, events: list[Event], quote: Quote | None,
                   *, now: int, max_catalog_age_seconds: int = 86400,
                   attest_catalog: Callable[[Quote], bool] | None = None,
                   attest_artifact: Callable[[Quote], bool] | None = None) -> Verdict:
    """Verify observed event contract and independently supplied business evidence.

    This is deliberately not based on agent-generated final response text.
    A real A2A adapter and independent, signed artifact store are still required.
    """
    def fail(code: str, buyer: bool = False, supplier: bool = False) -> Verdict:
        return Verdict(False, code, buyer, supplier)

    if not rfq.buyer or not rfq.supplier or rfq.buyer == rfq.supplier:
        return fail('INVALID_PARTIES')
    if not rfq.sku or not rfq.unit or not rfq.currency:
        return fail('INVALID_RFQ')
    if not events or len(events) > 10 or events[0].actor != rfq.buyer or events[0].kind != 'REQUEST':
        return fail('INVALID_DIALOGUE')
    if events[0].data.get('sku') != rfq.sku:
        return fail('RFQ_MISMATCH')
    sequence = [(event.actor, event.kind) for event in events]
    if rfq.quantity is None:
        expected = [(rfq.buyer, 'REQUEST'), (rfq.supplier, 'CLARIFY'),
                    (rfq.buyer, 'REPLY'), (rfq.supplier, 'OFFER'),
                    (rfq.supplier, 'COMPLETE')]
        if sequence != expected or events[1].data.get('field') != 'quantity':
            return fail('MISSING_CLARIFICATION')
        quantity = events[2].data.get('quantity')
    else:
        expected = [(rfq.buyer, 'REQUEST'), (rfq.supplier, 'OFFER'),
                    (rfq.supplier, 'COMPLETE')]
        if sequence != expected or events[0].data.get('quantity') != rfq.quantity:
            return fail('INVALID_DIALOGUE')
        quantity = rfq.quantity
    if type(quantity) is not int or quantity <= 0:
        return fail('INVALID_QUANTITY')
    if quote is None:
        return fail('MISSING_BUSINESS_ARTIFACT')
    if (quote.buyer != rfq.buyer or quote.supplier != rfq.supplier or
            quote.sku != rfq.sku or quote.quantity != quantity or
            quote.unit != rfq.unit or quote.currency != rfq.currency):
        return fail('QUOTE_CONTRACT_MISMATCH')
    if not quote.sharing_authorized or quote.disclosed_private_fields:
        return fail('SUPPLIER_DISCLOSURE_DENIED')
    if (not quote.catalog_ref.startswith('artifact://supplier/catalog/') or
            len(quote.catalog_digest) != 71 or
            not quote.catalog_digest.startswith('sha256:') or
            any(ch not in '0123456789abcdef' for ch in quote.catalog_digest[7:])):
        return fail('MISSING_VERIFIED_PROVENANCE')
    if (type(now) is not int or type(quote.catalog_updated_at) is not int
            or now < quote.catalog_updated_at or
            now - quote.catalog_updated_at > max_catalog_age_seconds):
        return fail('EXPIRED_CATALOG_EVIDENCE')
    price = _money(quote.unit_price)
    total = _money(quote.total)
    ceiling = _money(rfq.buyer_max_total)
    floor = _money(rfq.supplier_min_unit_price)
    if None in (price, total, ceiling, floor):
        return fail('INVALID_MONEY')
    if price * quantity != total:
        return fail('WRONG_QUOTE_TOTAL')
    buyer_pass = total <= ceiling
    supplier_pass = price >= floor
    if not buyer_pass or not supplier_pass:
        return fail('COUNTERPARTY_POLICY_DENIED', buyer_pass, supplier_pass)
    digest = quote.digest()
    if events[-2].data.get('artifact_digest') != digest:
        return fail('ARTIFACT_INTEGRITY_DENIED')
    # A hash proves structural integrity, never provenance or issuer authority.
    # Two independent injected trusted ports must attest the evidence.
    if attest_catalog is None or attest_artifact is None:
        return fail('ATTESTATION_REQUIRED')
    try:
        if not attest_catalog(quote) or not attest_artifact(quote):
            return fail('ATTESTATION_FAILED')
    except Exception:  # noqa: BLE001 - external attestation outage must fail closed.
        return fail('ATTESTATION_FAILED')
    return Verdict(True, 'PASS', True, True, digest)


