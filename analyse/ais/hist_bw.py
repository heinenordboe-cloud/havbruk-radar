"""Henter et tidsrom fra BarentsWatchs historikk-API slik en hulljeger måtte:
først hvilke MMSI som var i området (`mmsiinarea`), så sporet til hver av
dem (`tracks/{mmsi}/{fra}/{til}`). Måler hva det koster.

Kjøres på kystvakt-1 som brukeren `ais`. Ett kall om gangen, med pause,
slik BarentsWatch ber om for satsvise nedlastinger (developer-
dokumentasjonen, «Performance limitations»).

Hvert svar lagres uendret som en JSON-linje med vår tid ved siden av:

    {"t": <vår tid før kallet>, "kall": ..., "status": ..., "s": <sekunder>,
     "body": <svaret slik det kom, som tekst>}

    python3 hist_bw.py <fra ISO> <til ISO> <ut.jsonl> [pause_s] [maks_mmsi]

Området er omsluttende rektangel rundt `/v1/openaisarea`, som også
lagres. Filtrering av satellittposisjoner er slått AV
(`filterSatellitePositions=false`): vi vil ha alt kilden har.
"""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

NOKKEL = "/etc/kystvakt/barentswatch-ais.env"
TOKEN_URL = "https://id.barentswatch.no/connect/token"
LIVE = "https://live.ais.barentswatch.no"
HIST = "https://historic.ais.barentswatch.no"


def naa() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class Token:
    def __init__(self):
        self.verdi, self.utloper = None, 0.0

    def hent(self, forny=False) -> str:
        # Veggklokke: om tokenet er utløpt, handler om verden (F13).
        if forny or not self.verdi or time.time() > self.utloper:
            env = dict(l.split("=", 1) for l in open(NOKKEL).read().splitlines() if "=" in l)
            data = urllib.parse.urlencode({
                "client_id": env["BW_AIS_CLIENT_ID"],
                "client_secret": env["BW_AIS_CLIENT_SECRET"],
                "grant_type": "client_credentials", "scope": "ais"}).encode()
            with urllib.request.urlopen(TOKEN_URL, data, timeout=30) as r:
                d = json.load(r)
            self.verdi = d["access_token"]
            self.utloper = time.time() + int(d.get("expires_in", 3600)) - 120
        return self.verdi


def kall(tok: Token, ut, navn: str, url: str, body: dict | None = None):
    for forsok in (1, 2):
        hdr = {"Authorization": "Bearer " + tok.hent(forny=forsok == 2)}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            hdr["Content-Type"] = "application/json"
        t, t0 = naa(), time.monotonic()  # varighet handler om oss: monotonic
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data, hdr), timeout=120) as r:
                status, tekst = r.status, r.read().decode()
        except urllib.error.HTTPError as e:
            status, tekst = e.code, e.read().decode(errors="replace")
        except Exception as e:  # noqa: BLE001 — logges som et svar uten status
            status, tekst = None, repr(e)
        s = time.monotonic() - t0
        ut.write(json.dumps({"t": t, "kall": navn, "status": status, "s": round(s, 3),
                             "body": tekst}) + "\n")
        ut.flush()
        if status != 401:
            return status, tekst
    return status, tekst


def main() -> None:
    fra, til, sti = sys.argv[1], sys.argv[2], sys.argv[3]
    pause = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
    maks = int(sys.argv[5]) if len(sys.argv) > 5 else None  # bare for prøver
    tok = Token()
    with open(sti, "a") as ut:
        status, tekst = kall(tok, ut, "openaisarea", f"{LIVE}/v1/openaisarea")
        omr = json.loads(tekst)
        pkt = [p for poly in omr["coordinates"] for ring in poly for p in ring]
        lo0, lo1 = min(p[0] for p in pkt), max(p[0] for p in pkt)
        la0, la1 = min(p[1] for p in pkt), max(p[1] for p in pkt)
        rekt = {"type": "Polygon", "coordinates": [[[lo0, la0], [lo1, la0], [lo1, la1],
                                                     [lo0, la1], [lo0, la0]]]}
        status, tekst = kall(tok, ut, "mmsiinarea", f"{HIST}/v1/historic/mmsiinarea",
                             {"polygon": rekt, "msgTimeFrom": fra, "msgTimeTo": til})
        if status != 200:
            print(f"mmsiinarea: {status} {tekst[:300]}", file=sys.stderr)
            sys.exit(1)
        mmsier = json.loads(tekst)[:maks]
        print(f"{len(mmsier)} MMSI i området {fra}–{til}", file=sys.stderr, flush=True)
        f, t = urllib.parse.quote(fra), urllib.parse.quote(til)
        for i, m in enumerate(mmsier, 1):
            time.sleep(pause)
            kall(tok, ut, f"tracks {m}",
                 f"{HIST}/v1/historic/tracks/{m}/{f}/{t}"
                 "?modelFormat=Json&filterSatellitePositions=false")
            if i % 250 == 0:
                print(f"{naa()} {i}/{len(mmsier)}", file=sys.stderr, flush=True)
        print(f"{naa()} ferdig", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
