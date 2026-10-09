# ruff: noqa: E501
"""Tweede verkenning: metadata van GCC, waarden van coast_type_flag in onze landen, en een werkende manier om
het EMODnet-raster in blokken te downloaden (WCS 1.0.0 en 2.0.1, en de download-index)."""

from __future__ import annotations

import csv
import gzip
import io
import json
from collections import Counter

from pipeline.bodem.verken import OUT, get, probeer


def tekst(b: bytes) -> str:
    if b[:2] == b"\x1f\x8b":
        b = gzip.decompress(b)
    return b.decode("utf8", "replace")


def main() -> None:
    uit = {}
    uit["meta_data_yml"] = probeer(lambda: tekst(get("https://zenodo.org/api/records/11072020/files/meta_data.yml/content")))

    def gcc():
        b = get("https://zenodo.org/api/records/11072020/files/GCC_geophysical.csv/content", timeout=900)
        r = csv.DictReader(io.StringIO(b.decode("utf8")))
        ct, veg = Counter(), Counter()
        voorbeeld = []
        for row in r:
            lon, lat = float(row["lon"]), float(row["lat"])
            if 35 <= lat <= 52 and -10.5 <= lon <= 9.8:
                ct[row["coast_type_flag"]] += 1
                veg[row["veg_type"]] += 1
                if len(voorbeeld) < 5 and 51.3 < lat < 51.4 and 3.2 < lon < 3.4:
                    voorbeeld.append(row)
        return {"coast_type_flag": ct.most_common(), "veg_type": veg.most_common(), "knokke": voorbeeld}
    uit["gcc_waarden"] = probeer(gcc)

    w = "https://ows.emodnet-bathymetry.eu/wcs"
    uit["wcs10_caps"] = probeer(lambda: tekst(get(w + "?service=WCS&version=1.0.0&request=GetCapabilities"))[:4000])
    uit["wcs10_describe"] = probeer(lambda: tekst(get(w + "?service=WCS&version=1.0.0&request=DescribeCoverage&coverage=emodnet:mean"))[:4000])
    uit["wcs20_describe"] = probeer(lambda: tekst(get(w + "?service=WCS&version=2.0.1&request=DescribeCoverage&coverageId=emodnet__mean"))[:4000])

    def proef(url):
        def f():
            b = get(url, timeout=300)
            if not b.startswith((b"II*", b"MM\x00")):
                return {"geen_tiff": tekst(b)[:1500]}
            import numpy as np
            import rasterio
            with rasterio.MemoryFile(b) as m, m.open() as ds:
                a = ds.read(1)
                return {"bytes": len(b), "shape": a.shape, "crs": str(ds.crs), "transform": list(ds.transform)[:6],
                        "nodata": ds.nodata, "dtype": str(a.dtype), "min": float(np.nanmin(a)), "max": float(np.nanmax(a))}
        return probeer(f)
    uit["wcs10_proef"] = proef(w + "?service=WCS&version=1.0.0&request=GetCoverage&coverage=emodnet:mean&crs=EPSG:4326"
                               "&bbox=3.25,51.33,3.35,51.40&format=image/tiff&resx=0.0010416667&resy=0.0010416667")
    uit["wcs20_proef_klein"] = proef(w + "?service=WCS&version=2.0.1&request=GetCoverage&coverageId=emodnet__mean"
                                     "&format=image/tiff&subset=Lat(51.33,51.34)&subset=Long(3.25,3.26)")
    uit["wcs10_proef_1graad"] = proef(w + "?service=WCS&version=1.0.0&request=GetCoverage&coverage=emodnet:mean&crs=EPSG:4326"
                                      "&bbox=-9.5,38.5,-8.5,39.5&format=image/tiff&resx=0.0010416667&resy=0.0010416667")
    uit["downloads"] = probeer(lambda: tekst(get("https://downloads.emodnet-bathymetry.eu/v12/"))[:3000])
    uit["downloads_v11"] = probeer(lambda: tekst(get("https://downloads.emodnet-bathymetry.eu/v11/"))[:3000])
    uit["profiel"] = probeer(lambda: json.loads(get(
        "https://rest.emodnet-bathymetry.eu/depth_profile?geom=LINESTRING(-1.4380%2043.6650,-1.4600%2043.6670)")))

    out = OUT.with_name("verkenning2.json")
    out.write_text(json.dumps(uit, ensure_ascii=False, indent=1) + "\n")
    print(json.dumps(uit, ensure_ascii=False)[:20000])


if __name__ == "__main__":
    main()
