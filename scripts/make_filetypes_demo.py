"""Make demo files in every supported format for one synthetic patient (PC8102): a PDF, Word, text, CSV, Excel and JSON
lab report, a photo-style scan (PNG, read with OCR), daily readings (Excel) and a clinic note (Word).
Run:  python scripts/make_filetypes_demo.py          (writes demo-files/filetypes/)
All data is synthetic."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

PID = "PC8102"
OUT = Path(__file__).resolve().parent.parent / "demo-files" / "filetypes"
# one lab report per collection date: (date, LDL cholesterol, Fasting glucose, HbA1c)
LABS = {"pdf": ("2026-01-10", 112, 96, 5.5), "docx": ("2026-02-14", 119, 99, 5.6), "txt": ("2026-03-14", 127, 103, 5.7),
        "csv": ("2026-04-11", 134, 107, 5.8), "xlsx": ("2026-05-16", 141, 111, 5.9), "json": ("2026-06-13", 149, 115, 6.0),
        "png": ("2026-06-20", 153, 117, 6.1)}


def rows(v):
    return [("LDL cholesterol", v[1], "mg/dL", "0-100"), ("Fasting glucose", v[2], "mg/dL", "70-99"), ("HbA1c", v[3], "%", "4.0-5.6")]


def text_lines(date, v):
    out = ["Laboratory report", f"Patient ID: {PID}", "Age: 52", "Sex: Female", f"Collection date: {date}", "", "Test Result Unit Reference Range"]
    return out + [f"{n} {val} {u} {r}" for n, val, u, r in rows(v)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for kind, v in LABS.items():
        date, lines = v[0], text_lines(v[0], v)
        stem = OUT / (f"lab_scan_{date}" if kind == "png" else f"lab_report_{date}")
        if kind == "pdf":
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            c = canvas.Canvas(str(stem.with_suffix(".pdf")), pagesize=A4)
            y = 800
            for ln in lines:
                c.drawString(60, y, ln); y -= 20
            c.save()
        elif kind == "docx":
            import docx
            d = docx.Document()
            for ln in lines:
                d.add_paragraph(ln)
            d.save(stem.with_suffix(".docx"))
        elif kind == "txt":
            stem.with_suffix(".txt").write_text("\n".join(lines) + "\n")
        elif kind in ("csv", "xlsx", "json"):
            df = pd.DataFrame([{"Patient ID": PID, "Date": date, "Test": n, "Result": val, "Unit": u, "Reference Range": r} for n, val, u, r in rows(v)])
            if kind == "csv":
                df.to_csv(stem.with_suffix(".csv"), index=False)
            elif kind == "xlsx":
                df.to_excel(stem.with_suffix(".xlsx"), index=False)
            else:
                stem.with_suffix(".json").write_text(json.dumps(df.to_dict("records"), indent=1))
        else:
            from PIL import Image, ImageDraw, ImageFont
            try:
                font = ImageFont.truetype("arial.ttf", 30)
            except OSError:
                try:
                    font = ImageFont.truetype("DejaVuSans.ttf", 30)
                except OSError:
                    font = ImageFont.load_default()
            img = Image.new("RGB", (1100, 40 + 46 * len(lines)), "white")
            dr = ImageDraw.Draw(img)
            for i, ln in enumerate(lines):
                dr.text((40, 30 + 46 * i), ln, fill="black", font=font)
            img.save(stem.with_suffix(".png"))
    rng = np.random.default_rng(5)
    d = pd.date_range("2026-01-01", periods=170)
    t = np.linspace(0, 1, 170)
    pd.DataFrame({"Patient ID": PID, "Date": d.strftime("%Y-%m-%d"), "Weight": np.round(74 + 4.5 * t + rng.normal(0, .3, 170), 1),
                  "Resting HR": np.round(68 + 6 * t + rng.normal(0, 1.2, 170)), "Steps": np.round(8200 - 2600 * t + rng.normal(0, 500, 170))}
                 ).to_excel(OUT / "daily_readings_jan_to_jun.xlsx", index=False)
    import docx
    n = docx.Document()
    for ln in ["Clinic note", f"Patient ID: {PID}", "Age: 52", "Sex: Female", "Visit date: 2026-06-20", "", "Diagnoses:",
               "- Prediabetes (2025-11-02)", "", "Medications:", "- Metformin 500 mg daily for prediabetes since 2026-01-05", "",
               "Notes:", "Weight and fasting glucose have crept up since the winter."]:
        n.add_paragraph(ln)
    n.save(OUT / "clinic_note_2026-06-20.docx")
    return sorted(p.name for p in OUT.iterdir())


if __name__ == "__main__":
    print("\n".join(main()))
