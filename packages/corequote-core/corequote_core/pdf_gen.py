from fpdf import FPDF
import pandas as pd


class CutlistPDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Core Quotes - Cut List', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def _draw_table(pdf: FPDF, df: pd.DataFrame, title: str, has_unit_col: bool = False):
    """Render a titled table from a DataFrame."""
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 10, title, 0, 1, 'L')

    pdf.set_font('Arial', 'B', 10)
    if has_unit_col:
        pdf.cell(20, 8, 'Unit #', 1)
        pdf.cell(70, 8, 'Description', 1)
    else:
        pdf.cell(90, 8, 'Description', 1)
    pdf.cell(30, 8, 'Length (mm)', 1)
    pdf.cell(30, 8, 'Width (mm)', 1)
    pdf.cell(20, 8, 'Qty', 1)
    pdf.ln()

    pdf.set_font('Arial', '', 10)
    for _, row in df.iterrows():
        if has_unit_col:
            pdf.cell(20, 8, str(row['Unit #']), 1)
            pdf.cell(70, 8, str(row['Desc']), 1)
        else:
            pdf.cell(90, 8, str(row['Desc']), 1)
        pdf.cell(30, 8, str(row['L']), 1)
        pdf.cell(30, 8, str(row['W']), 1)
        pdf.cell(20, 8, str(row['Qty']), 1)
        pdf.ln()

    pdf.ln(8)


def generate_pdf(carcass_df: pd.DataFrame, panels_df: pd.DataFrame,
                 filename: str = "cutlist.pdf",
                 project_name: str = "", quote_name: str = "") -> bytes:
    """
    Generate a PDF cutlist.
    If the DataFrames contain a 'Unit #' column the table will include it.
    """
    pdf = CutlistPDF()
    pdf.add_page()

    # Optional project / quote header
    if project_name or quote_name:
        pdf.set_font('Arial', '', 11)
        if project_name:
            pdf.cell(0, 8, f'Project: {project_name}', 0, 1, 'L')
        if quote_name:
            pdf.cell(0, 8, f'Quote: {quote_name}', 0, 1, 'L')
        pdf.ln(4)

    has_unit_col = 'Unit #' in carcass_df.columns

    if not carcass_df.empty:
        _draw_table(pdf, carcass_df, 'Carcass Components', has_unit_col=has_unit_col)

    if not panels_df.empty:
        _draw_table(pdf, panels_df, 'Panels (Doors / Drawer Fronts)',
                    has_unit_col=('Unit #' in panels_df.columns))

    return pdf.output()
