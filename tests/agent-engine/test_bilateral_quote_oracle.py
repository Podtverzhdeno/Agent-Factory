"""Deterministic, synthetic buyer/supplier quote contract oracle, not A2A SDK E2E."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from decimal import Decimal, InvalidOperation
from typing import Any

import pytest


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
                   *, now: int, max_catalog_age_seconds: int = 86400) -> Verdict:
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
    return Verdict(True, 'PASS', True, True, digest)


NOW = 200000

def fixture(*, clarification: bool = True):
    rfq = RFQ('buyer-a', 'supplier-b', 'BOLT-1', None if clarification else 2,
              'pcs', 'USD', '30.00', '10.00')
    quote = Quote('buyer-a', 'supplier-b', 'BOLT-1', 2, 'pcs', 'USD',
                  '12.40', '24.80', 'artifact://supplier/catalog/v1',
                  'sha256:' + 'a'*64, NOW-60, True)
    events = [Event('buyer-a', 'REQUEST', {'sku':'BOLT-1'})]
    if clarification:
        events += [Event('supplier-b','CLARIFY',{'field':'quantity'}),
                   Event('buyer-a','REPLY',{'quantity':2})]
    else:
        events[0] = Event('buyer-a','REQUEST',{'sku':'BOLT-1','quantity':2})
    events += [Event('supplier-b','OFFER',{'artifact_digest':quote.digest()}),
               Event('supplier-b','COMPLETE',{})]
    return rfq, events, quote


def run(rfq=None, events=None, quote=None):
    a,b,c=fixture()
    return evaluate_quote(rfq if rfq is not None else a,
                          events if events is not None else b,
                          quote if quote is not None else c, now=NOW)


def test_valid_bilateral_clarification_and_exact_quote():
    result = run()
    assert (result.passed, result.code, result.buyer_pass, result.supplier_pass) == (True,'PASS',True,True)
    assert result.quote_digest == fixture()[2].digest()


def test_valid_bilateral_request_with_complete_quantity():
    rfq,events,quote=fixture(clarification=False)
    assert evaluate_quote(rfq,events,quote,now=NOW).passed


@pytest.mark.parametrize('change,error', [
    ({'total':'24.79'},'WRONG_QUOTE_TOTAL'),
    ({'currency':'EUR'},'QUOTE_CONTRACT_MISMATCH'),
    ({'unit':'kg'},'QUOTE_CONTRACT_MISMATCH'),
    ({'quantity':3},'QUOTE_CONTRACT_MISMATCH'),
    ({'unit_price':'NaN'},'INVALID_MONEY'),
    ({'unit_price':'12.401'},'INVALID_MONEY'),
    ({'catalog_digest':'sha256:fake'},'MISSING_VERIFIED_PROVENANCE'),
    ({'catalog_updated_at':NOW-90000},'EXPIRED_CATALOG_EVIDENCE'),
    ({'sharing_authorized':False},'SUPPLIER_DISCLOSURE_DENIED'),
    ({'disclosed_private_fields':('internal_margin',)},'SUPPLIER_DISCLOSURE_DENIED'),
    ({'buyer':'wrong-company'},'QUOTE_CONTRACT_MISMATCH'),
])
def test_invalid_supplier_quote_fails_independent_oracle(change,error):
    rfq,events,quote=fixture()
    modified=replace(quote,**change)
    events[-2]=Event('supplier-b','OFFER',{'artifact_digest':modified.digest()})
    assert evaluate_quote(rfq,events,modified,now=NOW).code == error


def test_supplier_draft_cannot_pass_only_with_task_completed():
    rfq,events,quote=fixture()
    assert evaluate_quote(rfq,events,None,now=NOW).code == 'MISSING_BUSINESS_ARTIFACT'


def test_supplier_cannot_invent_missing_quantity_or_clarify_for_buyer():
    rfq,events,quote=fixture()
    assert evaluate_quote(rfq,[events[0],*events[-2:]],quote,now=NOW).code == 'MISSING_CLARIFICATION'
    events[2]=Event('supplier-b','REPLY',{'quantity':2})
    assert evaluate_quote(rfq,events,quote,now=NOW).code == 'MISSING_CLARIFICATION'


def test_both_companies_have_independent_hard_business_constraints():
    rfq,events,quote=fixture()
    result=evaluate_quote(replace(rfq,buyer_max_total='20.00'),events,quote,now=NOW)
    assert not result.passed and not result.buyer_pass and result.supplier_pass
    result=evaluate_quote(replace(rfq,supplier_min_unit_price='14.00'),events,quote,now=NOW)
    assert not result.passed and result.buyer_pass and not result.supplier_pass


def test_quote_digest_detects_artifact_tamper():
    rfq,events,quote=fixture()
    quote=replace(quote,unit_price='12.50',total='25.00')
    assert evaluate_quote(rfq,events,quote,now=NOW).code=='ARTIFACT_INTEGRITY_DENIED'


def test_invalid_qty_and_duplicate_offer_do_not_pass():
    rfq,events,quote=fixture()
    events[2]=Event('buyer-a','REPLY',{'quantity':0})
    assert evaluate_quote(rfq,events,quote,now=NOW).code=='INVALID_QUANTITY'
    rfq,events,quote=fixture()
    events.insert(-1,events[-2])
    assert evaluate_quote(rfq,events,quote,now=NOW).code=='MISSING_CLARIFICATION'
