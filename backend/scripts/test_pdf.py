import sys
from pathlib import Path

_backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_backend_dir))

from app.infrastructure.pdf.report_generator import ReportGenerator
from pypdf import PdfReader

def test_valid_pdf():
    print("\n--- Test 1: Generación y validación de PDF válido ---")
    mock_opportunity = {
        "problem_name": "Falta de coordinación <y> errores en reparaciones", 
        "score_total": 87,
        "score_breakdown": {"quality": 100, "intensity": 100},
        "evidences": [
            {
                "text": "Los técnicos pierden 5 horas a la semana.",
                "source_url": "https://ejemplo.com/foro-tecnicos"
            }
        ]
    }
    
    generator = ReportGenerator()
    ruta_pdf = generator.generate_pdf(research_run_id=1, opportunity_data=mock_opportunity)
    
    pdf_path = Path(ruta_pdf).resolve()
    assert pdf_path.exists(), f"El archivo no existe: {pdf_path}"
    assert "backend" in pdf_path.parts, "La ruta no pasa por backend/"
    assert "reports" in pdf_path.parts, "La ruta no termina en reports/"
    assert pdf_path.suffix == ".pdf", "El archivo no es un PDF"
    
    try:
        reader = PdfReader(str(pdf_path))
        assert len(reader.pages) >= 1, "El PDF no tiene páginas."
    except Exception as e:
        raise AssertionError(f"Error al abrir el PDF con pypdf: {e}")
        
    texto = "".join(page.extract_text() for page in reader.pages)
    
    assert "Falta de coordinación <y> errores en reparaciones" in texto, "No se encontró el problema en el PDF."
    assert "Los técnicos pierden 5 horas a la semana." in texto, "No se encontró la evidencia en el PDF."
    assert "Puntuación Total: 87/100" in texto, "No se encontró la puntuación."
    
    print(f"  [OK] PDF generado en: {pdf_path}")
    print(f"  [OK] Páginas: {len(reader.pages)}")
    print("  [OK] Contenido y escapado XML verificados.")

def test_invalid_url():
    print("\n--- Test 2: Validación de URL inválida ---")
    mock_invalid = {
        "problem_name": "Problema test",
        "score_total": 50,
        "score_breakdown": {},
        "evidences": [
            {"text": "Texto", "source_url": "ftp://servidor-invalido"} 
        ]
    }
    
    generator = ReportGenerator()
    try:
        generator.generate_pdf(research_run_id=2, opportunity_data=mock_invalid)
        raise AssertionError("Fallo: El generador aceptó una URL con esquema inválido.")
    except ValueError as e:
        if "URL inválida" in str(e):
            print(f"  [OK] Rechazo correcto de URL inválida: {e}")
        else:
            raise

def test_missing_data():
    print("\n--- Test 3: Validación de datos incompletos ---")
    mock_missing = {
        "problem_name": "Problema test",
    }
    
    generator = ReportGenerator()
    try:
        generator.generate_pdf(research_run_id=3, opportunity_data=mock_missing)
        raise AssertionError("Fallo: El generador aceptó datos incompletos.")
    except ValueError as e:
        if "Faltan claves" in str(e):
            print(f"  [OK] Rechazo correcto de datos incompletos: {e}")
        else:
            raise

def main():
    print("=== PRUEBAS DE GENERACIÓN DE PDF (Fase 4.5.3) ===")
    try:
        test_valid_pdf()
        test_invalid_url()
        test_missing_data()
        print("\n=== TODAS LAS PRUEBAS DE PDF PASARON ===")
    except AssertionError as e:
        print(f"\n[FALLO] {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()