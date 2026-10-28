from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from datetime import datetime

class PDFService:
    @staticmethod
    def generate_invoice(transaction_data):
        """
        Generate a PDF invoice for a transaction
        Returns: BytesIO buffer containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        
        # Header
        company_name = transaction_data.get('company_name', 'Aikrofy Service')
        elements.append(Paragraph(f"Invoice / Receipt", styles['Title']))
        elements.append(Paragraph(f"Company: {company_name}", styles['Normal']))
        elements.append(Paragraph(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Payment Info
        elements.append(Paragraph(f"Payment ID: {transaction_data.get('id')}", styles['Normal']))
        elements.append(Spacer(1, 12))
        
        # Table Details
        amount = transaction_data.get('amount', '0.00')
        currency = transaction_data.get('currency', 'USD')
        description = transaction_data.get('description', 'Service Payment')
        
        data = [
            ["Item / Description", "Amount"],
            [description, f"{amount} {currency}"]
        ]
        
        t = Table(data, colWidths=[300, 100])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(t)
        
        elements.append(Spacer(1, 24))
        elements.append(Paragraph("Thank you for your business!", styles['Italic']))
        
        # Build
        doc.build(elements)
        buffer.seek(0)
        return buffer
