"""Fanger Kystverkets åpne AIS-strøm rått i et gitt antall sekunder.

Kjøres på kystvakt-1. Ingen dekoding her: hver linje skrives uendret,
med VÅR mottakstid foran og en tabulator imellom. Kildens egen klokke
står i c:-feltet inne i linja (CLAUDE.md 1b-7: to klokker, to eiere).

    <mottatt UTC, ISO, mikrosek>\t<linja slik den kom, med terminator>

Sammenføyer du alt etter første tabulator, får du byte-strømmen tilbake.
Brudd og gjenoppkoblinger logges som JSON-linjer i en egen fil.

    python3 fang.py <sekunder> <ut.txt> <hendelser.jsonl> [port]

Port 5631 er den Kystverket dokumenterer. 5632 er udokumentert (sett
28.10.2026: satellittkilder, s:NorSat_*), og måles bare ved siden av.
"""
import json
import socket
import sys
import time
from datetime import datetime, timezone

VERT = "153.44.253.27"
TIDSAVBRUDD = 120  # s uten data regnes som brudd


def naa() -> str:
    # Veggklokke: mottakstid handler om verden (1b-1), ikke om prosessen.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def main() -> None:
    varighet, ut_sti, hend_sti = float(sys.argv[1]), sys.argv[2], sys.argv[3]
    port = int(sys.argv[4]) if len(sys.argv) > 4 else 5631
    slutt = time.monotonic() + varighet  # hvor lenge VI kjører: monotonic
    with open(ut_sti, "ab") as ut, open(hend_sti, "a") as hend:
        def logg(**k):
            hend.write(json.dumps({"t": naa(), **k}) + "\n")
            hend.flush()

        logg(hendelse="start", varighet_s=varighet, vert=VERT, port=port)
        while time.monotonic() < slutt:
            try:
                s = socket.create_connection((VERT, port), timeout=15)
            except OSError as e:
                logg(hendelse="tilkobling_feilet", feil=repr(e))
                time.sleep(5)
                continue
            s.settimeout(TIDSAVBRUDD)
            logg(hendelse="tilkoblet")
            buf = b""
            mottatt = 0
            try:
                while time.monotonic() < slutt:
                    bit = s.recv(65536)
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
            except OSError as e:
                logg(hendelse="brudd", grunn=repr(e), bytes=mottatt)
            finally:
                if buf:
                    logg(hendelse="ufullstendig_hale", bytes=len(buf))
                ut.flush()
                s.close()
            if time.monotonic() < slutt:
                time.sleep(1)
        logg(hendelse="ferdig")


if __name__ == "__main__":
    main()
