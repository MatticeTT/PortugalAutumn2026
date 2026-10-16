"""De 14 testspots uit de specificatie 'Proef: specificatie voor Claude Code'.

ndbc_golf / ndbc_wind: boeien die de specificatie vastlegt (enkel VS).
metar_netwerken: IEM-netwerken waarin stap 0 het dichtstbijzijnde luchthavenstation zoekt
(in de VS enkel als de boei minder dan 70% geldige winduren heeft);
metar_spec: het station dat de specificatie noemt, ter controle in het logboek.
Golven en watertemperatuur buiten de VS: Copernicus In Situ, gekozen in stap 0.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Spot:
    nr: int
    slug: str
    naam: str
    lat: float
    lon: float
    sport: str
    ndbc_golf: str | None = None
    ndbc_wind: str | None = None
    metar_netwerken: tuple[str, ...] = field(default=())
    metar_spec: str | None = None


SPOTS = [
    Spot(1, "ocean_beach", "Ocean Beach, San Francisco (VS)", 37.760, -122.511, "surf", "46026", "46026", ("CA_ASOS",)),
    Spot(2, "hookipa", "Ho'okipa, Maui (VS)", 20.934, -156.357, "surf, windsurf, kite", "51205", None, ("HI_ASOS",), "PHOG"),
    Spot(3, "buxton", "Cape Hatteras, Buxton (VS)", 35.250, -75.525, "kite, surf", "41025", "41025", ("NC_ASOS",)),
    Spot(4, "cocoa_beach", "Cocoa Beach, Florida (VS)", 28.320, -80.607, "surf", "41009", "41009", ("FL_ASOS",)),
    Spot(5, "oostende", "Oostende, Mariakerke (BE)", 51.230, 2.905, "kite, windsurf", None, None, ("BE__ASOS", "FR__ASOS", "NL__ASOS"), "EBOS"),
    Spot(6, "scheveningen", "Scheveningen (NL)", 52.108, 4.268, "surf, kite", None, None, ("NL__ASOS",), "EHRD"),
    Spot(7, "hossegor", "Hossegor, La Gravière (FR)", 43.671, -1.443, "surf", None, None, ("FR__ASOS", "ES__ASOS"), "LFBZ"),
    Spot(8, "nazare", "Nazaré, Praia do Norte (PT)", 39.608, -9.085, "surf (grote golven)", None, None, ("PT__ASOS",), None),
    Spot(9, "tarifa", "Tarifa, Los Lances (ES)", 36.020, -5.625, "kite", None, None, ("ES__ASOS", "GI__ASOS", "MA__ASOS"), "LXGB"),
    Spot(10, "pozo", "Pozo Izquierdo, Gran Canaria (ES)", 27.820, -15.423, "windsurf", None, None, ("ES__ASOS",), "GCLP"),
    Spot(11, "big_bay", "Big Bay, Kaapstad (ZA)", -33.790, 18.460, "kite, surf", None, None, ("ZA__ASOS",), "FACT"),
    Spot(12, "manly", "Manly, Sydney (AU)", -33.797, 151.289, "surf", None, None, ("AU__ASOS",), "YSSY"),
    Spot(13, "joaquina", "Joaquina, Florianópolis (BR)", -27.629, -48.448, "surf", None, None, ("BR__ASOS",), "SBFL"),
    Spot(14, "uluwatu", "Uluwatu, Bali (ID)", -8.815, 115.087, "surf", None, None, ("ID__ASOS",), "WADD"),
]
