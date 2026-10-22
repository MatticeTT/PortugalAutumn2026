"""EOT20 (DGFI-TUM, CC BY 4.0) van SEANOE downloaden: alleen de ocean_tides, ook als ze in een zip in de zip zitten.

Gebruik: python -m pipeline.eot20 <doelmap>   (maakt <doelmap>/EOT20/ocean_tides/*.nc)
"""

import io
import pathlib
import re
import shutil
import sys
import urllib.request
import zipfile


def main(doel: pathlib.Path) -> None:
    pagina = urllib.request.urlopen("https://www.seanoe.org/data/00683/79489/", timeout=120).read().decode("utf-8", "ignore")
    links = sorted(set(re.findall(r"https://www\.seanoe\.org/data/00683/79489/data/\d+\.zip", pagina)))
    print("zips:", links)
    for url in links:
        pad = doel / "eot20.zip"
        doel.mkdir(exist_ok=True)
        with urllib.request.urlopen(url, timeout=1800) as r, open(pad, "wb") as f:
            shutil.copyfileobj(r, f)
        def zoek(z, diepte=0):
            """Alle ocean_tides-bestanden, ook in zips in de zip."""
            print("  " * diepte, z.namelist()[:20])
            uit = {}
            for n in z.namelist():
                if ("ocean_tides" in n or "_ocean_eot20" in n) and n.endswith(".nc"):
                    uit[pathlib.Path(n).name] = z.read(n)
                elif n.endswith(".zip") and "load" not in n.lower():
                    uit.update(zoek(zipfile.ZipFile(io.BytesIO(z.read(n))), diepte + 1))
            return uit
        gevonden = zoek(zipfile.ZipFile(pad))
        print(url, len(gevonden), "ocean_tides")
        pad.unlink()
        if gevonden:
            uit = doel / "EOT20" / "ocean_tides"
            uit.mkdir(parents=True, exist_ok=True)
            for n, b in gevonden.items():
                (uit / n).write_bytes(b)
            break
    else:
        raise SystemExit("Geen EOT20 ocean_tides gevonden")


if __name__ == "__main__":
    main(pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "getij"))
