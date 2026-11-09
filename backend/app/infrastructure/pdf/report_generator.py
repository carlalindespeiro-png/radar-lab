import uuid
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

class ReportGenerator:
    def __init__(self, output_dir: str = None):
        if output_dir:
            self.output_dir = Path(output_dir).resolve()
        else:
            # Sube 3 niveles: pdf -> infrastructure -> app -> backend
            backend_root = Path(__file__).resolve().parents[3]
            self.output_dir = backend_root / "data" / "reports"
            
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _validate_data(self, data: dict):
        if not isinstance(data, dict):
            raise ValueError("Los datos de la oportunidad deben ser un diccionario.")
        
        required_keys = {"problem_name", "score_total", "score_breakdown", "evidences"}
        if not required_keys.issubset(data.keys()):
            raise ValueError(f"Faltan claves obligatorias en los datos: {required_keys - data.keys()}")
            
        if not isinstance(data["problem_name"], str) or not data["problem_name"].strip():
            raise ValueError("El campo 'problem_name' debe ser un texto no vacío.")
            
        if not isinstance(data["score_total"], (int, float)):
            raise ValueError("El campo 'score_total' debe ser numérico.")
            
        if not isinstance(data["evidences"], list):
            raise ValueError("El campo 'evidences' debe ser una lista.")

        for i, ev in enumerate(data["evidences"]):
            if not isinstance(ev, dict) or "text" not in ev or "source_url" not in ev:
                raise ValueError(f"Evidencia {i} mal formada. Debe contener 'text' y 'source_url'.")
            
            url = ev["source_url"]
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError(f"URL inválida en evidencia {i}: '{url}'. Debe tener esquema http/https y un dominio válido.")

    def generate_pdf(self, research_run_id: int, opportunity_data: dict) -> str:
        self._validate_data(opportunity_data)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = uuid.uuid4().hex[:8]
        filename = f"report_run_{research_run_id}_{timestamp}_{unique_id}.pdf"
        filepath = self.output_dir / filename
        
        doc = SimpleDocTemplate(
            str(filepath), 
            pagesize=A4, 
            rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50
        )
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], spaceAfter=20)
        normal_style = styles['Normal']
        elements = []
        
        elements.append(Paragraph("RADAR LAB — Informe de Oportunidad", title_style))
        elements.append(Paragraph(f"ID de Investigación: {research_run_id}", normal_style))
        elements.append(Paragraph(f"Fecha de generación: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 20))
        
        elements.append(Paragraph("1. Problema Detectado", styles['Heading2']))
        problem_text = escape(str(opportunity_data['problem_name']))
        elements.append(Paragraph(problem_text, normal_style))
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("2. Índice de Madurez de la Oportunidad", styles['Heading2']))
        score = opportunity_data['score_total']
        elements.append(Paragraph(f"<b>Puntuación Total:</b> {score}/100", normal_style))
        
        breakdown = opportunity_data.get('score_breakdown', {})
        if breakdown:
            data = [["Indicador", "Puntuación"]]
            for k, v in breakdown.items():
                data.append([k.capitalize(), str(v)])
            
            table = Table(data, colWidths=[200, 100])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
            ]))
            elements.append(table)
        elements.append(Spacer(1, 10))
        
        elements.append(Paragraph("3. Evidencias Recopiladas", styles['Heading2']))
        for i, ev in enumerate(opportunity_data['evidences'], 1):
            ev_text = escape(str(ev.get('text', '')))
            ev_url = escape(str(ev.get('source_url', '')))
            elements.append(Paragraph(f"<b>Evidencia {i}:</b> \"{ev_text}\"", normal_style))
            elements.append(Paragraph(f"<i>Fuente:</i> {ev_url}", normal_style))
            elements.append(Spacer(1, 5))
                
        doc.build(elements)
        return str(filepath)