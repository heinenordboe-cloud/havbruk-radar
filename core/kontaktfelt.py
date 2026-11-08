"""Kontaktfelt i et råsvar: hvilke nøkler som ikke skal inn i rå-arkivet.

Regel 3 gjelder rå-arkivet like mye som snapshotene. Fram til 09.11.2026
lagret `enhetsregisteret` hele Brreg-svaret i `data/arkiv/`, og fila fra
02.11.2026 hadde 1 655 gateadresser, 455 telefonnumre, 332 mobilnumre,
439 e-postadresser og 183 hjemmesider. Feltvalget i `FELTER` holdt dem
ute av snapshotet, men ikke av kroppen.

## Hvorfor dette ikke står i core/persondata.py

Det gjorde det, fra bcd4221 (07.11.2026). `raw.arkiver()`,
`raw.arkiver_ny()` og `karantene.sett_inn()` importerte da persondata for
vakten, og persondata importerer polars. `ais_manifest.py` går gjennom
karantene og kjøres av ais-manifest.yml uten installerte pakker: den feilet
med ModuleNotFoundError 07.11 og 08.11, og status.json ble stående fra
06.11.

De to modulene svarer på hvert sitt spørsmål. persondata spør hvilke
ENHETER som er personer, og leser snapshotrammer. Denne spør hvilke
NØKLER i en JSON-kropp som peker på et menneske eller en kontaktkanal,
og trenger ikke annet enn standardbiblioteket. Arkivtrakta skal kunne
importeres der ingen pakker er installert, og derfor importerer denne
modulen bare standardbiblioteket.
"""

# Lista er Brregs egne feltnavn, målt på et arkivert svar 07.11.2026 (alle
# 73 feltstier i 1 805 enheter). Bare disse kan peke på et menneske eller
# en kontaktkanal; resten er register- og regnskapsdata. Adresseobjektet
# beholdes uten adresselinjene: `kommune`, `kommunenummer`, `postnummer`,
# `poststed`, `landkode` og `land` er geografien snapshotet bruker.
KONTAKTFELT = frozenset({"telefon", "mobil", "epostadresse", "hjemmeside"})

# Brregs adresseobjekter, og nøkkelen som bærer gate eller postboks i dem.
# `beliggenhetsadresse` står på underenheter; den er med så en kilde som
# begynner å hente dem, møter vakten i stedet for å slippe gjennom.
ADRESSEOBJEKTER = frozenset({"forretningsadresse", "postadresse",
                             "beliggenhetsadresse"})
ADRESSELINJE = "adresse"


def _har_verdi(v: object) -> bool:
    return v not in (None, "", [], {})


def uten_kontaktfelt(enhet: dict) -> tuple[dict, list[str]]:
    """En kopi av enheten uten kontaktfeltene, og hvilke stier som ble
    fjernet. Originalen røres ikke.

    Bare toppnivået og de tre adresseobjektene ses på. Det er der Brreg
    legger dem, og en dypere vask ville vært en gjetning om felt ingen
    har sett. Vakten under går derimot gjennom HELE kroppen: det er den
    som skal fange det denne ikke vet om.
    """
    ut = dict(enhet)
    fjernet: list[str] = []
    for felt in sorted(KONTAKTFELT):
        if felt in ut:
            if _har_verdi(ut[felt]):
                fjernet.append(felt)
            del ut[felt]
    for obj in sorted(ADRESSEOBJEKTER):
        a = ut.get(obj)
        if isinstance(a, dict) and ADRESSELINJE in a:
            if _har_verdi(a[ADRESSELINJE]):
                fjernet.append(f"{obj}.{ADRESSELINJE}")
            ut[obj] = {k: v for k, v in a.items() if k != ADRESSELINJE}
    return ut, fjernet


def kontaktfelt_i(raw: object) -> dict[str, int]:
    """Hvor mange ganger hvert kontaktfelt står med en verdi, hvor som
    helst i en JSON-kropp. Tom dict betyr at kroppen er ren.

    Leter etter NØKLENE, ikke etter noe som ser ut som et telefonnummer.
    Det er grensa for hva prøven kan love: et nummer i fritekst går forbi
    (se `sources/romming.py`, som har sin egen vakt for det).
    """
    ut: dict[str, int] = {}

    def gaa(o: object) -> None:
        if isinstance(o, dict):
            for k, v in o.items():
                if k in KONTAKTFELT and _har_verdi(v):
                    ut[k] = ut.get(k, 0) + 1
                elif (k in ADRESSEOBJEKTER and isinstance(v, dict)
                      and _har_verdi(v.get(ADRESSELINJE))):
                    n = f"{k}.{ADRESSELINJE}"
                    ut[n] = ut.get(n, 0) + 1
                gaa(v)
        elif isinstance(o, list):
            for x in o:
                gaa(x)

    gaa(raw)
    return dict(sorted(ut.items()))


def nekt_kontaktfelt(kilde: str, raw: object) -> None:
    """Kaster hvis en kropp som skal arkiveres har kontaktfelt.

    Samme rolle for rå-arkivet som `snapshot._nekt_personformer()` har for
    snapshotene: filteret i kilden er der feltene faktisk holdes ute, og
    dette er trakta alt skrives gjennom, for den kilden som glemmer det.

    Bare strukturerte kropper (dict og list) prøves. Bytes og tekst er
    PDF, HTML, regneark og XML, og der er en nøkkel ikke en nøkkel. Målt
    07.11.2026: ingen av de strukturerte kroppene i noen annen arkivmappe
    har noen av feltene, så vakten stopper bare `enhetsregisteret`.
    """
    if not isinstance(raw, (dict, list)):
        return
    funn = kontaktfelt_i(raw)
    if funn:
        detaljer = ", ".join(f"{k} {n}" for k, n in funn.items())
        raise ValueError(
            f"{kilde}: kroppen har kontaktfelt ({detaljer}) og arkiveres "
            f"ikke. Regel 3: adresser, telefon og e-post hentes ikke inn, "
            f"heller ikke til rå-arkivet. Fjern dem i kildens fetch() med "
            f"kontaktfelt.uten_kontaktfelt() — ikke her.")
