"""Hvor data havner. Ett sted, ikke fire.

Koden og dataene bor i hver sitt repo:

    havbruk-radar        offentlig, kode. Viser håndverket.
    havbruk-radar-data   privat, historikk. Fortrinnet.

Registerdataene er NLOD-lisensiert og kan hentes av hvem som helst i
morgen. Det som ikke kan hentes i morgen, er snapshotet fra 17.08.2026.
Tid er den eneste ressursen som ikke lar seg kopiere i etterkant, og
derfor er det historikken som ligger privat — ikke tallene.

Sett HAVBRUK_DATA_DIR for å skrive et annet sted. Uten den skrives det
til `data/` ved siden av koden, som er det du vil ha når du kjører
lokalt uten å tenke på det.
"""

import os
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent

DATA_DIR = Path(os.environ.get("HAVBRUK_DATA_DIR") or (ROT / "data")).resolve()

RAW_DIR = DATA_DIR / "raw"
ARKIV_DIR = DATA_DIR / "arkiv"
CHANGELOG_DIR = DATA_DIR / "changelog"
HEALTH_PATH = DATA_DIR / "health.json"
COMMIT_MSG_PATH = DATA_DIR / "siste_kjoring.txt"

# Fra da endringsloggen lå i én fil. Leses fortsatt, skrives aldri til.
GAMMEL_CHANGELOG = DATA_DIR / "changelog.parquet"
