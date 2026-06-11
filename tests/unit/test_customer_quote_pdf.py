from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Any

from corequote_core.customer_quote_pdf import (
    build_customer_quote_document,
    customer_quote_filename,
    render_customer_quote_pdf,
)


def test_customer_quote_document_excludes_internal_fields_and_groups_totals():
    document = build_customer_quote_document(
        company={
            "name": "CoreQuote Test Co",
            "contact_name": "Test Owner",
            "contact_email": "test.owner@corequote.local",
        },
        quote={
            "name": "Smith Kitchen Quote v1",
            "notes": "50% deposit, balance before installation.",
            "quote_number": "Q-001",
            "revision": 1,
        },
        project={
            "name": "Smith Kitchen",
            "client": "Alex Smith",
            "address": "12 Oak Street",
        },
        currency_code="ZAR",
        pricing_summary={
            "sell_before_vat_cents": 400000,
            "vat_cents": 60000,
            "grand_total_cents": 460000,
            "cost_total_cents": 250000,
            "profit_cents": 150000,
            "bucket_totals": [
                {"bucket": "component", "sell_total_cents": 50000, "cost_total_cents": 30000, "profit_cents": 20000},
                {"bucket": "handle", "sell_total_cents": 25000, "cost_total_cents": 10000, "profit_cents": 15000},
                {"bucket": "extra", "sell_total_cents": 10000, "cost_total_cents": 5000, "profit_cents": 5000},
                {"bucket": "installation", "sell_total_cents": 60000, "cost_total_cents": 40000, "profit_cents": 20000},
                {"bucket": "delivery", "sell_total_cents": 20000, "cost_total_cents": 15000, "profit_cents": 5000},
            ],
            "material_summary": {
                "groups": [
                    {
                        "material_role": "visible_panel",
                        "sell_total_cents": 70000,
                        "cost_total_cents": 40000,
                    }
                ]
            },
        },
        issue_date=date(2026, 6, 1),
    )

    assert document.company_name == "CoreQuote Test Co"
    assert document.client_name == "Alex Smith"
    assert document.issue_date == date(2026, 6, 1)
    assert document.expiry_date == date(2026, 7, 1)
    assert document.terms == "50% deposit, balance before installation."
    assert [(section.label, section.amount_cents) for section in document.sections] == [
        ("Cabinetry", 165000),
        ("Visible panels", 70000),
        ("Hardware and extras", 85000),
        ("Installation", 60000),
        ("Delivery", 20000),
    ]
    assert document.subtotal_cents == 400000
    assert document.vat_cents == 60000
    assert document.grand_total_cents == 460000

    for key in _keys(asdict(document)):
        assert "cost" not in key
        assert "profit" not in key
        assert "margin" not in key


def test_customer_quote_pdf_renders_bytes_and_business_filename():
    document = build_customer_quote_document(
        company={"name": "CoreQuote Test Co", "contact_name": "Test Owner", "contact_email": "test.owner@corequote.local"},
        quote={"name": "Smith Kitchen Quote v1", "quote_number": "Q-001", "revision": 1},
        project={"name": "Smith Kitchen", "client": "Alex Smith", "address": "12 Oak Street"},
        currency_code="ZAR",
        pricing_summary={
            "sell_before_vat_cents": 100000,
            "vat_cents": 15000,
            "grand_total_cents": 115000,
            "bucket_totals": [],
            "material_summary": {"groups": []},
        },
        issue_date=date(2026, 6, 1),
    )

    assert customer_quote_filename(document) == "Smith-Kitchen-Quote-v1-Q-001-rev-1.pdf"
    pdf_bytes = render_customer_quote_pdf(document)
    assert bytes(pdf_bytes).startswith(b"%PDF")


def _keys(value: Any) -> list[str]:
    if isinstance(value, dict):
        found: list[str] = []
        for key, child in value.items():
            found.append(str(key))
            found.extend(_keys(child))
        return found
    if isinstance(value, list):
        found = []
        for child in value:
            found.extend(_keys(child))
        return found
    return []
