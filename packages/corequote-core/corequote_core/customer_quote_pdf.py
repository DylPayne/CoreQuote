"""Customer-facing quote PDF output.

The dataclasses in this module intentionally model only customer-visible data.
Internal cost, margin, and profit fields stay in pricing summaries and are not
copied into the document model.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from fpdf import FPDF


DEFAULT_EXPIRY_DAYS = 30
DEFAULT_TERMS = "Valid until the expiry date shown. Scope changes may require a revised quote."


@dataclass(frozen=True)
class CustomerQuoteSection:
    label: str
    amount_cents: int


@dataclass(frozen=True)
class CustomerQuoteDocument:
    company_name: str
    company_contact_name: str
    company_contact_email: str
    currency_code: str
    project_name: str
    client_name: str
    site_address: str
    quote_name: str
    quote_number: str
    revision: int
    issue_date: date
    expiry_date: date
    terms: str
    sections: list[CustomerQuoteSection]
    subtotal_cents: int
    vat_cents: int
    grand_total_cents: int


class CustomerQuotePDF(FPDF):
    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(110, 110, 110)
        self.cell(0, 8, _pdf_text(f"Page {self.page_no()}"), align="C")


def build_customer_quote_document(
    *,
    company: dict[str, Any],
    quote: dict[str, Any],
    project: dict[str, Any],
    currency_code: str,
    pricing_summary: dict[str, Any],
    issue_date: date | None = None,
    expiry_days: int = DEFAULT_EXPIRY_DAYS,
) -> CustomerQuoteDocument:
    """Build the customer-facing quote model from internal quote data."""

    issued = issue_date or date.today()
    subtotal_cents = _positive_int(pricing_summary.get("sell_before_vat_cents"))
    sections = _customer_sections(pricing_summary, subtotal_cents=subtotal_cents)
    return CustomerQuoteDocument(
        company_name=_text(company.get("name"), fallback="Company"),
        company_contact_name=_text(company.get("contact_name"), fallback=""),
        company_contact_email=_text(company.get("contact_email"), fallback=""),
        currency_code=_currency(currency_code),
        project_name=_text(project.get("name"), fallback="Project"),
        client_name=_text(project.get("client"), fallback="Client"),
        site_address=_text(project.get("address"), fallback=""),
        quote_name=_text(quote.get("name"), fallback="Quote"),
        quote_number=_text(quote.get("quote_number"), fallback="Quote"),
        revision=max(1, _positive_int(quote.get("revision"))),
        issue_date=issued,
        expiry_date=issued + timedelta(days=max(1, expiry_days)),
        terms=_text(quote.get("notes"), fallback=DEFAULT_TERMS),
        sections=sections,
        subtotal_cents=subtotal_cents,
        vat_cents=_positive_int(pricing_summary.get("vat_cents")),
        grand_total_cents=_positive_int(pricing_summary.get("grand_total_cents")),
    )


def customer_quote_filename(document: CustomerQuoteDocument) -> str:
    base = "-".join(
        part
        for part in (
            _filename_part(document.quote_name),
            _filename_part(document.quote_number),
            f"rev-{document.revision}",
        )
        if part
    )
    return f"{base or 'customer-quote'}.pdf"


def render_customer_quote_pdf(document: CustomerQuoteDocument) -> bytes:
    pdf = CustomerQuotePDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    _draw_header(pdf, document)
    _draw_quote_meta(pdf, document)
    _draw_summary(pdf, document)
    _draw_terms(pdf, document)
    return bytes(pdf.output())


def _customer_sections(pricing_summary: dict[str, Any], *, subtotal_cents: int) -> list[CustomerQuoteSection]:
    visible_panels_cents = _material_role_total(pricing_summary, "visible_panel")
    hardware_extras_cents = _bucket_total(pricing_summary, {"component", "handle", "extra"})
    installation_cents = _bucket_total(pricing_summary, {"installation"})
    delivery_cents = _bucket_total(pricing_summary, {"delivery"})
    allocated_cents = visible_panels_cents + hardware_extras_cents + installation_cents + delivery_cents
    cabinetry_cents = max(0, subtotal_cents - allocated_cents)

    sections = [
        CustomerQuoteSection("Cabinetry", cabinetry_cents),
        CustomerQuoteSection("Visible panels", visible_panels_cents),
        CustomerQuoteSection("Hardware and extras", hardware_extras_cents),
        CustomerQuoteSection("Installation", installation_cents),
        CustomerQuoteSection("Delivery", delivery_cents),
    ]
    return [section for section in sections if section.amount_cents > 0]


def _draw_header(pdf: FPDF, document: CustomerQuoteDocument) -> None:
    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(205, 211, 220)
    pdf.rect(10, 10, 34, 22, style="DF")
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(45, 55, 72)
    pdf.set_xy(10, 17)
    pdf.cell(34, 6, _pdf_text(_initials(document.company_name)), align="C")

    pdf.set_xy(50, 10)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(0, 8, _pdf_text(document.company_name))
    pdf.set_xy(50, 19)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 96, 110)
    contact = " / ".join(part for part in (document.company_contact_name, document.company_contact_email) if part)
    pdf.cell(0, 6, _pdf_text(contact or "Contact details not configured"))

    pdf.set_xy(140, 12)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(60, 8, _pdf_text("Customer Quote"), align="R")
    pdf.set_xy(140, 22)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(90, 96, 110)
    pdf.cell(60, 5, _pdf_text(document.currency_code), align="R")
    pdf.ln(24)


def _draw_quote_meta(pdf: FPDF, document: CustomerQuoteDocument) -> None:
    start_y = pdf.get_y() + 4
    left = [
        ("Client", document.client_name),
        ("Site", document.site_address or "-"),
        ("Project", document.project_name),
    ]
    right = [
        ("Quote", document.quote_number),
        ("Revision", str(document.revision)),
        ("Issue date", document.issue_date.isoformat()),
        ("Expiry date", document.expiry_date.isoformat()),
    ]

    pdf.set_y(start_y)
    _draw_label_values(pdf, left, x=10, width=86)
    pdf.set_y(start_y)
    _draw_label_values(pdf, right, x=112, width=88)
    pdf.ln(8)


def _draw_summary(pdf: FPDF, document: CustomerQuoteDocument) -> None:
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(0, 8, _pdf_text(document.quote_name), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_fill_color(245, 247, 250)
    pdf.set_draw_color(205, 211, 220)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(130, 8, _pdf_text("Section"), border=1, fill=True)
    pdf.cell(50, 8, _pdf_text("Amount"), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    for section in document.sections:
        pdf.cell(130, 8, _pdf_text(section.label), border=1)
        pdf.cell(
            50,
            8,
            _pdf_text(_money(section.amount_cents, document.currency_code)),
            border=1,
            align="R",
            new_x="LMARGIN",
            new_y="NEXT",
        )

    pdf.ln(2)
    _draw_total_row(pdf, "Subtotal", document.subtotal_cents, document.currency_code, bold=False)
    _draw_total_row(pdf, "VAT", document.vat_cents, document.currency_code, bold=False)
    _draw_total_row(pdf, "Grand total", document.grand_total_cents, document.currency_code, bold=True)
    pdf.ln(6)


def _draw_terms(pdf: FPDF, document: CustomerQuoteDocument) -> None:
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(0, 7, _pdf_text("Terms and notes"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(70, 78, 92)
    pdf.multi_cell(0, 5, _pdf_text(document.terms))


def _draw_label_values(pdf: FPDF, rows: list[tuple[str, str]], *, x: int, width: int) -> None:
    for label, value in rows:
        pdf.set_x(x)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(90, 96, 110)
        pdf.cell(24, 6, _pdf_text(label))
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(20, 24, 31)
        pdf.multi_cell(width - 24, 6, _pdf_text(value))


def _draw_total_row(pdf: FPDF, label: str, amount_cents: int, currency_code: str, *, bold: bool) -> None:
    pdf.set_font("Helvetica", "B" if bold else "", 10)
    pdf.set_text_color(20, 24, 31)
    pdf.cell(130, 8, "")
    pdf.cell(25, 8, _pdf_text(label), align="R")
    pdf.cell(25, 8, _pdf_text(_money(amount_cents, currency_code)), align="R", new_x="LMARGIN", new_y="NEXT")


def _bucket_total(pricing_summary: dict[str, Any], buckets: set[str]) -> int:
    total = 0
    for row in _list(pricing_summary.get("bucket_totals")):
        if str(row.get("bucket") or "") in buckets:
            total += _positive_int(row.get("sell_total_cents"))
    return total


def _material_role_total(pricing_summary: dict[str, Any], material_role: str) -> int:
    material_summary = pricing_summary.get("material_summary")
    if not isinstance(material_summary, dict):
        return 0
    total = 0
    for row in _list(material_summary.get("groups")):
        if str(row.get("material_role") or "") == material_role:
            total += _positive_int(row.get("sell_total_cents"))
    return total


def _money(amount_cents: int, currency_code: str) -> str:
    amount = amount_cents / 100
    return f"{currency_code} {amount:,.2f}"


def _currency(value: str) -> str:
    cleaned = str(value or "").strip().upper()
    return cleaned if re.fullmatch(r"[A-Z]{3}", cleaned) else "ZAR"


def _text(value: Any, *, fallback: str) -> str:
    cleaned = str(value or "").strip()
    return cleaned or fallback


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _list(value: Any) -> list[dict[str, Any]]:
    return value if isinstance(value, list) else []


def _filename_part(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value.strip()).strip("-")
    return cleaned[:60]


def _initials(value: str) -> str:
    letters = [part[0].upper() for part in re.findall(r"[A-Za-z0-9]+", value)[:2]]
    return "".join(letters) or "CQ"


def _pdf_text(value: str) -> str:
    return value.encode("latin-1", "replace").decode("latin-1")
