"""Turn any supported file into something the report readers understand: pages of text or a table.

Supported: PDF (text or scanned), images (PNG, JPG, TIFF, BMP, WEBP), DOCX, TXT, CSV, XLSX/XLSM/XLS, JSON (plain
tables) and FHIR bundles. Scans and photos are read with OCR when the OCR engine (Tesseract) is installed; values
read that way are flagged so the person can check them. Nothing is guessed here: unreadable files raise ReportError.
"""
import io
import json
import re

import pandas as pd

from .reports import ReportError

TEXT_EXT = (".pdf", ".txt", ".docx")
IMAGE_EXT = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp")
TABLE_EXT = (".csv", ".xlsx", ".xlsm", ".xls", ".json")
SUPPORTED = TEXT_EXT + IMAGE_EXT + TABLE_EXT
OCR_MISSING = ("This file is an image or a scan and needs OCR, but the OCR engine (Tesseract) is not installed on this server. "
               "Install Tesseract, or upload a PDF with selectable text, a CSV or an XLSX.")


def ext(filename: str) -> str:
    n = filename.lower()
    return n[n.rfind("."):] if "." in n else ""


def _ocr_image(img) -> str:
    try:
        import pytesseract
        text = pytesseract.image_to_string(img.convert("L"), config="--psm 6")
        text = re.sub(r"(?<=\d),(?=\d{1,2}\b)", ".", text)         # a decimal comma read from a scan
        text = re.sub(r"(?<=\d)\.(?=\s|$)", "", text)               # a stray full stop after a number ("107.")
        return "\n".join(l for l in text.splitlines() if l.strip())    # OCR adds blank lines between table rows
    except ImportError:
        raise ReportError(OCR_MISSING)
    except Exception as exc:
        if exc.__class__.__name__ == "TesseractNotFoundError":
            raise ReportError(OCR_MISSING)
        raise ReportError(f"Could not read the image ({str(exc)[:80]}).")


def _ocr_pdf(data: bytes):
    try:
        import pypdfium2 as pdfium
    except ImportError:
        raise ReportError(OCR_MISSING)
    try:
        pdf = pdfium.PdfDocument(data)
        return [_ocr_image(pdf[i].render(scale=2.5).to_pil()) for i in range(min(len(pdf), 12))]
    except ReportError:
        raise
    except Exception as exc:
        raise ReportError(f"Could not read the PDF ({str(exc)[:80]}).")


def _docx_text(data: bytes) -> str:
    try:
        from docx import Document
        doc = Document(io.BytesIO(data))
    except ImportError:
        raise ReportError("Word documents need the python-docx package on this server.")
    except Exception as exc:
        raise ReportError(f"Could not read the Word document ({str(exc)[:80]}).")
    body, lines = doc.element.body, []
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    for child in body.iterchildren():          # keep paragraphs and tables in document order
        if child.tag.endswith("}p"):
            lines.append(Paragraph(child, doc).text)
        elif child.tag.endswith("}tbl"):
            for row in Table(child, doc).rows:
                cells, seen = [], []
                for c in row.cells:
                    if c._tc not in seen:
                        seen.append(c._tc)
                        cells.append(c.text.strip().replace("\n", " "))
                lines.append("  ".join(cells))
    return "\n".join(lines)


def text_pages(filename: str, data: bytes):
    """-> (pages of text, read_by_ocr). Raises ReportError for files that are not text-like."""
    e = ext(filename)
    if e == ".pdf":
        try:
            from pypdf import PdfReader
            pages = [(pg.extract_text(extraction_mode="layout") or "") for pg in PdfReader(io.BytesIO(data)).pages]
        except Exception as exc:
            raise ReportError(f"Could not read the PDF ({str(exc)[:80]}).")
        if len("".join(pages).strip()) >= 20:
            return pages, False
        return _ocr_pdf(data), True          # a scan: no selectable text
    if e == ".txt":
        text = data.decode("utf-8", errors="replace")
        if not text.strip():
            raise ReportError("The text file is empty.")
        return [text], False
    if e == ".docx":
        return [_docx_text(data)], False
    if e in IMAGE_EXT:
        try:
            from PIL import Image
            img = Image.open(io.BytesIO(data))
        except ImportError:
            raise ReportError(OCR_MISSING)
        except Exception as exc:
            raise ReportError(f"Could not open the image ({str(exc)[:80]}).")
        return [_ocr_image(img)], True
    raise ReportError("Not a document with text.")


def _json_table(obj):
    if isinstance(obj, dict):
        for k in ("results", "records", "data", "rows", "items", "labs", "readings"):
            if isinstance(obj.get(k), list):
                obj = obj[k]
                break
        else:
            obj = [obj]
    if not isinstance(obj, list) or not obj or not all(isinstance(r, dict) for r in obj):
        raise ReportError("The JSON file is not a list of records or a FHIR bundle.")
    return pd.json_normalize(obj)


def load_json(data: bytes):
    try:
        return json.loads(data.decode("utf-8-sig"))
    except Exception as exc:
        raise ReportError(f"Could not read the JSON file ({str(exc)[:80]}).")


def is_fhir(obj) -> bool:
    return isinstance(obj, dict) and obj.get("resourceType") in ("Bundle", "Observation", "Condition", "MedicationRequest", "MedicationStatement", "Patient")


def table_of(filename: str, data: bytes) -> pd.DataFrame:
    e = ext(filename)
    try:
        if e == ".csv":
            return pd.read_csv(io.BytesIO(data))
        if e in (".xlsx", ".xlsm"):
            return pd.read_excel(io.BytesIO(data))
        if e == ".xls":
            return pd.read_excel(io.BytesIO(data), engine="xlrd")
        if e == ".json":
            return _json_table(load_json(data))
    except ReportError:
        raise
    except ImportError:
        raise ReportError("Old Excel (.xls) files need the xlrd package on this server.")
    except Exception as exc:
        raise ReportError(f"Could not read the file ({str(exc)[:80]}).")
    raise ReportError("Not a table.")
