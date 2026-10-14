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
    build.write_levels(rgb, tmp_path, "wind")
    from PIL import Image

    coarse = np.array(Image.open(tmp_path / "wind.png"))
    assert coarse.shape == (181, 360, 3)
    last = np.array(Image.open(tmp_path / "wind" / "3_7.png"))
    assert last.shape == (build.TILE_PX + 1, build.TILE_PX + 1, 3)
    assert np.array_equal(last[:, -1], rgb[540:, 0])  # oostrand = lengte 0 (rond de wereld)
    assert np.array_equal(last[-1], np.concatenate([rgb[-1, 1260:], rgb[-1, :1]]))
