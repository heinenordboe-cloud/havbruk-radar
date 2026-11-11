"""Måling: tidsaksens lag — hvor langt bakover, og med hvilken oppløsning.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \\
        .venv/bin/python analyse/tidsakse/m1_lag.py > analyse/tidsakse/m1_lag.txt

Svarer på punkt 1 i økt 7 for hvert lag tidsaksen skal bære. Leser
snapshotene gjennom lesedøra (`analyse.kjoringslogg`, som går gjennom
`snapshot._les()` og persondatafilteret), og arkivkroppene for lagene som
bare finnes der, med sha256 over den UTPAKKEDE kroppen.

Skriver ingenting utenom stdout og kjøringsloggen i `analyse/ut/`. Utskriften
er determinstisk: to kjøringer mot samme datarepo gir samme bytes.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROT))

from analyse import kjoringslogg                     # noqa: E402  (lesedøra)
from core import config, feltnormal, paths, snapshot  # noqa: E402
from sources import reguleringsomraader as regomr    # noqa: E402
from sources import trafikklysvedtak as tlv          # noqa: E402

UT = Path(__file__).resolve().parent
LOGG = kjoringslogg.Kjoringslogg(
    "tidsakse_m1_lag", ROT / "analyse" / "ut" / "tidsakse-m1_lag.kjoring.log")

AKSE_START = "2012-01-02"     # første uke i lusetall, mandag i uke 1/2012
EIERKOBLING_FRA = "2026-08-17"


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def kropp(rel: str) -> tuple[bytes, str]:
    """Arkivkroppen, utpakket, og sha256 over den."""
    fil = paths.ARKIV_DIR / rel
    b = gzip.open(fil, "rb").read() if fil.name.endswith(".gz") else fil.read_bytes()
    return b, sha_bytes(b)


def uke(d: str) -> str:
    aar, nr, _ = dt.date.fromisoformat(d[:10]).isocalendar()
    return f"{aar}-W{nr:02d}"


def mandag(d: str) -> str:
    x = dt.date.fromisoformat(d[:10])
    return (x - dt.timedelta(days=x.weekday())).isoformat()


def uker_mellom(a: str, b: str) -> list[str]:
    """Mandagene fra uka med a til uka med b, begge med."""
    x, y = dt.date.fromisoformat(mandag(a)), dt.date.fromisoformat(mandag(b))
    ut = []
    while x <= y:
        ut.append(x.isoformat())
        x += dt.timedelta(days=7)
    return ut


def fil_liste(kilde: str) -> tuple[int, str]:
    """(antall filer, sha256 over lista «sti<TAB>sha256 av fila\\n»).

    Filene hashes som bytes og leses ikke som parquet: innholdet går bare
    gjennom døra.
    """
    mappe = snapshot.RAW_DIR / kilde
    linjer = [f"raw/{kilde}/{p.name}\t{sha_bytes(p.read_bytes())}\n"
              for p in sorted(mappe.glob("*.parquet"))]
    return len(linjer), sha_bytes("".join(linjer).encode())


def gjeldende(versjoner: list) -> object:
    """Som `snapshot.gjeldende()`: nyeste hele, ellers nyeste."""
    hele = [r for r in versjoner if not snapshot.ufullstendig_i(r)]
    return (hele or versjoner)[-1]


def les_alle(kilde: str) -> dict[str, list]:
    """{dato: [ramme, …]} for hver versjon, eldst utgitt først."""
    per: dict[str, list] = defaultdict(list)
    for dato, ramme in LOGG.les(kilde, "0001-01-01", "9999-12-31",
                                versjonsvalg=kjoringslogg.ALLE):
        per[dato].append(ramme)
    return dict(per)


def felt(ramme, navn: str) -> dict[str, str]:
    """{entity_id: verdi} for ett felt."""
    r = ramme.filter(ramme["field"] == navn)
    return dict(zip(r["entity_id"].to_list(), r["value"].to_list()))


def skriv(*deler) -> None:
    print(*deler)


# ======================================================== 1. inventaret

KILDER = ["akvakultur", "eierskap", "eierskap_historikk", "enhetsregisteret",
          "enhetsregisteret_oppslag", "biomasselag", "biomasse", "lusetall",
          "sjotemperatur", "trafikklysvedtak", "ekspertgruppen",
          "reguleringsomraader", "unntaksvekst", "romming"]

skriv("# Måling: tidsaksens lag (analyse/tidsakse/m1_lag.py)")
skriv()
skriv("== 1. Snapshotene, gjennom lesedøra")
skriv("kilde | filer datoer | første siste | median dager mellom datoer | "
      "ufullstendige | entity_type | entiteter i siste | sha256 over fillista")
LEST: dict[str, dict[str, list]] = {}
for k in KILDER:
    alle = les_alle(k)
    LEST[k] = alle
    datoer = sorted(alle)
    n_filer, digest = fil_liste(k)
    gap = sorted((dt.date.fromisoformat(b) - dt.date.fromisoformat(a)).days
                 for a, b in zip(datoer, datoer[1:]))
    median = gap[len(gap) // 2] if gap else 0
    uf = sum(1 for d in datoer for r in alle[d] if snapshot.ufullstendig_i(r))
    siste = gjeldende(alle[datoer[-1]])
    typer = ",".join(sorted(set(siste["entity_type"].to_list())))
    skriv(f"{k} | {n_filer} {len(datoer)} | {datoer[0]} {datoer[-1]} | {median} | "
          f"{uf} | {typer} | {siste['entity_id'].n_unique()} | {digest}")

UKENTLIGE = ["akvakultur", "eierskap", "enhetsregisteret", "biomasselag",
             "lusetall", "sjotemperatur", "unntaksvekst"]
skriv()
skriv("-- ISO-uker uten snapshot mellom første og siste (ukentlige kilder)")
for k in UKENTLIGE:
    datoer = sorted(LEST[k])
    har = {mandag(d) for d in datoer}
    alle_uker = uker_mellom(datoer[0], datoer[-1])
    mangler = [uke(m) for m in alle_uker if m not in har]
    flere = Counter(mandag(d) for d in datoer)
    dobbel = sorted(uke(m) for m, n in flere.items() if n > 1)
    skriv(f"{k}: uker {len(alle_uker)} ({uke(datoer[0])}..{uke(datoer[-1])}), "
          f"med snapshot {len(har)}, uten {len(mangler)}: {', '.join(mangler) or '-'}; "
          f"uker med flere datoer: {', '.join(dobbel) or '-'}")

# ================================================ 2. registerets tilstand

skriv()
skriv("== 2. Registerets tilstand, PO, kommune (akvakultur)")
skriv("dato uke | lokaliteter | med kapasitet | med koordinater | med PO | med kommunenummer | "
      "med tillatelser | versjon_status (topp)")
for d in sorted(LEST["akvakultur"]):
    r = gjeldende(LEST["akvakultur"][d])
    ider = set(r["entity_id"].to_list())
    kap, br, po, kom, til = (felt(r, f) for f in
                             ("kapasitet", "breddegrad", "prodomraade_kode",
                              "kommunenummer", "tillatelser"))
    vs = Counter(felt(r, "versjon_status").values()).most_common(3)
    skriv(f"{d} {uke(d)} | {len(ider)} | {len(kap)} | {len(br)} | {len(po)} | {len(kom)} | "
          f"{len(til)} | {vs}")

siste_akva = gjeldende(LEST["akvakultur"][sorted(LEST["akvakultur"])[-1]])
po_av = felt(siste_akva, "prodomraade_kode")
status_av = felt(siste_akva, "prodomraade_status")
skriv("-- prodomraade_status per PO i siste akvakultursnapshot (registerets ord, ikke vedtaket)")
per_po: dict[str, Counter] = defaultdict(Counter)
for e, p in po_av.items():
    per_po[p][status_av.get(e, "(tom)")] += 1
for p in sorted(per_po, key=int):
    skriv(f"   PO {p}: {dict(sorted(per_po[p].items()))}")

skriv("-- første snapshotdato per kilde med en kobling lokalitet–tillatelse eller tillatelse–innehaver")
forste_til = min(d for d in LEST["akvakultur"]
                 if felt(gjeldende(LEST["akvakultur"][d]), "tillatelser"))
forste_eier = min(d for d in LEST["eierskap"]
                  if felt(gjeldende(LEST["eierskap"][d]), "eier_orgnr"))
skriv(f"   akvakultur.tillatelser: {forste_til} ({uke(forste_til)}); "
      f"eierskap.eier_orgnr: {forste_eier} ({uke(forste_eier)}); "
      f"før {EIERKOBLING_FRA}: "
      f"{sum(1 for k in ('akvakultur', 'eierskap') for d in LEST[k] if d < EIERKOBLING_FRA)} snapshots")

# ================================================= 3. tillatelser og eier

skriv()
skriv("== 3. Tillatelser, MTB og eier (eierskap)")
skriv("dato uke | tillatelser | med lokaliteter | lokaliteter koblet | eier_orgnr ulike | "
      "kapasitet_enhet | kapasitet_type")
for d in sorted(LEST["eierskap"]):
    r = gjeldende(LEST["eierskap"][d])
    lok = felt(r, "lokaliteter")
    koblet = {x.strip() for v in lok.values() for x in v.split(";") if x.strip()}
    eiere = set(felt(r, "eier_orgnr").values())
    enh = Counter(felt(r, "kapasitet_enhet").values())
    typ = Counter(felt(r, "kapasitet_type").values())
    skriv(f"{d} {uke(d)} | {r['entity_id'].n_unique()} | {len(lok)} | {len(koblet)} | "
          f"{len(eiere)} | {dict(sorted(enh.items()))} | {dict(sorted(typ.items()))}")

skriv("-- eierskap_historikk: overføringer per år (journal_dato), og spennet")
jd: list[str] = []
for d in sorted(LEST["eierskap_historikk"]):
    r = gjeldende(LEST["eierskap_historikk"][d])
    jd += [v for v in felt(r, "journal_dato").values() if v]
per_aar = Counter(v[:4] for v in jd)
skriv(f"   {len(jd)} overføringer, journal_dato {min(jd)}..{max(jd)}; "
      f"per år: {dict(sorted(per_aar.items()))}")

# =========================================================== 4. selskap

skriv()
skriv("== 4. Selskapsleddet (enhetsregisteret)")
felter_er = Counter()
for d in sorted(LEST["enhetsregisteret"]):
    for r in LEST["enhetsregisteret"][d]:
        felter_er.update(set(r["field"].to_list()))
overordnet = sorted(f for f in felter_er if "overordnet" in f or "forelder" in f
                    or "mor" == f or "konsern" in f)
skriv(f"   datoer {len(LEST['enhetsregisteret'])}, "
      f"{sorted(LEST['enhetsregisteret'])[0]}..{sorted(LEST['enhetsregisteret'])[-1]}; "
      f"ulike felt i alle versjoner: {len(felter_er)}")
skriv(f"   felt som nevner overordnet/forelder/konsern: {overordnet or '-'}")
siste_er = gjeldende(LEST["enhetsregisteret"][sorted(LEST["enhetsregisteret"])[-1]])
siste_eier = gjeldende(LEST["eierskap"][sorted(LEST["eierskap"])[-1]])
eier_orgnr = set(felt(siste_eier, "eier_orgnr").values())
i_er = eier_orgnr & set(siste_er["entity_id"].to_list())
skriv(f"   siste eierskap: {len(eier_orgnr)} innehavere, {len(i_er)} av dem i siste "
      f"enhetsregister-snapshot ({len(eier_orgnr) - len(i_er)} utenfor vårt utvalg)")

# =================================================== 5. reguleringsområde

skriv()
skriv("== 5. Reguleringsområde (punkt i polygon, sources.reguleringsomraader.inneholder)")
rd = sorted(LEST["reguleringsomraader"])
rr = gjeldende(LEST["reguleringsomraader"][rd[-1]])
versjon = sorted(set(felt(rr, "datasett_versjon").values()))
status = sorted(set(felt(rr, "status").values()))
omr: dict[str, list[tuple[float, float]]] = {}
for e, wkt in felt(rr, "geometri").items():
    tall = [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?", wkt)]
    omr[e] = list(zip(tall[0::2], tall[1::2]))
skriv(f"   snapshot {rd[-1]} ({uke(rd[-1])}), published_at {snapshot.published_at_i(rr) or '(tom)'}, "
      f"versjon {versjon}, status {status}, områder {len(omr)}")
br, le = felt(siste_akva, "breddegrad"), felt(siste_akva, "lengdegrad")
treff = Counter()
for e in sorted(br):
    inne = [o for o, pkt in omr.items()
            if regomr.inneholder(pkt, float(le[e]), float(br[e]))]
    treff[len(inne)] += 1
skriv(f"   siste akvakultur: lokaliteter med koordinater {len(br)}; i antall områder: "
      f"{dict(sorted(treff.items()))}")

# ============================================================ 6. trafikklys

skriv()
skriv("== 6. Trafikklys (trafikklysvedtak), per PO og tildelingsrunde")
for d in sorted(LEST["trafikklysvedtak"]):
    for r in LEST["trafikklysvedtak"][d]:
        farge = felt(r, "farge")
        skriv(f"   runde {d[:4]} | published_at {snapshot.published_at_i(r)} | PO med farge "
              f"{len(farge)}: " + ", ".join(f"{p}={farge[p]}" for p in sorted(farge, key=int)))
b26, h26 = kropp("trafikklysvedtak/2026-12-31.bin.gz")
flat = tlv._forskriftstekst(tlv._tekst(b26))
par4 = tlv._paragraf(flat, "4", "5")
ORDLYD = re.compile(r"Tillatelser hjemmehørende i øvrige produksjonsområder kan utnyttes 100 prosent\.")
ordlyd = ORDLYD.findall(par4)
gjeld = gjeldende(LEST["trafikklysvedtak"]["2026-12-31"])
farget_2026 = set(felt(gjeld, "farge"))
uten = [str(p) for p in range(1, tlv.ANTALL_PO + 1) if str(p) not in farget_2026]
skriv(f"   2026-kroppen trafikklysvedtak/2026-12-31.bin.gz sha256 {h26}")
skriv(f"   § 4 har setningen ordrett {len(ordlyd)} gang(er): {ordlyd[0] if ordlyd else '-'}")
skriv(f"   2026: PO uten farge i snapshotet: {', '.join(uten)} ({len(uten)} celler)")

# ============================================================ 7. biomasselag

skriv()
skriv("== 7. Biomasselaget: én påstand per lokalitet og månedsslutt (siste_rapport)")
krav: dict[tuple[str, str], tuple[str, str]] = {}
for d in sorted(LEST["biomasselag"]):
    r = gjeldende(LEST["biomasselag"][d])
    sr = felt(r, "siste_rapport")
    hf = felt(r, "har_fisk")
    for e, m in sr.items():
        krav[(e, m)] = (d, hf.get(e, ""))
    topp = Counter(sr.values()).most_common(3)
    skriv(f"   {d} {uke(d)}: lokaliteter {len(sr)}, siste_rapport topp {topp}")
alle_m = [m for (_, m) in krav]
i_aksen = [m for m in alle_m if m >= AKSE_START]
per_aar_m = Counter(m[:4] for m in alle_m)
skriv(f"   påstander (lokalitet, månedsslutt): {len(krav)}; månedsslutter {len(set(alle_m))}; "
      f"siste_rapport {min(alle_m)}..{max(alle_m)}; fra {AKSE_START}: {len(i_aksen)}, "
      f"før: {len(alle_m) - len(i_aksen)}")
skriv(f"   per år: {dict(sorted(per_aar_m.items()))}")
store = sorted((m, n) for m, n in Counter(alle_m).items() if n >= 100)
skriv(f"   månedsslutter med minst 100 lokaliteter: {store}")

# ===================================================== 8. lus og sjøtemperatur

skriv()
skriv("== 8. Lus, brakklegging, behandling (lusetall) og sjøtemperatur")
maks = int(config.get("kilder.lusetall.maks_nullstrekk",
                      feltnormal.STANDARD_MAKS_NULLSTREKK))
dodt_fra = config.get("kilder.lusetall.dodt_fra", {}) or {}
uker_lus = sorted(LEST["lusetall"])
skriv(f"   lusetall: {len(uker_lus)} uker {uker_lus[0]}..{uker_lus[-1]}; maks_nullstrekk {maks}; "
      f"dodt_fra {dict(sorted(dodt_fra.items()))}")
FLAGG = ("har_mekanisk_fjerning", "har_medikamentell_behandling", "har_rensefisk")
sann_i_univers: dict[str, list[bool]] = {f: [] for f in FLAGG}
for d in uker_lus:
    r = gjeldende(LEST["lusetall"][d])
    laks = felt(r, "har_laksefisk")
    land = felt(r, "er_landbasert")
    slakt = felt(r, "er_slaktemerd")
    univ = {e for e in laks if laks[e] == "True" and land.get(e) == "False"
            and slakt.get(e) == "False"}
    for f in FLAGG:
        v = felt(r, f)
        sann_i_univers[f].append(any(v.get(e) == "True" for e in univ))
for f in FLAGG:
    s = sann_i_univers[f]
    strekk, i = [], 0
    while i < len(s):
        if not s[i]:
            j = i
            while j < len(s) and not s[j]:
                j += 1
            if j - i > maks:
                strekk.append((uker_lus[i], uker_lus[j - 1], j - i))
            i = j
        else:
            i += 1
    lever = [u for k, u in enumerate(uker_lus)
             if not any(a <= u <= b for a, b, _ in strekk)]
    dod = dodt_fra.get(f)
    lever_dod = [u for u in lever if not dod or u < dod]
    sanne = [u for u, x in zip(uker_lus, s) if x]
    skriv(f"   {f}: første True {sanne[0] if sanne else '-'}, siste True {sanne[-1] if sanne else '-'}; "
          f"døde strekk > {maks}: {strekk or '-'}; lever etter regelen {len(lever)} uker "
          f"({lever[0]}..{lever[-1]}); med dodt_fra {len(lever_dod)} uker "
          f"({lever_dod[0]}..{lever_dod[-1]})")
uker_sjo = sorted(LEST["sjotemperatur"])
skriv(f"   sjotemperatur: {len(uker_sjo)} uker {uker_sjo[0]}..{uker_sjo[-1]}; "
      f"samme uker som lusetall: {uker_sjo == uker_lus}")
lus_ider = set()
for d in uker_lus:
    lus_ider |= set(gjeldende(LEST["lusetall"][d])["entity_id"].to_list())
skriv(f"   lokaliteter i noen lusetalluke: {len(lus_ider)}")

# ============================================================== 9. sykdom

skriv()
skriv("== 9. Sykdom (Mattilsynet, arkivkroppen; R5)")
bs, hs = kropp("maling-ilapd/2026-11-04.json.gz")
logg = json.loads((paths.ARKIV_DIR / "maling-ilapd/2026-11-04.i2.logg.json").read_text())
tilf = json.loads(bs)
ILA, PD = "INFEKSIØS_LAKSEANEMI", "PANKREASSYKDOM"
gyldige = [t for t in tilf if t.get("sykdomstype") in (ILA, PD)
           and not t.get("ugyldiggjøringsdato")]
opprettet = sorted(t["opprettet"] for t in tilf)
skriv(f"   maling-ilapd/2026-11-04.json.gz sha256 {hs}; hentet {logg[0]['fetched_at']}; "
      f"tilfeller {len(tilf)}; gyldige ILA "
      f"{sum(1 for t in gyldige if t['sykdomstype'] == ILA)}, gyldige PD "
      f"{sum(1 for t in gyldige if t['sykdomstype'] == PD)}")
skriv(f"   tidligste opprettet {opprettet[0]} ({uke(opprettet[0])}); "
      f"lokaliteter med gyldig ILA/PD {len({t['lokalitetsnummer'] for t in gyldige})}; "
      f"av dem i noen lusetalluke {len({str(t['lokalitetsnummer']) for t in gyldige} & lus_ider)}")
siste_lusuke = {}
for d in uker_lus:
    for e in gjeldende(LEST["lusetall"][d])["entity_id"].to_list():
        siste_lusuke[e] = d
akva_ider = set(siste_akva["entity_id"].to_list())
apne_pd = sorted({str(t["lokalitetsnummer"]) for t in gyldige
                  if t["sykdomstype"] == PD and not t.get("avslutningsdato")
                  and str(t["lokalitetsnummer"]) not in akva_ider})
skriv(f"   åpne PD-saker på lokaliteter som ikke står i siste akvakultursnapshot: "
      + ", ".join(f"{e} (siste lusetalluke {siste_lusuke.get(e, '-')})" for e in apne_pd))

# ======================================================== 10. unntaksvekst

skriv()
skriv("== 10. Unntaksvekst (unntaksvekst)")
for d in sorted(LEST["unntaksvekst"]):
    r = gjeldende(LEST["unntaksvekst"][d])
    nr = felt(r, "lokalitet_nr")
    res = Counter(felt(r, "resultat").values())
    kob = Counter(felt(r, "lokalitet_kobling").values())
    skriv(f"   {d} {uke(d)}: søknadslokaliteter {r['entity_id'].n_unique()}, med lokalitet_nr "
          f"{len(nr)}, ulike lokaliteter {len(set(nr.values()))}; resultat {dict(sorted(res.items()))}; "
          f"kobling {dict(sorted(kob.items()))}")

# ======================================== 11. lagene som bare er arkivkropper

skriv()
skriv("== 11. Lagene som bare finnes som arkivkropper (ingen kilde i sources/)")


def mappe(navn: str) -> list[Path]:
    m = paths.ARKIV_DIR / navn
    return sorted(m.iterdir()) if m.exists() else []


for navn in ("auksjon", "havbruksfondet", "lusetall-innkomst", "lusetall-innkomst-v2",
             "akvakultur-flater", "akvakultur-soknader", "maling-nye-kilder"):
    filer = mappe(navn)
    kropper = [f for f in filer if ".logg." not in f.name]
    logger = [f for f in filer if ".logg." in f.name]
    datoer = sorted({f.name[:10] for f in kropper})
    skriv(f"   {navn}: kropper {len(kropper)}, logger {len(logger)}, "
          f"datoer i filnavn {datoer[0] if datoer else '-'}..{datoer[-1] if datoer else '-'} "
          f"({len(datoer)})")

skriv("-- lusetall-innkomst (v1) og -v2: uker og hentinger, fra fangstloggene")
for navn in ("lusetall-innkomst", "lusetall-innkomst-v2"):
    hentet: dict[str, list[str]] = defaultdict(list)
    for f in mappe(navn):
        if not f.name.endswith(".logg.json") or ".fangst." not in f.name:
            continue
        for post in json.loads(f.read_text()).get("uker", []):
            if post.get("observed_at") and post.get("fetched_at"):
                hentet[post["observed_at"]].append(post["fetched_at"])
    uker = sorted(hentet)
    if uker:
        skriv(f"   {navn}: uker i fangstloggene {len(uker)} ({uker[0]}..{uker[-1]}); "
              f"hentinger {sum(len(v) for v in hentet.values())}; første henting "
              f"{min(min(v) for v in hentet.values())}, siste {max(max(v) for v in hentet.values())}")
    else:
        skriv(f"   {navn}: ingen uker i fangstloggene")

skriv()
skriv("== 12. Kroppene bak påstandene som holdes mot arkivet")
lusk = sorted((paths.ARKIV_DIR / "lusetall").glob("*.json.gz"))
liste = "".join(f"lusetall/{p.name}\t{kropp('lusetall/' + p.name)[1]}\n" for p in lusk)
skriv(f"   arkiv/lusetall: {len(lusk)} kropper, {lusk[0].name}..{lusk[-1].name}; "
      f"sha256 over lista «sti<TAB>sha256\\n» {sha_bytes(liste.encode())}")
for rel in ("lusetall/2026-03-02.json.gz", "lusetall/2026-03-09.json.gz"):
    b, h = kropp(rel)
    nr = {str(x.get("localityNo")) for x in json.loads(b).get("localities", [])}
    skriv(f"   {rel} sha256 {h}: lokaliteter {len(nr)}; av de fire med åpen PD: "
          f"{sorted(set(apne_pd) & nr) or '-'}")
b, h = kropp("akvakultur/2026-11-09.json.gz")
sites = {str(x.get("siteNr")) for x in json.loads(b)}
skriv(f"   akvakultur/2026-11-09.json.gz sha256 {h}: lokaliteter {len(sites)}; av de fire: "
      f"{sorted(set(apne_pd) & sites) or '-'}")
for navn in ("akvakultur", "eierskap"):
    forste = sorted(p.name for p in (paths.ARKIV_DIR / navn).glob("*.json.gz"))[0]
    skriv(f"   arkiv/{navn}: første kropp {forste}")

skriv()
skriv("== 13. Parene i R2 (REGLER.md) mot feltene i snapshotene")
FELT_I = {k: sorted(set(gjeldende(LEST[k][sorted(LEST[k])[-1]])["field"].to_list()))
          for k in ("lusetall", "sjotemperatur")}
for k, f in FELT_I.items():
    skriv(f"   {k}: {', '.join(f)}")
PAR = [("P1 eier", "eierskap: eier_navn, organisasjonsform", "enhetsregisteret: navn, organisasjonsform"),
       ("P2 tillatelser", "akvakultur: tillatelser", "eierskap: lokaliteter"),
       ("P3 fisk/brakk", "biomasselag: har_fisk, arter_tilstede, siste_rapport", "lusetall: brakklagt"),
       ("P4 koordinater", "akvakultur: breddegrad, lengdegrad", "lusetall: (lat, lon finnes ikke)"),
       ("P5 kommune", "akvakultur: kommunenummer", "lusetall: (municipalityNo finnes ikke)"),
       ("P6 PO", "akvakultur: prodomraade_kode", "sjotemperatur: (ProduksjonsområdeId finnes ikke)")]
for par, a, bb in PAR:
    skriv(f"   {par:16s} A {a:56s} B {bb}")

skriv()
skriv("== 14. Dekningen per lag, oppsummert (MÅLBAR av tabellene over)")
LAG = [
    ("registerets tilstand", "akvakultur", "uke", sorted(LEST["akvakultur"])),
    ("tillatelser, MTB, eier", "eierskap", "uke", sorted(LEST["eierskap"])),
    ("selskap", "enhetsregisteret", "uke", sorted(LEST["enhetsregisteret"])),
    ("lus, brakk, behandling", "lusetall", "uke", uker_lus),
    ("sjøtemperatur, lusegrense", "sjotemperatur", "uke", uker_sjo),
    ("biomasselaget", "biomasselag", "henting uke / påstand måned", sorted(LEST["biomasselag"])),
    ("trafikklys", "trafikklysvedtak", "runde (2 år)", sorted(LEST["trafikklysvedtak"])),
    ("reguleringsområde", "reguleringsomraader", "én versjon", rd),
    ("unntaksvekst", "unntaksvekst", "uke", sorted(LEST["unntaksvekst"])),
]
for navn, kilde, oppl, datoer in LAG:
    skriv(f"   {navn:28s} {kilde:20s} {oppl:28s} {datoer[0]}..{datoer[-1]} "
          f"({len(datoer)} datoer)")

LOGG.skriv()
