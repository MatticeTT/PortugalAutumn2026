"""M2: de officiële getijtabel 2026 (Instituto Hidrográfico) inlezen, alleen ter controle.

De tabel mag niet overgenomen worden (PLAN.md 3.2). Dit script downloadt de pdf in
GitHub Actions en haalt per hoofdhaven hoog- en laagwater eruit, in het geheugen of in
data/raw/ (niet in git). In git komen alleen de verschillen met onze voorspelling.

Opbouw van een tabelpagina (pdftotext -layout):

    Horas do Fuso: 0 (TU)                                   Ano: 2026
                   JANEIRO              FEVEREIRO              MARÇO
           Hora    Altura   Hora Altura   Hora Altura ...       (6 kolommen)
           00:09    3.1     01:36  3.1    ...
    01     06:26    0.9  17 07:52  1.1    ...                  (dagnummer)
           12:39    3.1  SÁB 13:59 2.9    ...                  (weekdag)
           18:47    0.9     19:56  1.1    ...

Per maand twee kolommen: dag 1 tot 16 en dag 17 tot 31. Een lege regel sluit een dag af.
"""

from __future__ import annotations

import re
import subprocess
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
PDF_URL = "https://loja.hidrografico.pt/ln/web/wp-content/uploads/2023/11/TabelaMare_I_2026_signed.pdf"
YEAR = 2026

# Hoofdhavens van het vasteland, zoals ze in de tabel heten.
PORTS = {
    "VIANA DO CASTELO": "viana_do_castelo", "LEIXÕES": "leixoes", "AVEIRO": "aveiro",
    "FIGUEIRA DA FOZ": "figueira_da_foz", "PENICHE": "peniche", "CASCAIS": "cascais", "LISBOA": "lisboa",
    "SESIMBRA": "sesimbra", "SINES": "sines", "LAGOS": "lagos", "FARO-OLHÃO": "faro_olhao",
    "VILA REAL DE SANTO ANTÓNIO": "vila_real_santo_antonio",
}
ISLANDS = {"FUNCHAL", "PORTO SANTO", "PONTA DELGADA", "ANGRA DO HEROÍSMO", "HORTA", "LAJES DAS FLORES",
           "VILA DO PORTO", "SANTA CRUZ DAS FLORES"}
MONTHS = {"JANEIRO": 1, "FEVEREIRO": 2, "MARÇO": 3, "ABRIL": 4, "MAIO": 5, "JUNHO": 6, "JULHO": 7,
          "AGOSTO": 8, "SETEMBRO": 9, "OUTUBRO": 10, "NOVEMBRO": 11, "DEZEMBRO": 12}

TIME_H = re.compile(r"(\d{2}):(\d{2})\s+(-?\d+[.,]\d)")
DAY = re.compile(r"(?<![\d:.,])(\d{2})(?![\d:.,])")


@dataclass
class Port:
    key: str
    name: str
    lat: float | None = None
    lon: float | None = None
    nivel_medio: float | None = None
    events: list[tuple[datetime, float]] = field(default_factory=list)


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


def port_name(line: str) -> str | None:
    t = line.strip()
    t = re.sub(r"^(PORTO D[AEO]|BARRA DE)\s+", "", t)
    if t in PORTS or t in ISLANDS:
        return t
    return None


def dms(deg: str, minutes: str) -> float:
    return float(deg) + float(minutes.replace(",", ".")) / 60


def parse(text: str) -> dict[str, Port]:
    ports: dict[str, Port] = {}
    cur: Port | None = None
    months: list[int] = []
    cols: list[int] = []          # tekenpositie van elke kolom "Hora"
    group: dict[int, dict] = {}   # kolom -> {"day": int|None, "events": [(h, m, height)]}

    def flush():
        if cur is None or not months or not cols:
            group.clear()
            return
        for c, g in group.items():
            if g["day"] is None or not g["events"]:
                continue
            month = months[min(c // 2, len(months) - 1)]
            for hh, mm, h in g["events"]:
                try:
                    t = datetime(YEAR, month, g["day"], int(hh), int(mm), tzinfo=UTC)
                except ValueError:
                    continue
                cur.events.append((t, h))
        group.clear()

    for line in text.splitlines():
        name = port_name(line)
        if name:
            flush()
            if name in ISLANDS:
                cur = None
            else:
                cur = ports.setdefault(name, Port(PORTS[name], name))
            months, cols = [], []
            continue
        if cur is None:
            continue
        if m := re.search(r"N[íi]vel m[ée]dio:\s*([\d,\.]+)\s*m", line):
            cur.nivel_medio = cur.nivel_medio or float(m.group(1).replace(",", "."))
        if m := re.search(r"Latitude\s+(\d+)[º°]\s*([\d.,]+)'?\s*N\s+Longitude\s+(\d+)[º°]\s*([\d.,]+)'?\s*W", line):
            cur.lat = dms(m.group(1), m.group(2))
            cur.lon = -dms(m.group(3), m.group(4))
        words = line.split()
        if words and all(w in MONTHS for w in words) and len(words) >= 2:
            flush()
            months = [MONTHS[w] for w in words]
            cols = []
            continue
        if "Hora" in line and "Altura" in line:
            cols = [m.start() for m in re.finditer(r"Hora", line)]
            continue
        if not line.strip():
            flush()
            continue
        if not cols:
            continue
        matches = list(TIME_H.finditer(line))
        if not matches:
            continue

        def col_of(pos: int) -> int:
            return max([k for k, c in enumerate(cols) if pos >= c - 4] or [0])

        for m in matches:
            c = col_of(m.start())
            g = group.setdefault(c, {"day": None, "events": []})
            g["events"].append((m.group(1), m.group(2), float(m.group(3).replace(",", "."))))
        # Dagnummers: twee cijfers links van een tijd, niet zelf een tijd.
        spans = [(m.start(), m.end()) for m in matches]
        for d in DAY.finditer(line):
            if any(a <= d.start() < b for a, b in spans):
                continue
            nxt = next((m for m in matches if m.start() > d.end()), None)
            if nxt is None:
                continue
            c = col_of(nxt.start())
            day = int(d.group(1))
            if 1 <= day <= 31:
                group.setdefault(c, {"day": None, "events": []})["day"] = day
    flush()
    for p in ports.values():
        p.events = sorted(set(p.events))
    return ports


def classify(port: Port) -> list[tuple[datetime, float, bool]]:
    """Hoog of laag: hoger dan beide buren is hoog."""
    ev = port.events
    out = []
    for i, (t, h) in enumerate(ev):
        prev_h = ev[i - 1][1] if i > 0 else None
        next_h = ev[i + 1][1] if i + 1 < len(ev) else None
        ref = [x for x in (prev_h, next_h) if x is not None]
        out.append((t, h, all(h > r for r in ref)))
    return out


def load() -> dict[str, Port]:
    return parse(to_text(download()).read_text(errors="replace"))


if __name__ == "__main__":
    for p in load().values():
        ev = p.events
        print(f"{p.name}: {len(ev)} extremen, nível médio {p.nivel_medio}, {p.lat}, {p.lon}, "
              f"{ev[0][0]:%m-%d} tot {ev[-1][0]:%m-%d}" if ev else f"{p.name}: geen extremen")
