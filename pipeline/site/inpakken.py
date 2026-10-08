"""Compacte fiches voor de andere landen: getallen per uur als tekst (de waarden blijven exact gelijk).

Elk getal wordt een geheel getal (waarde x schaal; de waarden zijn al op zoveel decimalen afgerond) en
dan 2 of 3 tekens uit ALFABET (64 tekens); het hoogste getal betekent "geen waarde". De site pakt het
terug uit (web/src/fiche.ts, uitpakken); tests/test_inpakken.py controleert dat heen en terug gelijk is.
"""

from __future__ import annotations

ALFABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_"
# veld: (schaal, tekens per waarde)
VELDEN = {
    "wind": (10, 2), "vlagen": (10, 2), "windrichting": (1, 2), "zee_h": (100, 2), "zee_t": (10, 2),
    "zee_r": (1, 2), "E_zee": (1, 3), "bereikt": (1, 2), "E": (1, 3), "periode": (10, 2), "H": (100, 2),
    "windhoek": (10, 2), "tij": (1, 2), "tijgewicht": (100, 2), "verval": (100, 2),
}


def pak(waarden: list, schaal: int, n: int) -> str:
    leeg = 64 ** n - 1
    uit = []
    for v in waarden:
        if v is None:
            k = leeg
        else:
            k = round(v * schaal)
            if not 0 <= k < leeg:
                raise ValueError(f"{v} past niet in {n} tekens")
        uit.append("".join(ALFABET[(k // 64 ** (n - 1 - j)) % 64] for j in range(n)))
    return "".join(uit)


def ontpak(tekst: str, schaal: int, n: int) -> list:
    leeg = 64 ** n - 1
    uit = []
    for i in range(0, len(tekst), n):
        k = 0
        for c in tekst[i:i + n]:
            k = k * 64 + ALFABET.index(c)
        uit.append(None if k == leeg else (k if schaal == 1 else k / schaal))
    return uit


def inpakken(detail: dict) -> dict:
    """Velden uit VELDEN als tekst onder "p" (met de schalen onder "ps"); de rest blijft."""
    p = {}
    for veld, (schaal, n) in VELDEN.items():
        if veld in detail:
            waarden = detail.pop(veld)
            p[veld] = pak(waarden, schaal, n)
            if ontpak(p[veld], schaal, n) != waarden:  # nooit stil een andere waarde tonen
                raise ValueError(f"{veld}: inpakken verandert de waarden")
    detail["p"] = p
    return detail


# Conclusies: "andere: windsurfen 25/100, niet ideaal door ..." verschilt per uur vaak alleen in de score, en die
# score staat al in "scores" (rond(ruw) van die activiteit). De tekst wordt dan een sjabloon met "#" op de plaats
# van de score; terugzetten = "#" vervangen door scores[uur][kolom van die activiteit]. Alleen als dat exact de
# oorspronkelijke tekst geeft (dat wordt hier per uur nagekeken), anders blijft de volledige tekst.
KOLOM = {"windsurfen op golven": 1, "golfsurfen": 0, "windsurfen": 2, "stille waters": 3}  # langste naam eerst


def sjabloon(tekst: str | None, scores: list | None) -> str | None:
    if tekst is None or scores is None:
        return tekst
    for naam, kol in KOLOM.items():
        stuk = f"{naam} {scores[kol]}/100"
        if stuk in tekst and tekst.count("/100") == 1:
            s = tekst.replace(stuk, f"{naam} #/100")
            if terug(s, scores) == tekst:
                return s
    return tekst


def terug(s: str | None, scores: list | None) -> str | None:
    if s is None or "#/100" not in s:
        return s
    for naam, kol in KOLOM.items():
        if f"{naam} #/100" in s:
            return s.replace(f"{naam} #/100", f"{naam} {scores[kol]}/100")
    return s


def pak_scores(scores: list) -> str:
    """Per uur de 5 scores (0..100, 2 tekens elk) of 5 x leeg."""
    return "".join(pak(rij if rij is not None else [None] * 5, 1, 2) for rij in scores)


def ontpak_scores(tekst: str) -> list:
    uit = []
    for i in range(0, len(tekst), 10):
        rij = ontpak(tekst[i:i + 10], 1, 2)
        uit.append(None if all(v is None for v in rij) else rij)
    return uit


def conclusies_inpakken(detail: dict) -> dict:
    """"conclusie" -> "conclusies" (unieke sjablonen) + "c" (volgnummer per uur, -1 = geen); "scores" -> "sc"."""
    scores = detail["scores"]
    sj = [sjabloon(c, scores[i]) for i, c in enumerate(detail.pop("conclusie"))]
    teksten = sorted({c for c in sj if c is not None})
    nr = {c: k for k, c in enumerate(teksten)}
    detail["conclusies"] = teksten
    detail["c"] = [-1 if c is None else nr[c] for c in sj]
    detail["sc"] = pak_scores(detail.pop("scores"))
    return detail


def conclusies_uitpakken(d: dict) -> dict:
    if "sc" in d:
        d["scores"] = ontpak_scores(d["sc"])
    if "c" in d:
        d["conclusie"] = [None if k < 0 else terug(d["conclusies"][k], d["scores"][i]) for i, k in enumerate(d["c"])]
    return d
