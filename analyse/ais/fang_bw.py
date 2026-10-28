"""Fanger BarentsWatchs Live AIS-strøm (GET /v1/ais) rått i et gitt antall sekunder.

Kjøres på kystvakt-1 som brukeren `ais`, som eier nøkkelfila. Strømmen
er JSON, én melding per linje (OpenAPI: «Messages are separated by line
breaks»). Ingen dekoding her: hver linje skrives uendret, med VÅR
mottakstid foran og en tabulator imellom, samme format som fang.py.
Kildens klokke står i `msgtime` inne i linja (CLAUDE.md 1b-7).

    <mottatt UTC, ISO, mikrosek>\t<linja slik den kom>

Tokenet hentes ved hver tilkobling og logges aldri. Brudd og
gjenoppkoblinger logges som JSON-linjer i en egen fil.

    python3 fang_bw.py <sekunder> <ut.txt> <hendelser.jsonl>
"""
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

NOKKEL = "/etc/kystvakt/barentswatch-ais.env"
TOKEN_URL = "https://id.barentswatch.no/connect/token"
STROM_URL = "https://live.ais.barentswatch.no/v1/ais"
TIDSAVBRUDD = 120  # s uten data regnes som brudd


def naa() -> str:
    # Veggklokke: mottakstid handler om verden (1b-1), ikke om prosessen.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def token() -> str:
    env = dict(l.split("=", 1) for l in open(NOKKEL).read().splitlines() if "=" in l)
    data = urllib.parse.urlencode({
        "client_id": env["BW_AIS_CLIENT_ID"],
        "client_secret": env["BW_AIS_CLIENT_SECRET"],
        "grant_type": "client_credentials",
        "scope": "ais",
    }).encode()
    with urllib.request.urlopen(TOKEN_URL, data, timeout=30) as r:
        return json.load(r)["access_token"]


def main() -> None:
    varighet, ut_sti, hend_sti = float(sys.argv[1]), sys.argv[2], sys.argv[3]
    slutt = time.monotonic() + varighet  # hvor lenge VI kjører: monotonic
    with open(ut_sti, "ab") as ut, open(hend_sti, "a") as hend:
        def logg(**k):
            hend.write(json.dumps({"t": naa(), **k}) + "\n")
            hend.flush()

        logg(hendelse="start", varighet_s=varighet, url=STROM_URL)
        while time.monotonic() < slutt:
            try:
                req = urllib.request.Request(
                    STROM_URL, headers={"Authorization": "Bearer " + token()})
                r = urllib.request.urlopen(req, timeout=TIDSAVBRUDD)
            except Exception as e:  # noqa: BLE001 — alt logges, ingenting stopper fangsten
                logg(hendelse="tilkobling_feilet", feil=repr(e)[:300])
                time.sleep(5)
                continue
            logg(hendelse="tilkoblet", status=r.status,
                 headers={k: v for k, v in r.headers.items()
                          if k.lower() not in ("set-cookie",)})
            mottatt = 0
            buf = b""
            try:
                while time.monotonic() < slutt:
                    bit = r.read1(65536)
                    if not bit:
                        logg(hendelse="brudd", grunn="eof", bytes=mottatt)
                        break
                    mottatt += len(bit)
                    t = naa().encode()
                    buf += bit
                    *hele, buf = buf.split(b"\n")
                    for linje in hele:
                        ut.write(t + b"\t" + linje + b"\n")
                else:
                    logg(hendelse="slutt", bytes=mottatt)
            except Exception as e:  # noqa: BLE001
                logg(hendelse="brudd", grunn=repr(e)[:300], bytes=mottatt)
            finally:
                if buf:
                    logg(hendelse="ufullstendig_hale", bytes=len(buf))
                ut.flush()
                r.close()
            if time.monotonic() < slutt:
                time.sleep(1)
        logg(hendelse="ferdig")


if __name__ == "__main__":
    main()
