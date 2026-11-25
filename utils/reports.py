
from fpdf import FPDF

def build_pdf_report(total_residents, total_households):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "BARANGAY HOUSEHOLD REPORT", ln=True)

    pdf.set_font("Arial", size=12)
    pdf.cell(0, 10, f"Total Residents: {total_residents}", ln=True)
    pdf.cell(0, 10, f"Total Households: {total_households}", ln=True)

    return bytes(pdf.output())
