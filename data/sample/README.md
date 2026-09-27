# Sample Data

**Do not commit real or full patient workbooks to this repository — private or not.**

This folder is for small, de-identified, or synthetically-generated snippets used for local
development and unit tests only (e.g. a handful of rows from one sheet, or a fully synthetic
mini-workbook you generate yourself).

The full 1,000-patient dataset lives in the shared Google Drive folder linked in the course
kickoff email. Download it there and keep it **outside** version control:

1. Create a local `data/raw/` folder (already gitignored).
2. Place the downloaded workbooks there.
3. Point notebooks/scripts at `data/raw/` via a config value or environment variable —
   never hardcode a path that assumes everyone's machine is laid out the same way.

If you need a shareable snippet for a bug report or a notebook example, generate a synthetic
one (e.g. with `faker` or hand-built fixtures) rather than trimming a real workbook.
