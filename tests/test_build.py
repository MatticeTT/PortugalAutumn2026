"""Codering van wind en golven: wat de browser terugleest moet kloppen met de modelwaarden."""

import numpy as np

from pipeline import build


def dec_wind(b):
    s = b.astype(float) / 127.5 - 1
    return np.sign(s) * s * s * build.WIND_MAX


def test_wind_roundtrip():
    u = np.array([[-30.0, -5.0, -0.5, 0.0, 0.5, 5.0, 12.0, 30.0]], np.float32)
    v = -u
    rgb = build.encode_wind(u, v)
    du, dv = dec_wind(rgb[..., 0]), dec_wind(rgb[..., 1])
    # Fout van hooguit ongeveer 0,5 m/s, en veel kleiner bij zwakke wind.
    assert np.all(np.abs(du - u) <= np.maximum(0.03, 0.035 * np.abs(u)))
    assert np.all(np.abs(dv - v) <= np.maximum(0.03, 0.035 * np.abs(v)))
    assert np.all(np.sign(np.round(du, 2)) == np.sign(u))


def test_wave_direction_and_mask():
    # Golven uit het noordwesten (315 graden) lopen naar het zuidoosten.
    hs = np.array([[2.0, np.nan, 0.0]], np.float32)
    dirp = np.array([[315.0, np.nan, 90.0]], np.float32)
    per = np.array([[12.0, np.nan, 5.0]], np.float32)
    rgb = build.encode_wave(hs, dirp, per).astype(float)
    x, y = rgb[0, 0, 0] / 127.5 - 1, rgb[0, 0, 1] / 127.5 - 1
    assert x > 0 and y < 0 and abs(abs(x) - abs(y)) < 0.02  # zuidoost
    length = np.hypot(x, y)
    assert abs((length - 0.3) / 0.7 * build.T_MAX - 12.0) < 0.3
    s = (rgb[0, 0, 2] - 1) / 254
    assert abs(s * s * build.H_MAX - 2.0) < 0.1
    assert rgb[0, 1, 2] == 0  # land
    assert rgb[0, 2, 2] >= 1  # vlakke zee is geen land
    assert rgb[0, 2, 0] < 128 and abs(rgb[0, 2, 1] - 127.5) < 1  # uit het oosten: loopt naar het westen


def test_tiles_cover_globe_with_overlap(tmp_path):
    rng = np.random.default_rng(1)
    rgb = rng.integers(0, 255, (build.NJ, build.NI, 3), dtype=np.uint8)
    build.write_tiles(rgb, tmp_path, "wind")
    from PIL import Image

    # Laatste rij met fijne tegels (0 .. 45 zuid); de rij daaronder (45 .. 90 zuid) heeft alleen het wereldraster.
    last = np.array(Image.open(tmp_path / "wind" / f"{build.FINE_ROWS - 1}_7.webp"))
    assert last.shape == (build.TILE_PX + 1, build.TILE_PX + 1, 3)
    j0 = (build.FINE_ROWS - 1) * build.TILE_PX
    assert np.array_equal(last[:, -1], rgb[j0:j0 + build.TILE_PX + 1, 0])  # oostrand = lengte 0 (rond de wereld)
    assert np.array_equal(last[-1], np.concatenate([rgb[j0 + build.TILE_PX, 1260:], rgb[j0 + build.TILE_PX, :1]]))
    assert not (tmp_path / "wind" / f"{build.FINE_ROWS}_0.webp").exists()


def test_hours_follow_ecmwf_steps():
    hs = build.hours(360)
    assert hs[:3] == [0, 3, 6] and 144 in hs and 147 not in hs and 150 in hs and hs[-1] == 360
    assert len(hs) == 85


def test_decode_shifts_to_lon_zero():
    import eccodes

    g = eccodes.codes_grib_new_from_samples("regular_ll_sfc_grib2")
    for k, v in {"Ni": build.NI, "Nj": build.NJ, "iDirectionIncrementInDegrees": 0.25,
                 "jDirectionIncrementInDegrees": 0.25, "latitudeOfFirstGridPointInDegrees": 90,
                 "latitudeOfLastGridPointInDegrees": -90, "longitudeOfFirstGridPointInDegrees": 180,
                 "longitudeOfLastGridPointInDegrees": 179.75}.items():
        eccodes.codes_set(g, k, v)
    lon = (180 + np.arange(build.NI) * 0.25) % 360  # waarde = lengte van de cel
    eccodes.codes_set_values(g, np.tile(lon, build.NJ).astype(float))
    grid = build.decode(eccodes.codes_get_message(g))
    assert abs(grid[0, 0]) < 0.01 and abs(grid[0, 4] - 1.0) < 0.01 and abs(grid[0, -1] - 359.75) < 0.01


def test_coarse_keeps_mask_and_mean():
    hs = np.full((build.NJ, build.NI), 2.0, np.float32)
    hs[:, :8] = np.nan  # land
    dirp = np.full_like(hs, 270.0)  # uit het westen
    per = np.full_like(hs, 10.0)
    rgb = build.coarse_wave(hs, dirp, per, 4)
    assert rgb.shape == (181, 360, 3)
    assert (rgb[:, :2, 2] == 0).all() and (rgb[:, 2:, 2] > 0).all()
    assert rgb[90, 100, 0] > 200 and abs(int(rgb[90, 100, 1]) - 128) <= 1  # loopt naar het oosten
    u = np.full((build.NJ, build.NI), 5.0, np.float32)
    w = build.coarse_wind(u, -u, 2)
    assert w.shape == (361, 720, 3) and (w[..., 0] == build.encode_wind(u[:1, :1], u[:1, :1])[0, 0, 0]).all()


def test_fill_coast_reaches_inland_a_few_cells():
    hs = np.full((build.NJ, build.NI), np.nan, np.float32)
    dirp = np.full_like(hs, np.nan)
    per = np.full_like(hs, np.nan)
    hs[:, :100], dirp[:, :100], per[:, :100] = 2.0, 300.0, 11.0  # zee in het westen, land erachter
    h, d, t = build.fill_coast(hs, dirp, per, cells=3)
    assert np.isfinite(h[:, 100:103]).all() and np.isnan(h[:, 103:-3]).all()
    assert np.allclose(h[:, 102], 2.0) and np.allclose(d[:, 102], 300.0, atol=0.01) and np.allclose(t[:, 102], 11.0)


def test_copernicus_naar_kaartrooster():
    """1/12 graad (vanaf 80 zuid, lengte -180) naar het kaartrooster van 0,25 graad (vanaf 90 noord, lengte 0)."""
    from pipeline import golven

    nlat, nlon = 2041, 4320
    lat = -80 + np.arange(nlat) / 12
    lon = -180 + np.arange(nlon) / 12
    h = np.broadcast_to(1.0 + (lon + 180) / 360, (nlat, nlon)).astype(np.float32).copy()  # hoogte volgt de lengte
    d = np.full((nlat, nlon), 270.0, np.float32)
    tp = np.full((nlat, nlon), 10.0, np.float32)
    h[(np.abs(lat - 50) < 0.01)[:, None] & (np.abs(lon - 2) < 0.01)[None, :]] = np.nan  # één landcel op 50 N, 2 O
    hm, dm, tm = golven.naar_kaartrooster(h, d, tp, -80.0, -180.0)
    assert hm.shape == (721, 1440)
    j = lambda la: int(round((90 - la) * 4))  # noqa: E731
    i = lambda lo: int(round((lo % 360) * 4))  # noqa: E731
    # 10 graden oost: fijne kolom bij lengte 10 heeft hoogte 1 + 190/360
    assert hm[j(40), i(10)] == np.float32(1 + 190 / 360) or abs(hm[j(40), i(10)] - (1 + 190 / 360)) < 1e-4
    assert abs(hm[j(40), i(-30)] - (1 + 150 / 360)) < 1e-4  # 30 west = kolom 1320
    assert abs(dm[j(40), i(10)] - 270) < 1e-3 and abs(tm[j(40), i(10)] - 10) < 1e-4
    assert np.isnan(hm[j(-85), i(10)])  # buiten het golfmodel
    assert np.isnan(hm[j(50), i(2)])  # middelste fijne cel is land: kaartcel is land
    assert np.isfinite(hm[j(50), i(2.25)])  # buur ernaast: zee, gemiddeld zonder de landcel
