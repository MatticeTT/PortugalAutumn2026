"""M2: de officiële getijtabel 2026 (Instituto Hidrográfico) inlezen, alleen ter controle.

De tabel mag niet overgenomen worden (PLAN.md 3.2). Dit script downloadt de pdf in
GitHub Actions, haalt hoog- en laagwater per haven eruit en bewaart ze alleen in
data/raw/ (niet in git). In git komen enkel de verschillen met onze voorspelling.
"""

from __future__ import annotations

import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PDF_URL = "https://loja.hidrografico.pt/ln/web/wp-content/uploads/2023/11/TabelaMare_I_2026_signed.pdf"


def download() -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    dest = RAW / "tabela_mares_2026.pdf"
    if not dest.exists():
        req = urllib.request.Request(PDF_URL, headers={"User-Agent": "surfkaart-portugal/0.1 (controle)"})
        with urllib.request.urlopen(req, timeout=300) as r:
            dest.write_bytes(r.read())
    return dest


def to_text(pdf: Path) -> Path:
    txt = pdf.with_suffix(".txt")
    subprocess.run(["pdftotext", "-layout", str(pdf), str(txt)], check=True)
    return txt


if __name__ == "__main__":
    txt = to_text(download())
    lines = txt.read_text(errors="replace").splitlines()
    print(f"{len(lines)} regels")
    # Alleen voor de ontwikkeling van de parser: de havenkoppen en een kort stuk van een tabelpagina.
    def is_head(t: str) -> bool:
        return t.isupper() and t.replace(" ", "").replace("-", "").isalpha()

    heads = sorted({ln.strip() for ln in lines if is_head(ln.strip())})
    print("koppen:", len(heads))
    term = sys.argv[1] if len(sys.argv) > 1 else "PORTO DE CASCAIS"
    hits = [i for i, ln in enumerate(lines) if ln.strip() == term]
    print("regels met", term, hits[:20])
    if hits:
        j = next(i for i in range(hits[0], len(lines)) if lines[i].strip().startswith("JANEIRO"))
        for ln in lines[j - 4 : j + 16]:
            print("|" + ln)
