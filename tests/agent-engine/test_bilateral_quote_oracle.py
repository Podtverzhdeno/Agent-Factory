"""Synthetic acceptance tests for the reusable Runtime business oracle."""

from dataclasses import replace

import pytest

from agent_runtime.bilateral_oracle import Event, Quote, RFQ, evaluate_quote


NOW = 200000

def evaluate_verified(rfq, events, quote, *, now):
    # Synthetic test-only attestation ports; never accept model-supplied flags.
    return evaluate_quote(rfq, events, quote, now=now,
                          attest_catalog=lambda _quote: True,
                          attest_artifact=lambda _quote: True)


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
    return evaluate_verified(rfq if rfq is not None else a,
                          events if events is not None else b,
                          quote if quote is not None else c, now=NOW)


def test_valid_bilateral_clarification_and_exact_quote():
    result = run()
    assert (result.passed, result.code, result.buyer_pass, result.supplier_pass) == (True,'PASS',True,True)
    assert result.quote_digest == fixture()[2].digest()


def test_valid_bilateral_request_with_complete_quantity():
    rfq,events,quote=fixture(clarification=False)
    assert evaluate_verified(rfq,events,quote,now=NOW).passed


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
    assert evaluate_verified(rfq,events,modified,now=NOW).code == error


def test_supplier_draft_cannot_pass_only_with_task_completed():
    rfq,events,quote=fixture()
    assert evaluate_verified(rfq,events,None,now=NOW).code == 'MISSING_BUSINESS_ARTIFACT'


def test_supplier_cannot_invent_missing_quantity_or_clarify_for_buyer():
    rfq,events,quote=fixture()
    assert evaluate_verified(rfq,[events[0],*events[-2:]],quote,now=NOW).code == 'MISSING_CLARIFICATION'
    events[2]=Event('supplier-b','REPLY',{'quantity':2})
    assert evaluate_verified(rfq,events,quote,now=NOW).code == 'MISSING_CLARIFICATION'


def test_both_companies_have_independent_hard_business_constraints():
    rfq,events,quote=fixture()
    result=evaluate_verified(replace(rfq,buyer_max_total='20.00'),events,quote,now=NOW)
    assert not result.passed and not result.buyer_pass and result.supplier_pass
    result=evaluate_verified(replace(rfq,supplier_min_unit_price='14.00'),events,quote,now=NOW)
    assert not result.passed and result.buyer_pass and not result.supplier_pass


def test_quote_digest_detects_artifact_tamper():
    rfq,events,quote=fixture()
    quote=replace(quote,unit_price='12.50',total='25.00')
    assert evaluate_verified(rfq,events,quote,now=NOW).code=='ARTIFACT_INTEGRITY_DENIED'


def test_invalid_qty_and_duplicate_offer_do_not_pass():
    rfq,events,quote=fixture()
    events[2]=Event('buyer-a','REPLY',{'quantity':0})
    assert evaluate_verified(rfq,events,quote,now=NOW).code=='INVALID_QUANTITY'
    rfq,events,quote=fixture()
    events.insert(-1,events[-2])
    assert evaluate_verified(rfq,events,quote,now=NOW).code=='MISSING_CLARIFICATION'

def test_valid_quote_requires_two_independent_evidence_attestors():
    rfq, events, quote = fixture()
    assert evaluate_quote(rfq, events, quote, now=NOW).code == 'ATTESTATION_REQUIRED'
    assert evaluate_quote(rfq, events, quote, now=NOW,
                          attest_catalog=lambda _: True).code == 'ATTESTATION_REQUIRED'
    assert evaluate_quote(rfq, events, quote, now=NOW,
                          attest_artifact=lambda _: True).code == 'ATTESTATION_REQUIRED'


def test_attestation_failures_and_timeouts_deny_business_pass():
    rfq, events, quote = fixture()
    assert evaluate_quote(rfq, events, quote, now=NOW,
                          attest_catalog=lambda _: False,
                          attest_artifact=lambda _: True).code == 'ATTESTATION_FAILED'
    assert evaluate_quote(rfq, events, quote, now=NOW,
                          attest_catalog=lambda _: True,
                          attest_artifact=lambda _: False).code == 'ATTESTATION_FAILED'
    def unavailable(_):
        raise TimeoutError('synthetic provider timeout')
    assert evaluate_quote(rfq, events, quote, now=NOW,
                          attest_catalog=unavailable,
                          attest_artifact=lambda _: True).code == 'ATTESTATION_FAILED'
