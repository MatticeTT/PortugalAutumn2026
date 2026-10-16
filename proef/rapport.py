"""Uitvoer van de proef: stations_resolved.csv, <spot>.md/.csv, summary.md/.csv, horizon.png, run_log.md."""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .fouten import afstand_km
from .spots import SPOTS

NAMEN = {
    "wind_kn": "Windsnelheid (kn)", "windrichting": "Windrichting (°)", "vlaag_kn": "Windvlagen (kn)",
    "hs_m": "Golfhoogte (m)", "tp_s": "Piekperiode (s)", "tm_s": "Gemiddelde periode (s)",
    "golfrichting": "Golfrichting (°)", "sst_c": "Watertemperatuur (°C)",
}
HORIZON_VOLGORDE = {"1 dag": 1, "3 dagen": 3, "5 dagen": 5, "kort": 0}
GROEPNAAM = {"golf": "golven", "wind": "wind", "sst": "watertemperatuur"}
KOLOMMEN = ["variabele", "model", "horizon", "n", "dekking_pct", "bias", "mae", "rmse", "r", "trefkans_pct"]


def _rond(x, nd=4):
    return None if x is None else round(float(x), nd)


def station_rij(spot, groep: str, info: dict | None, status: str) -> dict:
    info = info or {}
    afst = info.get("afstand_km")
    return {
        "spot": spot.naam, "groep": groep, "meetpunt": info.get("id", "geen meting"),
        "soort": info.get("soort", ""), "lat": _rond(info.get("lat")), "lon": _rond(info.get("lon")),
        "afstand_km": round(afst, 1) if afst is not None else None,
        "dekking_pct": info.get("dekking_pct"), "status": status,
    }


def schrijf_stations(out: Path, rijen: list[dict]):
    df = pd.DataFrame(rijen)
    df["groep"] = df.groep.map(GROEPNAAM)
    df.to_csv(out / "stations_resolved.csv", index=False)


def _km(a, b):
    if not a or a.get("lat") is None or not b or b.get("cel_lat") is None:
        return None
    return round(float(afstand_km(a["lat"], a["lon"], b["cel_lat"], b["cel_lon"])), 1)


def spotkop(spot, r: dict, cellen: dict) -> dict:
    kop = {}
    for groep in ("wind", "golf", "sst"):
        m = r[groep]
        if not m:
            kop[groep] = {"meetpunt": "geen meting"}
            continue
        cel = {k: _km(m, v) for k, v in cellen.get(groep, {}).items()}
        kop[groep] = {"meetpunt": m["id"], "soort": m.get("soort", ""), "afstand_strand_km": round(m["afstand_km"], 1),
                      "dekking_pct": m["dekking_pct"], "cel_km": cel, "opmerking": m.get("opmerking", "")}
    return kop


def _fmt(x, nd=2):
    if x is None or (isinstance(x, float) and pd.isna(x)):
        return "—"
    return f"{x:.{nd}f}"


def _sorteer(df: pd.DataFrame) -> pd.DataFrame:
    volg = {k: i for i, k in enumerate(NAMEN)}
    return df.assign(_v=df.variabele.map(volg), _h=df.horizon.map(HORIZON_VOLGORDE)) \
             .sort_values(["_v", "model", "_h"]).drop(columns=["_v", "_h"])


def schrijf_spot(out: Path, spot, kop: dict, fouten: list[dict]):
    df = pd.DataFrame(fouten, columns=["spot", "slug"] + KOLOMMEN)
    if not df.empty:
        df = _sorteer(df)
    df[KOLOMMEN].to_csv(out / f"{spot.slug}.csv", index=False)
    regels = [f"# {spot.naam}", "", f"Positie strand {spot.lat:.3f}, {spot.lon:.3f} · sport: {spot.sport} · september 2026, UTC", ""]
    for groep in ("wind", "golf", "sst"):
        k = kop[groep]
        if k["meetpunt"] == "geen meting":
            regels.append(f"- **{GROEPNAAM[groep].capitalize()}**: geen meting")
            continue
        cel = ", ".join(f"{m} {_fmt(v, 1)} km" for m, v in k["cel_km"].items()) or "—"
        regels.append(f"- **{GROEPNAAM[groep].capitalize()}**: {k['meetpunt']} ({k['soort']}), "
                      f"{k['afstand_strand_km']} km van het strand, dekking {k['dekking_pct']}%. "
                      f"Rastercel ↔ meetpunt: {cel}." + (f" {k['opmerking']}." if k["opmerking"] else ""))
    regels += ["", "Bias = gemiddelde van voorspelling − meting. Richtingen: kortste hoekverschil; windrichting enkel bij ≥ 5 kn gemeten wind.", ""]
    if df.empty:
        regels.append("Geen fouttabel: geen meting voor deze spot.")
    else:
        regels.append("| Variabele | Model | Horizon | n | Dekking % | Bias | MAE | RMSE | r | Trefkans % |")
        regels.append("|---|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for _, x in df.iterrows():
            regels.append(f"| {NAMEN[x.variabele]} | {x.model} | {x.horizon} | {x.n} | {_fmt(x.dekking_pct, 1)} | "
                          f"{_fmt(x.bias)} | {_fmt(x.mae)} | {_fmt(x.rmse)} | {_fmt(x.r)} | {_fmt(x.trefkans_pct, 0)} |")
    (out / f"{spot.slug}.md").write_text("\n".join(regels) + "\n")


def beste(df: pd.DataFrame, variabele: str):
    """Laagste MAE op 1 dag vooruit (wind) of korte horizon (golven, watertemperatuur)."""
    h = "1 dag" if variabele in ("wind_kn", "windrichting", "vlaag_kn") else "kort"
    x = df[(df.variabele == variabele) & (df.horizon == h) & (df.n > 0)]
    if x.empty:
        return None
    return x.loc[x.mae.idxmin()]


def schrijf_overzicht(out: Path, fouten: list[dict], res: dict):
    df = pd.DataFrame(fouten, columns=["spot", "slug"] + KOLOMMEN)
    rijen = []
    for s in SPOTS:
        d = df[df.slug == s.slug]
        rij = {"spot": s.naam}
        for var in NAMEN:
            b = beste(d, var) if not d.empty else None
            if b is None:
                rij[f"{var}_mae"] = "geen meting"
                rij[f"{var}_model"] = "geen meting"
                rij[f"{var}_n"] = 0
            else:
                rij[f"{var}_mae"] = round(float(b.mae), 2)
                rij[f"{var}_model"] = b.model
                rij[f"{var}_n"] = int(b.n)
        rijen.append(rij)
    tab = pd.DataFrame(rijen)
    tab.to_csv(out / "summary.csv", index=False)

    regels = ["# Overzicht proef september 2026", "",
              "MAE van het beste model per variabele: wind op 1 dag vooruit, golven en watertemperatuur op korte horizon. "
              "Tussen haakjes het model en n (geldige uren). Per spot de volledige tabel in <spot>.md.", ""]
    regels.append("| Spot | " + " | ".join(NAMEN.values()) + " |")
    regels.append("|---|" + "---|" * len(NAMEN))
    for r in rijen:
        cellen = []
        for var in NAMEN:
            if r[f"{var}_mae"] == "geen meting":
                cellen.append("geen meting")
            else:
                cellen.append(f"{r[f'{var}_mae']:.2f} ({r[f'{var}_model']}, n={r[f'{var}_n']})")
        regels.append(f"| {r['spot']} | " + " | ".join(cellen) + " |")
    (out / "summary.md").write_text("\n".join(regels) + "\n")


def schrijf_grafiek(out: Path, fouten: list[dict], model: str = "best_match"):
    """MAE windsnelheid tegen horizon, één lijn per spot. Eén kleur; de spot staat als label aan het eind van de lijn."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    df = pd.DataFrame(fouten, columns=["spot", "slug"] + KOLOMMEN)
    df = df[(df.variabele == "wind_kn") & (df.model == model) & (df.horizon != "kort") & (df.n > 0)]
    fig, ax = plt.subplots(figsize=(8, 5.5), dpi=150)
    fig.patch.set_facecolor("#ffffff")
    inkt, zacht, lijn = "#1f2328", "#59636e", "#2f6fb0"
    eindes = []
    for spot, d in df.groupby("spot"):
        d = d.assign(h=d.horizon.map(HORIZON_VOLGORDE)).sort_values("h")
        ax.plot(d.h, d.mae, color=lijn, lw=2, marker="o", ms=4, alpha=0.85)
        eindes.append((float(d.mae.iloc[-1]), int(d.h.iloc[-1]), spot))
    # Labels rechts, uit elkaar geschoven zodat ze niet overlappen.
    eindes.sort()
    stap = (max([e[0] for e in eindes], default=1) - min([e[0] for e in eindes], default=0)) / 28 or 0.1
    vorige = -1e9
    for y, x, spot in eindes:
        y_label = max(y, vorige + stap)
        vorige = y_label
        ax.annotate(spot.split(",")[0], (x, y), xytext=(x + 0.15, y_label), fontsize=7.5, color=zacht,
                    va="center", arrowprops=dict(arrowstyle="-", color="#c8ced6", lw=0.6))
    ax.set_xticks([1, 3, 5], ["1 dag", "3 dagen", "5 dagen"])
    ax.set_xlim(0.8, 6.6)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("MAE windsnelheid (kn)", color=inkt)
    ax.set_title(f"Fout op windsnelheid per horizon · {model} · september 2026", color=inkt, fontsize=11, loc="left")
    ax.grid(axis="y", color="#e6e9ed", lw=0.8)
    for kant in ("top", "right"):
        ax.spines[kant].set_visible(False)
    for kant in ("left", "bottom"):
        ax.spines[kant].set_color("#c8ced6")
    ax.tick_params(colors=zacht)
    if df.empty:
        ax.text(3, 0.5, "geen windmetingen", ha="center", color=zacht)
    fig.tight_layout()
    fig.savefig(out / "horizon.png")
    plt.close(fig)


def schrijf_ruw(map_: Path, slug: str, data: dict, meetpunt: dict, strand: pd.DataFrame):
    """Uurwaarden bewaren om met de hand na te rekenen."""
    obs = pd.concat([df.add_prefix(f"{g}:") for g, df in data.items()], axis=1) if data else pd.DataFrame()
    obs = obs.loc[:, ~obs.columns.duplicated()]
    obs.to_csv(map_ / f"{slug}_metingen.csv", index_label="tijd_utc", float_format="%.3f")
    fc = pd.concat([df.add_prefix(f"{g}:") for g, df in meetpunt.items()], axis=1) if meetpunt else pd.DataFrame()
    fc.to_csv(map_ / f"{slug}_voorspelling_meetpunt.csv", index_label="tijd_utc", float_format="%.3f")
    strand.to_csv(map_ / f"{slug}_voorspelling_strand.csv", index_label="tijd_utc", float_format="%.3f")


def schrijf_logboek(out: Path, log, duur_min: float):
    eind = datetime.now(timezone.utc)
    r = ["# Logboek proef", "",
         f"Gestart {log.start:%Y-%m-%d %H:%M} UTC, klaar {eind:%Y-%m-%d %H:%M} UTC ({duur_min:.1f} min).", "",
         "## Bronnen", "",
         "- Open-Meteo Previous Runs API (wind, `_previous_day1/3/5`) en Marine API (golven, watertemperatuur), CC BY 4.0, niet-commercieel",
         "- NDBC (NOAA): maandarchief `data/stdmet/Sep/<id>.txt`, aangevuld uit `data/realtime2/<id>.txt`; stationspagina voor positie en anemometerhoogte",
         "- METAR via Iowa Environmental Mesonet: `cgi-bin/request/asos.py`; stationslijsten `geojson/network/<netwerk>.geojson`",
         "- Copernicus Marine In Situ: `cmems_obs-ins_glo_phybgcwav_mynrt_na_irr`, `index_monthly.txt`, map `monthly/<soort>/202609/`",
         "", "## Aanvragen", ""]
    r += [f"- {host}: {n}" for host, n in sorted(log.aanvragen.items())]
    r += [f"- Open-Meteo, geschat gewicht (meer dan 10 variabelen of 2 weken telt meervoudig): {log.gewicht_open_meteo:.0f}", "",
          "## Weggefilterde waarden", ""]
    if log.weggefilterd:
        r += ["| Bron | Reden | Aantal |", "|---|---|---:|"]
        for bron, redenen in sorted(log.weggefilterd.items()):
            for reden, n in sorted(redenen.items()):
                r.append(f"| {bron} | {reden} | {n} |")
    else:
        r.append("Geen.")
    r += ["", "## Open punten uit de specificatie (NA TE GAAN)", "", "| Punt | Status | Antwoord |", "|---|---|---|"]
    r += [f"| {p} | {s} | {a} |" for p, s, a in log.na_te_gaan]
    r += ["", "## Verloop", ""] + log.regels
    (out / "run_log.md").write_text("\n".join(r) + "\n")
