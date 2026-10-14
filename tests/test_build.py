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

    last = np.array(Image.open(tmp_path / "wind" / "3_7.webp"))
    assert last.shape == (build.TILE_PX + 1, build.TILE_PX + 1, 3)
    assert np.array_equal(last[:, -1], rgb[540:, 0])  # oostrand = lengte 0 (rond de wereld)
    assert np.array_equal(last[-1], np.concatenate([rgb[-1, 1260:], rgb[-1, :1]]))


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
