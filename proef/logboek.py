"""HTTP met wachttijd per host, en het logboek (results/run_log.md)."""

import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

WACHT_S = 1.0


class Logboek:
    def __init__(self):
        self.start = datetime.now(timezone.utc)
        self.regels: list[str] = []
        self.aanvragen = Counter()  # per host
        self.gewicht_open_meteo = 0.0
        self.weggefilterd = defaultdict(Counter)  # bron -> reden -> aantal
        self.na_te_gaan: list[tuple[str, str, str]] = []  # (punt, status, antwoord)
        self._laatst: dict[str, float] = {}
        self.sessie = requests.Session()
        self.sessie.headers["User-Agent"] = "golfkaart-proef/1.0 (github.com/matticett/portugalautumn2026)"

    def info(self, tekst: str):
        stempel = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.regels.append(f"- {stempel} {tekst}")
        print(tekst, flush=True)

    def antwoord(self, punt: str, opgelost: bool, antwoord: str):
        self.na_te_gaan.append((punt, "opgelost" if opgelost else "NIET OPGELOST", antwoord))
        self.info(f"NA TE GAAN · {punt}: {antwoord}")

    def filter(self, bron: str, reden: str, aantal: int):
        if aantal:
            self.weggefilterd[bron][reden] += int(aantal)

    def get(self, url: str, params=None, timeout=120, pogingen=4) -> requests.Response:
        """GET met minstens 1 s tussen aanvragen naar dezelfde host en herhaling bij 429/5xx."""
        host = urlparse(url).netloc
        for poging in range(pogingen):
            wacht = WACHT_S - (time.monotonic() - self._laatst.get(host, 0))
            if wacht > 0:
                time.sleep(wacht)
            self._laatst[host] = time.monotonic()
            self.aanvragen[host] += 1
            try:
                r = self.sessie.get(url, params=params, timeout=timeout)
            except requests.RequestException as e:
                if poging == pogingen - 1:
                    raise
                self.info(f"netwerkfout {host}: {e}; opnieuw")
                time.sleep(2 ** (poging + 1))
                continue
            if r.status_code in (429, 500, 502, 503, 504) and poging < pogingen - 1:
                self.info(f"{host} gaf {r.status_code}; opnieuw na {2 ** (poging + 2)} s")
                time.sleep(2 ** (poging + 2))
                continue
            return r
        return r
