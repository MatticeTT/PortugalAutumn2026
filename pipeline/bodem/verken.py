"""Verkenning van de bodembronnen (vanuit GitHub Actions; de sandbox kan ze niet bereiken).

- EMODnet Bathymetry: depth_sample op enkele punten (zee, strand, land) om het teken en het referentievlak te zien,
  en de WCS-beschrijving (rasterpunten, eenheid, nodata) voor het lokale uitlezen.
- Global Coastal Characteristics (Zenodo 8200199): de bestandslijst, en de kolomnamen en eerste regels van elk CSV-bestand.
Schrijft data/beaches/bodem/verkenning.json.
"""

from __future__ import annotations

import io
import json
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "beaches" / "bodem" / "verkenning.json"
UA = {"User-Agent": "surfkaart-portugal/0.1 (niet-commercieel, besloten)"}


def get(url: str, n: int | None = None, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read(n) if n else r.read()


def probeer(f):
    try:
        return f()
    except Exception as e:  # noqa: BLE001
        return {"fout": f"{type(e).__name__}: {e}"[:400]}


def main() -> None:
    uit: dict = {}
    punten = {"knokke_strand": (3.308944, 51.358653), "knokke_zee_2km": (3.30, 51.375),
              "noordzee_diep": (2.5, 51.6), "nazare_zee": (-9.10, 39.60), "brussel_land": (4.35, 50.85),
              "hossegor_zee_1km": (-1.457, 43.665)}
    uit["depth_sample"] = {k: probeer(lambda p=p: json.loads(get(
        f"https://rest.emodnet-bathymetry.eu/depth_sample?geom=POINT({p[0]}%20{p[1]})")))
        for k, p in punten.items()}
    uit["depth_profile"] = probeer(lambda: json.loads(get(
        "https://rest.emodnet-bathymetry.eu/depth_profile?geom=LINESTRING(3.3089%2051.3587,3.30%2051.375)")))
    uit["wcs_capabilities"] = probeer(lambda: get(
        "https://ows.emodnet-bathymetry.eu/wcs?service=WCS&version=2.0.1&request=GetCapabilities", 6000).decode("utf8", "replace"))
    uit["wcs_describe"] = probeer(lambda: get(
        "https://ows.emodnet-bathymetry.eu/wcs?service=WCS&version=2.0.1&request=DescribeCoverage&coverageId=emodnet__mean",
        8000).decode("utf8", "replace"))
    # klein proefstuk als GeoTIFF rond Knokke
    def tif():
        b = get("https://ows.emodnet-bathymetry.eu/wcs?service=WCS&version=2.0.1&request=GetCoverage"
                "&coverageId=emodnet__mean&format=image/tiff&subset=Lat(51.33,51.40)&subset=Long(3.25,3.35)")
        import numpy as np
        import rasterio
        with rasterio.MemoryFile(b) as m, m.open() as ds:
            a = ds.read(1)
            return {"bytes": len(b), "shape": a.shape, "crs": str(ds.crs), "transform": list(ds.transform)[:6],
                    "nodata": ds.nodata, "dtype": str(a.dtype), "min": float(np.nanmin(a)), "max": float(np.nanmax(a)),
                    "rij_midden": [float(x) for x in a[a.shape[0] // 2][::8]]}
    uit["wcs_proef"] = probeer(tif)

    def zen():
        rec = json.loads(get("https://zenodo.org/api/records/8200199"))
        files = [{"key": f["key"], "size": f["size"], "url": f["links"]["self"]} for f in rec.get("files", [])]
        meta = {k: rec["metadata"].get(k) for k in ("title", "version", "license", "publication_date", "doi")}
        meta["description"] = (rec["metadata"].get("description") or "")[:3000]
        return {"meta": meta, "files": files, "latest": rec.get("links", {}).get("latest")}
    z = probeer(zen)
    uit["zenodo"] = z
    voorbeelden = {}
    for f in (z.get("files") or []) if isinstance(z, dict) else []:
        key = f["key"].lower()
        if key.endswith((".csv", ".txt", ".md")):
            voorbeelden[f["key"]] = probeer(lambda f=f: get(f["url"], 4000).decode("utf8", "replace"))
        elif key.endswith((".xlsx", ".pdf")) and f["size"] < 5_000_000:
            def lees(f=f):
                b = get(f["url"])
                if key.endswith(".xlsx"):
                    import openpyxl
                    wb = openpyxl.load_workbook(io.BytesIO(b), read_only=True)
                    return {ws.title: [[str(c) for c in r] for r in ws.iter_rows(values_only=True)][:120]
                            for ws in wb.worksheets}
                return {"bytes": len(b)}
            voorbeelden[f["key"]] = probeer(lees)
        elif key.endswith(".zip") and f["size"] < 400_000_000:
            def zipkop(f=f):
                zf = zipfile.ZipFile(io.BytesIO(get(f["url"], timeout=600)))
                kop = {}
                for n in zf.namelist()[:40]:
                    if n.lower().endswith((".csv", ".txt")):
                        with zf.open(n) as h:
                            kop[n] = h.read(3000).decode("utf8", "replace")
                return {"namen": zf.namelist()[:200], "koppen": kop}
            voorbeelden[f["key"]] = probeer(zipkop)
    uit["zenodo_inhoud"] = voorbeelden
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(uit, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(uit, ensure_ascii=False)[:20000])


if __name__ == "__main__":
    main()
