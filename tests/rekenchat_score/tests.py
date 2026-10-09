import itertools, json, sys
from score import score, breaking_height, CATEGORIES, GO

ANY = (0, 90, 170)
OFF = (170,)
# golf-combinaties uit het document: (Hs, T, golfhoek, [(windmax, hoeken)...], stroming)
S = {
 "golfsurfen_beginner": {
  "A": dict(hs=(.4,.6), t=(8,10), ga=(0,20), wind=[(0,8,OFF),(0,3,ANY)], cur=.5),
  "B": dict(hs=(.5,.8), t=(5,7), ga=(0,20), wind=[(0,8,ANY)], cur=.5),
  "C": dict(hs=(.3,.4), t=(11,14), ga=(0,20), wind=[(0,5,OFF),(0,3,ANY)], cur=.5),
  "D": dict(hb=(.6,1.0), t=(9,12), ga=(50,80), wind=[(0,10,OFF)], cur=.5)},
 "golfsurfen_gemiddeld": {
  "A": dict(hs=(.6,.8), t=(10,13), ga=(10,30), wind=[(3,10,OFF),(0,3,ANY)], cur=.5),
  "B": dict(hs=(.8,1.1), t=(7,9), ga=(10,30), wind=[(0,8,(110,135,170))], cur=.5),
  "C": dict(hs=(.5,.6), t=(14,17), ga=(10,30), wind=[(0,8,OFF),(0,3,ANY)], cur=.5)},
 "golfsurfen_ervaren": {
  "A": dict(hs=(1.2,1.8), t=(11,14), ga=(10,30), wind=[(5,15,OFF)], cur=.5),
  "B": dict(hs=(1.8,2.3), t=(8,10), ga=(0,15), wind=[(5,12,OFF)], cur=.5),
  "C": dict(hs=(1.0,1.3), t=(15,18), ga=(15,30), wind=[(0,10,OFF)], cur=.5)},
 "longboard_gemiddeld": {
  "A": dict(hs=(.3,.5), t=(11,14), ga=(15,30), wind=[(0,5,ANY),(0,8,OFF)], cur=.5),
  "B": dict(hs=(.5,.7), t=(7,9), ga=(15,30), wind=[(0,8,OFF)], cur=.5),
  "C": dict(hs=(.4,.6), t=(9,11), ga=(15,30), wind=[(0,6,(90,170)),(0,5,ANY)], cur=.5),
  "D": dict(hb=(.6,1.1), t=(12,16), ga=(50,80), wind=[(0,8,OFF)], cur=.5)},
 "longboard_ervaren": {
  "A": dict(hs=(.5,.8), t=(11,15), ga=(15,30), wind=[(3,8,OFF)], cur=.5),
  "B": dict(hs=(.7,1.0), t=(8,10), ga=(15,30), wind=[(0,5,ANY)], cur=.5),
  "C": dict(hs=(.4,.6), t=(15,18), ga=(15,30), wind=[(0,6,OFF)], cur=.5)},
 "shortboard_gemiddeld": {
  "A": dict(hs=(.7,1.0), t=(10,13), ga=(10,30), wind=[(5,12,OFF)], cur=.5),
  "B": dict(hs=(1.0,1.4), t=(7,9), ga=(10,30), wind=[(0,10,OFF)], cur=.5),
  "C": dict(hs=(.6,.8), t=(14,17), ga=(15,30), wind=[(3,10,OFF)], cur=.5)},
 "shortboard_ervaren": {
  "A": dict(hs=(1.5,2.0), t=(12,16), ga=(10,30), wind=[(8,15,OFF)], cur=.5),
  "B": dict(hs=(2.0,2.5), t=(9,11), ga=(0,20), wind=[(5,12,OFF)], cur=.5),
  "C": dict(hs=(1.0,1.4), t=(16,20), ga=(15,30), wind=[(0,10,OFF)], cur=.5)},
}
# vlak water: wind, vlaag boven gemiddelde, hoeken, golf aan strand, stroming (kn, richting)
F = {
 "windsurfen_beginner": {
  "A": dict(w=(5,8), g=3, an=(20,65,110), wa=(0,.2), cur=(.3,"dwars")),
  "B": dict(w=(8,12), g=5, an=(20,70), wa=(0,.3), cur=(.5,"dwars")),
  "C": dict(w=(12,15), g=5, an=(20,110), wa=(0,.3), cur=(.5,"dwars"))},
 "windsurfen_gemiddeld": {
  "A": dict(w=(13,16), g=5, an=(70,110), wa=(0,.3), cur=(1.5,"tegen")),
  "B": dict(w=(16,20), g=6, an=(20,110), wa=(0,.5), cur=(1,"dwars")),
  "C": dict(w=(20,25), g=8, an=(70,110), wa=(0,.3), cur=(1,"dwars"))},
 "windsurfen_ervaren": {
  "A": dict(w=(20,30), g=6, an=(70,140), wa=(0,.2), cur=(.5,"dwars")),
  "B": dict(w=(18,25), g=8, an=(70,110), wa=(.3,.8), cur=(1,"tegen")),
  "D": dict(w=(30,40), g=10, an=(20,110), wa=(0,.4), cur=(.5,"dwars"))},
 "kitesurfen_beginner": {
  "A": dict(w=(12,15), g=4, an=(20,70), wa=(0,.3), cur=(.5,"dwars")),
  "B": dict(w=(15,18), g=5, an=(20,110), wa=(0,.5), cur=(.5,"dwars")),
  "C": dict(w=(18,22), g=5, an=(20,70), wa=(0,.3), cur=(.5,"dwars"))},
 "kitesurfen_gemiddeld": {
  "A": dict(w=(11,14), g=4, an=(20,110), wa=(0,.3), cur=(1.5,"tegen")),
  "B": dict(w=(15,20), g=6, an=(20,110), wa=(0,.5), cur=(1,"dwars")),
  "C": dict(w=(20,26), g=6, an=(20,70), wa=(.3,.8), cur=(1,"dwars"))},
 "kitesurfen_ervaren": {
  "A": dict(w=(28,38), g=8, an=(20,110), wa=(.5,1.5), cur=(1,"tegen")),
  "B": dict(w=(16,22), g=4, an=(70,110), wa=(0,.15), cur=(.5,"dwars"))},
}
W = {
 "windsurfen_golven_gemiddeld": {
  "A": dict(w=(18,24), an=(30,60), hs=(.6,1.0), t=(6,8), g=8, cur=1),
  "B": dict(w=(16,22), an=(70,110), hs=(.6,.9), t=(9,12), g=8, cur=.5),
  "C": dict(w=(24,30), an=(30,60), hs=(.5,.8), t=(5,7), g=8, cur=1)},
 "windsurfen_golven_ervaren": {
  "A": dict(w=(18,25), an=(110,140), hs=(1.5,2.5), t=(12,16), g=8, cur=.5),
  "B": dict(w=(25,35), an=(70,110), hs=(2.0,3.0), t=(9,12), g=8, cur=1),
  "C": dict(w=(30,40), an=(30,60), hs=(2.5,4.0), t=(8,10), g=8, cur=2),
  "D": dict(w=(12,17), an=(90,130), hs=(1.2,2.0), t=(14,18), g=8, cur=.5)},
 "kitesurfen_golven_gemiddeld": {
  "A": dict(w=(16,22), an=(30,60), hs=(.5,.9), t=(6,8), g=6, cur=1),
  "B": dict(w=(15,20), an=(70,110), hs=(.6,.9), t=(9,12), g=6, cur=.5),
  "C": dict(w=(22,28), an=(30,60), hs=(.6,1.0), t=(5,7), g=6, cur=1)},
 "kitesurfen_golven_ervaren": {
  "A": dict(w=(14,20), an=(110,140), hs=(1.5,2.5), t=(12,16), g=6, cur=.5),
  "B": dict(w=(20,28), an=(70,110), hs=(1.5,2.5), t=(9,12), g=6, cur=1),
  "C": dict(w=(25,35), an=(30,60), hs=(2.0,3.0), t=(7,10), g=6, cur=2),
  "D": dict(w=(12,15), an=(70,110), hs=(1.2,1.8), t=(13,17), g=6, cur=.5)},
}

def mid(r): return (r[0]+r[1])/2

def combo_scores():
    out = {}
    for cat, cs in S.items():
        for k, c in cs.items():
            vals = []
            for (wlo, whi, angs) in c["wind"]:
                for wv, wa, t, ga in itertools.product((wlo, whi), angs, c["t"], c["ga"]):
                    hrange = c.get("hs") or c["hb"]
                    for h in hrange:
                        cond = dict(wind=wv, windhoek=wa, periode=t, golfhoek=ga, stroming=c["cur"])
                        if "hs" in c: cond["golfhoogte"] = h
                        else: cond["hb"] = h
                        vals.append(score(cat, cond)["score"])
            out[(cat, k)] = (min(vals), max(vals))
    for cat, cs in F.items():
        for k, c in cs.items():
            vals = []
            for wv, wa, wat in itertools.product(c["w"], c["an"], c["wa"]):
                cond = dict(wind=wv, vlaag=wv+c["g"], windhoek=wa, golf_aan_strand=wat,
                            stroming=c["cur"][0], stroming_tov_wind=c["cur"][1])
                vals.append(score(cat, cond)["score"])
                cond0 = dict(cond, stroming=0)
                if c["cur"][1] != "tegen" or True:
                    vals.append(score(cat, cond0)["score"]) if c["cur"][1] != "tegen" else None
            out[(cat, k)] = (min(vals), max(vals))
    for cat, cs in W.items():
        for k, c in cs.items():
            vals = []
            for wv, wa, h, t, ga in itertools.product(c["w"], c["an"], c["hs"], c["t"], (0, 20)):
                cond = dict(wind=wv, vlaag=wv+c["g"], windhoek=wa, golfhoogte=h, periode=t,
                            golfhoek=ga, stroming=c["cur"], stroming_tov_wind="dwars")
                vals.append(score(cat, cond)["score"])
            out[(cat, k)] = (min(vals), max(vals))
    return out

ZERO = [
 ("onweer", "kitesurfen_gemiddeld", dict(wind=18, vlaag=22, windhoek=60, golf_aan_strand=.3, onweer=True)),
 ("kitebeginner, aflandige wind", "kitesurfen_beginner", dict(wind=15, vlaag=18, windhoek=150, golf_aan_strand=.2)),
 ("kite, 6 knopen", "kitesurfen_gemiddeld", dict(wind=6, vlaag=8, windhoek=60, golf_aan_strand=.2)),
 ("windsurfen gemiddeld, 8 knopen", "windsurfen_gemiddeld", dict(wind=8, vlaag=10, windhoek=60, golf_aan_strand=.2)),
 ("windsurfbeginner, 25 knopen", "windsurfen_beginner", dict(wind=25, vlaag=30, windhoek=60, golf_aan_strand=.3)),
 ("kitebeginner, vlagen +12", "kitesurfen_beginner", dict(wind=15, vlaag=27, windhoek=60, golf_aan_strand=.2)),
 ("surfbeginner, brekende golf 2 m", "golfsurfen_beginner", dict(hb=2.0, periode=10, wind=3, windhoek=170)),
 ("shortboard ervaren, golf 0,5 m", "shortboard_ervaren", dict(hb=0.5, periode=10, wind=8, windhoek=170)),
 ("golfsurfen gemiddeld, 20 knopen aanlandig", "golfsurfen_gemiddeld", dict(hb=1.3, periode=10, wind=20, windhoek=0)),
 ("kite op golven gemiddeld, aflandig", "kitesurfen_golven_gemiddeld", dict(wind=18, vlaag=22, windhoek=140, golfhoogte=.8, periode=8)),
 ("windsurfen op golven ervaren, geen golf", "windsurfen_golven_ervaren", dict(wind=25, vlaag=30, windhoek=90, golfhoogte=.3, periode=5)),
]

# mogen geen "ga" (60 of meer) geven
NO_GO = [
 ("kitesurfen gemiddeld, 12 knopen", "kitesurfen_gemiddeld", dict(wind=12, vlaag=14, windhoek=60, golf_aan_strand=.2)),
 ("kitesurfen beginner, 12 knopen", "kitesurfen_beginner", dict(wind=12, vlaag=14, windhoek=60, golf_aan_strand=.2)),
 ("windsurfen gemiddeld, 13 knopen", "windsurfen_gemiddeld", dict(wind=13, vlaag=15, windhoek=60, golf_aan_strand=.2)),
 ("windsurfen ervaren, 9 knopen", "windsurfen_ervaren", dict(wind=9, vlaag=11, windhoek=60, golf_aan_strand=.2)),
 ("kitesurfen ervaren, 9 knopen", "kitesurfen_ervaren", dict(wind=9, vlaag=11, windhoek=60, golf_aan_strand=.2)),
 ("golfsurfen beginner, 0,35 m met 14 s", "golfsurfen_beginner", dict(golfhoogte=.35, periode=14, wind=3, windhoek=170)),
 ("golfsurfen beginner, 0,3 m met 8 s", "golfsurfen_beginner", dict(golfhoogte=.3, periode=8, wind=3, windhoek=170)),
 ("golfsurfen gemiddeld, 0,5 m met 8 s", "golfsurfen_gemiddeld", dict(golfhoogte=.5, periode=8, wind=3, windhoek=170)),
 ("windsurfen op golven ervaren, 14 knopen", "windsurfen_golven_ervaren", dict(wind=14, vlaag=17, windhoek=100, golfhoogte=1.6, periode=15)),
]

# (categorie, omschrijving, betere dag, slechtere dag)
PAIRS = [
 ("golfsurfen_gemiddeld", "aflandig 6 kn tegenover aanlandig 12 kn", dict(hb=1.3, periode=11, wind=6, windhoek=170), dict(hb=1.3, periode=11, wind=12, windhoek=0)),
 ("golfsurfen_gemiddeld", "1,3 m tegenover 0,5 m", dict(hb=1.3, periode=11, wind=5, windhoek=170), dict(hb=0.5, periode=11, wind=5, windhoek=170)),
 ("golfsurfen_beginner", "1,0 m tegenover 1,9 m", dict(hb=1.0, periode=8, wind=4, windhoek=170), dict(hb=1.9, periode=8, wind=4, windhoek=170)),
 ("golfsurfen_beginner", "weinig stroming tegenover 1,5 knoop", dict(hb=0.8, periode=8, wind=4, windhoek=170, stroming=.3), dict(hb=0.8, periode=8, wind=4, windhoek=170, stroming=1.5)),
 ("golfsurfen_ervaren", "12 s tegenover 6 s bij dezelfde brekende golf", dict(hb=2.2, periode=12, wind=8, windhoek=170), dict(hb=2.2, periode=6, wind=8, windhoek=170)),
 ("longboard_gemiddeld", "windstil tegenover 15 kn aflandig", dict(hb=0.8, periode=10, wind=1, windhoek=170), dict(hb=0.8, periode=10, wind=15, windhoek=170)),
 ("longboard_ervaren", "1,2 m tegenover 2,0 m", dict(hb=1.2, periode=12, wind=4, windhoek=170), dict(hb=2.0, periode=12, wind=4, windhoek=170)),
 ("shortboard_gemiddeld", "aflandig 8 kn tegenover dwars 12 kn", dict(hb=1.5, periode=11, wind=8, windhoek=170), dict(hb=1.5, periode=11, wind=12, windhoek=90)),
 ("shortboard_ervaren", "2,5 m tegenover 1,0 m", dict(hb=2.5, periode=13, wind=10, windhoek=170), dict(hb=1.0, periode=13, wind=10, windhoek=170)),
 ("shortboard_ervaren", "een zuivere deining tegenover kruisende golven", dict(hb=2.5, periode=13, wind=10, windhoek=170, aandeel_hoofdgolf=.9), dict(hb=2.5, periode=13, wind=10, windhoek=170, aandeel_hoofdgolf=.45)),
 ("windsurfen_beginner", "8 kn tegenover 18 kn", dict(wind=8, vlaag=11, windhoek=60, golf_aan_strand=.2), dict(wind=18, vlaag=22, windhoek=60, golf_aan_strand=.2)),
 ("windsurfen_beginner", "side-on tegenover aflandig", dict(wind=8, vlaag=11, windhoek=60, golf_aan_strand=.2), dict(wind=8, vlaag=11, windhoek=150, golf_aan_strand=.2)),
 ("windsurfen_gemiddeld", "constante wind tegenover vlagen +14", dict(wind=18, vlaag=22, windhoek=90, golf_aan_strand=.3), dict(wind=18, vlaag=32, windhoek=90, golf_aan_strand=.3)),
 ("windsurfen_gemiddeld", "18 kn tegenover 11 kn", dict(wind=18, vlaag=22, windhoek=90, golf_aan_strand=.3), dict(wind=11, vlaag=14, windhoek=90, golf_aan_strand=.3)),
 ("windsurfen_gemiddeld", "13 kn met stroom tegen tegenover stroom mee", dict(wind=13, vlaag=16, windhoek=90, golf_aan_strand=.2, stroming=1.5, stroming_tov_wind="tegen"), dict(wind=13, vlaag=16, windhoek=90, golf_aan_strand=.2, stroming=1.5, stroming_tov_wind="mee")),
 ("windsurfen_ervaren", "25 kn op vlak water tegenover 25 kn met vlagen +15", dict(wind=25, vlaag=30, windhoek=90, golf_aan_strand=.2), dict(wind=25, vlaag=40, windhoek=90, golf_aan_strand=.2)),
 ("kitesurfen_beginner", "15 kn side-on tegenover 25 kn", dict(wind=15, vlaag=18, windhoek=60, golf_aan_strand=.2), dict(wind=25, vlaag=28, windhoek=60, golf_aan_strand=.2)),
 ("kitesurfen_beginner", "vlak water tegenover 0,9 m golf", dict(wind=15, vlaag=18, windhoek=60, golf_aan_strand=.2), dict(wind=15, vlaag=18, windhoek=60, golf_aan_strand=.9)),
 ("kitesurfen_gemiddeld", "side-shore tegenover recht aanlandig", dict(wind=18, vlaag=22, windhoek=90, golf_aan_strand=.4), dict(wind=18, vlaag=22, windhoek=0, golf_aan_strand=.4)),
 ("kitesurfen_gemiddeld", "droog tegenover buien", dict(wind=18, vlaag=22, windhoek=90, golf_aan_strand=.4, neerslag=0), dict(wind=18, vlaag=22, windhoek=90, golf_aan_strand=.4, neerslag=5)),
 ("kitesurfen_ervaren", "32 kn constant tegenover 32 kn met vlagen +14", dict(wind=32, vlaag=38, windhoek=60, golf_aan_strand=1.0), dict(wind=32, vlaag=46, windhoek=60, golf_aan_strand=1.0)),
 ("windsurfen_golven_gemiddeld", "side-shore tegenover recht aanlandig", dict(wind=20, vlaag=25, windhoek=90, golfhoogte=.8, periode=9), dict(wind=20, vlaag=25, windhoek=0, golfhoogte=.8, periode=9)),
 ("windsurfen_golven_gemiddeld", "golf 1,2 m tegenover 2,2 m", dict(wind=20, vlaag=25, windhoek=90, hb=1.2, periode=9), dict(wind=20, vlaag=25, windhoek=90, hb=2.2, periode=9)),
 ("windsurfen_golven_ervaren", "golf 3 m tegenover 1,3 m", dict(wind=25, vlaag=30, windhoek=100, hb=3.0, periode=12), dict(wind=25, vlaag=30, windhoek=100, hb=1.3, periode=12)),
 ("kitesurfen_golven_gemiddeld", "side-on tegenover side-off", dict(wind=18, vlaag=22, windhoek=50, golfhoogte=.8, periode=8), dict(wind=18, vlaag=22, windhoek=125, golfhoogte=.8, periode=8)),
 ("kitesurfen_golven_ervaren", "golf recht op het strand tegenover 60 graden schuin", dict(wind=20, vlaag=24, windhoek=100, hb=2.8, periode=12, golfhoek=5), dict(wind=20, vlaag=24, windhoek=100, hb=2.8, periode=12, golfhoek=60)),
]

DAYS = {
 "Kleine schone deining": dict(wind=5, vlaag=7, windhoek=170, golfhoogte=.5, periode=10, golf_aan_strand=.5, golfhoek=15),
 "Stevige schone deining": dict(wind=8, vlaag=11, windhoek=170, golfhoogte=1.6, periode=13, golf_aan_strand=1.6, golfhoek=15),
 "Vlak water, 18 knopen": dict(wind=18, vlaag=22, windhoek=70, golfhoogte=.3, periode=3, golf_aan_strand=.3, golfhoek=10),
 "Wind en golven, 22 knopen": dict(wind=22, vlaag=28, windhoek=50, golfhoogte=1.0, periode=7, golf_aan_strand=1.0, golfhoek=10),
 "Storm, 34 knopen": dict(wind=34, vlaag=42, windhoek=50, golfhoogte=2.8, periode=9, golf_aan_strand=2.8, golfhoek=10),
 "Lichte wind, 12 knopen": dict(wind=12, vlaag=14, windhoek=60, golfhoogte=.2, periode=3, golf_aan_strand=.2, golfhoek=10),
}

LICHT = {("golfsurfen_beginner", "C"),  ("windsurfen_golven_ervaren", "D"),
         ("kitesurfen_gemiddeld", "A"), ("kitesurfen_golven_ervaren", "D")}

def midscore(cat, c, kind):
    if kind == "S":
        wlo, whi, angs = c["wind"][0]
        cond = dict(wind=(wlo + whi) / 2, windhoek=angs[-1], periode=mid(c["t"]), golfhoek=mid(c["ga"]), stroming=c["cur"])
        if "hs" in c: cond["golfhoogte"] = mid(c["hs"])
        else: cond["hb"] = mid(c["hb"])
    elif kind == "F":
        cond = dict(wind=mid(c["w"]), vlaag=mid(c["w"]) + c["g"], windhoek=sum(c["an"]) / len(c["an"]),
                    golf_aan_strand=mid(c["wa"]), stroming=c["cur"][0], stroming_tov_wind=c["cur"][1])
    else:
        cond = dict(wind=mid(c["w"]), vlaag=mid(c["w"]) + c["g"], windhoek=mid(c["an"]), golfhoogte=mid(c["hs"]),
                    periode=mid(c["t"]), golfhoek=10, stroming=c["cur"], stroming_tov_wind="dwars")
    return score(cat, cond)["score"]

if __name__ == "__main__":
    from score import algemeen, GOLF, WIND
    ok = True
    print("== T1 scenario's uit het eerste document, midden van elk bereik ==")
    n = n80 = 0
    for kind, D in (("S", S), ("F", F), ("W", W)):
        for cat, d in D.items():
            for k, c in d.items():
                ms = midscore(cat, c, kind); n += 1
                if (cat, k) in LICHT:
                    good = ms < 80; note = "streng beoordeeld (licht weer of strandafhankelijk)"
                else:
                    good = ms >= 80; note = ""; n80 += 1
                if not good: ok = False
                print(f"{cat:30s} {k} {ms:5.1f} {'ok' if good else 'FOUT'} {note}")
    print(f"{n} scenario's, waarvan {n80} minstens 80 moeten halen")
    print("\n== T2 moet 0 zijn ==")
    for name, cat, cond in ZERO:
        s = score(cat, cond)["score"]
        if s != 0: ok = False
        print(f"{name:45s} {s}")
    print("\n== T2b mag geen 'ga' zijn (onder 60) ==")
    for name, cat, cond in NO_GO:
        s = score(cat, cond)["score"]
        if s >= GO: ok = False
        print(f"{name:45s} {s} {'ok' if s < GO else 'FOUT'}")
    print("\n== T3 vergelijkingen ==")
    for cat, name, a, b in PAIRS:
        sa, sb = score(cat, a)["score"], score(cat, b)["score"]
        good = sa > sb
        if not good: ok = False
        print(f"{cat:30s} {name:55s} {sa:5.1f} > {sb:5.1f} {'ok' if good else 'FOUT'}")
    print("\n== T4 dezelfde dag: 17 scores en de twee cirkels ==")
    for d, cond in DAYS.items():
        g, w = algemeen(GOLF, cond), algemeen(WIND, cond)
        print(f"{d:28s} golf {g['cijfer']} {g['rand'] or '-':7s} wind {w['cijfer']} {w['rand'] or '-':7s}",
              {k: round(v) for k, v in {**g['scores'], **w['scores']}.items() if v > 0})
    print("\n== T5 stille waters, storm, donker, niveaufilter ==")
    from score import strand_uur, stille_waters, is_storm
    kalm = dict(wind=4, vlaag=6, windhoek=60, golfhoogte=.1, periode=3, golf_aan_strand=.1, stroming=.2)
    checks = [
     ("kalme dag: stille waters 4", strand_uur(kalm)["stille_waters"]["cijfer"] == 4),
     ("kalme dag: golf onder 3", strand_uur(kalm)["golf"]["cijfer"] < 3),
     ("kalme dag: wind onder 3", strand_uur(kalm)["wind"]["cijfer"] < 3),
     ("surfdag: stille waters onder 3", strand_uur(DAYS["Kleine schone deining"])["stille_waters"]["cijfer"] < 3),
     ("18 knopen: stille waters 0", strand_uur(DAYS["Vlak water, 18 knopen"])["stille_waters"]["cijfer"] == 0),
     ("kalm maar aflandig 9 knopen: stille waters onder 3", stille_waters(dict(kalm, wind=9, windhoek=170))["score"] < 60),
     ("kalm met onweer: stille waters 0", stille_waters(dict(kalm, onweer=True))["score"] == 0),
     ("reuzengolven 7 m 17 s: golf 0 en te_veel", (lambda r: r["golf"]["cijfer"] == 0 and r["golf"]["te_veel"] and r["te_gevaarlijk"])(
         strand_uur(dict(wind=10, vlaag=12, windhoek=170, golfhoogte=7, periode=17, golf_aan_strand=7)))),
     ("vlakke zee: golf 0 en niet te_veel", (lambda r: r["golf"]["cijfer"] == 0 and not r["golf"]["te_veel"] and not r["te_gevaarlijk"])(
         strand_uur(dict(wind=4, vlaag=5, windhoek=90, golfhoogte=0.2, periode=5, golf_aan_strand=0.2)))),
     ("3 m 15 s: golf 4 rood, niet te_veel", (lambda r: r["golf"]["cijfer"] == 4 and r["golf"]["rand"] == "rood" and not r["golf"]["te_veel"])(
         strand_uur(dict(wind=10, vlaag=12, windhoek=170, golfhoogte=3, periode=15, golf_aan_strand=3)))),
     ("filter beginner bij 1,6 m 12 s: golf 0 en te_veel", (lambda r: r["golf"]["cijfer"] == 0 and r["golf"]["te_veel"])(
         strand_uur(dict(wind=8, vlaag=10, windhoek=170, golfhoogte=1.6, periode=12, golf_aan_strand=1.6), "beginner"))),
     ("filter beginner bij 28 knopen: wind 0 en te_veel", (lambda r: r["wind"]["cijfer"] == 0 and r["wind"]["te_veel"])(
         strand_uur(dict(wind=28, vlaag=34, windhoek=90, golfhoogte=0.8, periode=5, golf_aan_strand=0.8), "beginner"))),
     ("6 knopen, filter ervaren: wind 0 en niet te_veel", (lambda r: r["wind"]["cijfer"] == 0 and not r["wind"]["te_veel"])(
         strand_uur(dict(wind=6, vlaag=8, windhoek=45, golfhoogte=0.2, periode=4, golf_aan_strand=0.2), "ervaren"))),
     ("45 knopen is storm", is_storm(dict(wind=45, vlaag=55))),
     ("34 knopen is geen storm", not is_storm(dict(wind=34, vlaag=42))),
     ("donker: elke categorie 0", all(score(k, dict(DAYS["Vlak water, 18 knopen"], donker=True))["score"] == 0 for k in CATEGORIES)),
     ("niveaufilter beginner bij 34 knopen: wind 0", strand_uur(DAYS["Storm, 34 knopen"], "beginner")["wind"]["cijfer"] == 0),
     ("niveaufilter ervaren bij 34 knopen: wind 4", strand_uur(DAYS["Storm, 34 knopen"], "ervaren")["wind"]["cijfer"] == 4),
    ]
    for name, good in checks:
        if not good: ok = False
        print(f"{name:55s} {'ok' if good else 'FOUT'}")
    print("\nALLES OK" if ok else "\nER ZIJN FOUTEN")
