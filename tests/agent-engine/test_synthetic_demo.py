"""Concrete synthetic RFQ XLSX and supplier verification from one factory core."""

import pytest
from agent_runtime.synthetic_demo import execute_two_tasks
from openpyxl import load_workbook


@pytest.mark.asyncio
async def test_two_business_tasks_with_real_synthetic_excel(tmp_path):
    (rfq_spec, rfq_result, rfq_tools), (supplier_spec, supplier_result, supplier_tools) = (
        await execute_two_tasks(tmp_path))
    assert rfq_result.status == 'COMPLETED'
    assert supplier_result.status == 'COMPLETED'
    assert rfq_spec.artifact_digest != supplier_spec.artifact_digest
    assert {x.tool_id for x in supplier_spec.selected_tools} == {'supplier.lookup'}
    assert len(rfq_tools.calls) == 3 and len(supplier_tools.calls) == 1
    assert all('draft' not in call[1] for call in supplier_tools.calls)
    workbook = load_workbook(tmp_path / 'draft-quote.xlsx', data_only=True, read_only=True)
    try:
        sheet = workbook.active
        assert sheet is not None
        assert sheet['D2'].value == 24
    finally:
        workbook.close()
