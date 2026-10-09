"""Punkt 3: tillatelseshandel siste 12 måneder per produksjonsområde.

To ledd, begge målt mot arkivkroppene:
  A. data/arkiv/eierskap-overforinger/<nr>.json.gz  (transfers-kjeden,
     hentet ca. 01.-02.09.2026; ajourDate står i kroppen)
  B. data/arkiv/eierskap/<dato>.json.gz  (ukentlig eier per tillatelse,
     02.09 -> 05.10.2026): eierskifte = annet openLegalEntityNr

Selger i ledd A er forrige mottaker i kjeden, eller den opprinnelig
tildelte for første overføring. Persondatafilteret går på ALT: en part
uten kjent selskapsform, med personform eller uten ni-sifret nummer
holder hele overføringen utenfor. Navn på slike parter skrives aldri ut.

Kapasitet og PO er DAGENS (eierskapskroppen 05.10.2026), ikke verdien da
overføringen skjedde. Summeres bare innen samme enhet.
"""
import collections
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path

import polars as pl

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from sources.eierskap import er_person  # noqa: E402

D = Path(os.environ.get("HAVBRUK_DATA_DIR", "../havbruk-radar-data/data"))
FRA, TIL = "2025-10-08", "2026-10-08"   # [FRA, TIL)
SELSKAP = {"LimitedLiabilityCompany", "PublicLimitedCompany", "AS", "ASA"}
UT = Path("/tmp/maling-okt/p3"); UT.mkdir(parents=True, exist_ok=True)


def kropp(sti):
    b = gzip.open(sti, "rb").read()
    return hashlib.sha256(b).hexdigest(), json.loads(b)


# --- typekart: orgnr -> form, fra alle kilder vi har kropper for
form: dict[str, str] = {}
for f in sorted((D / "arkiv/eierskap").glob("*.json.gz")):
    for e in kropp(f)[1].get("enheter") or []:
        if e.get("openNr"):
            form[str(e["openNr"])] = e.get("typeValue")
for f in (D / "arkiv/eierskap-brreg").glob("*.json.gz"):
    d = kropp(f)[1]
    if d.get("status") == "ok":
        form.setdefault(str(d["organisasjonsnummer"]), d.get("organisasjonsform"))
hist = pl.concat([pl.read_parquet(f) for f in (D / "raw/eierskap_historikk").glob("*.parquet")])
for orgnr, t in hist.filter(pl.col("field").is_in(["mottaker_orgnr", "mottaker_type"])).pivot(
        on="field", index="entity_id", values="value", aggregate_function="first"
        ).select("mottaker_orgnr", "mottaker_type").iter_rows():
    form.setdefault(orgnr, t)


# Brreg i MINNET for numre vi ikke kjenner formen til (oppløste selskaper).
# Ingenting skrives til disk; personformer blir bare en telling.
BRREG_STATUS = collections.Counter()


def brreg_slaa_opp(numre):
    import time
    import httpx
    from sources.eierskap import Eierskap
    e = Eierskap()
    with httpx.Client(timeout=30) as c:
        for nr in sorted(numre):
            d = e.brreg_form(nr, c)
            BRREG_STATUS[d["status"]] += 1
            if d["status"] == "ok":
                form[nr] = d["organisasjonsform"]
            time.sleep(e.BRREG_PAUSE_S)


def klasse(orgnr):
    orgnr = (orgnr or "").strip()
    if not re.fullmatch(r"\d{9}", orgnr):
        return "person_eller_uten_nr"
    t = form.get(orgnr)
    if not t:
        return "ukjent_form"
    if er_person(t) or t in ("Person", "SoleProprietorship"):
        return "personform"
    return "selskap" if t in SELSKAP else f"annen_form:{t}"


# --- dagens tillatelser (PO, kapasitet, tildelt) fra siste kropp
siste = sorted((D / "arkiv/eierskap").glob("*.json.gz"))
h_siste, b_siste = kropp(siste[-1])
lis = {l["licenseNr"]: l for l in b_siste["tillatelser"]}
for f in reversed(siste[:-1]):   # utgåtte tillatelser: eldre kropper
    for l in kropp(f)[1]["tillatelser"]:
        lis.setdefault(l["licenseNr"], l)


h_akva, sites = kropp(sorted((D / "arkiv/akvakultur").glob("*.json.gz"))[-1])
site_po = {}
lis_site = collections.defaultdict(set)
for st in sites:
    site_po[st["siteNr"]] = (st.get("placement") or {}).get("prodAreaCode")
    for k in st.get("connections") or []:
        if k.get("active"):
            lis_site[k["licenseNr"]].add(st["siteNr"])


def po(nr):
    """Tillatelsens egen PO, ellers PO-ene til lokalitetene den er koblet til."""
    l = lis.get(nr)
    egen = ((l or {}).get("placement") or {}).get("prodAreaCode")
    if egen:
        return str(egen)
    via = {site_po.get(s) for s in lis_site.get(nr, ())} - {None}
    if len(via) == 1:
        return f"{via.pop()} (via lokalitet)"
    return "flere" if via else "uten PO"


def ttype(nr):
    return ((lis.get(nr) or {}).get("type") or {}).get("tag") or "ukjent"


def kap(nr):
    c = (lis.get(nr) or {}).get("capacity") or {}
    return c.get("current"), c.get("unit")


ukjente = set()
for f in (D / "arkiv/eierskap-overforinger").glob("*.json.gz"):
    tr = kropp(f)[1].get("transfers") or []
    for i, t in enumerate(tr):
        if FRA <= str(t.get("journalDate") or "") < TIL:
            for x in (t.get("identityNr"), tr[i - 1].get("identityNr") if i else
                      ((lis.get(f.name[:-8]) or {}).get("grantInformation") or {}).get("openLegalEntityNr")):
                x = str(x or "").strip()
                if re.fullmatch(r"\d{9}", x) and x not in form:
                    ukjente.add(x)
if "--brreg" in sys.argv:
    brreg_slaa_opp(ukjente)
print(f"numre uten kjent form: {len(ukjente)}  brreg-oppslag: {dict(BRREG_STATUS)}")

rader, tap = [], collections.Counter()
hasher = []
# --- ledd A
ajour = collections.Counter()
for f in sorted((D / "arkiv/eierskap-overforinger").glob("*.json.gz")):
    h, b = kropp(f)
    hasher.append(f"{h}  {f.name}")
    nr = f.name[:-8]
    ajour[b.get("ajourDate")] += 1
    tr = b.get("transfers") or []
    for i, t in enumerate(tr):
        dato = str(t.get("journalDate") or "")
        if not (FRA <= dato < TIL):
            continue
        tap["A_overforinger_i_vinduet"] += 1
        kjoper = str(t.get("identityNr") or "")
        if i > 0:
            selger = str(tr[i - 1].get("identityNr") or "")
            selger_navn = tr[i - 1].get("officialName")
        else:
            g = (lis.get(nr) or {}).get("grantInformation") or {}
            selger = str(g.get("openLegalEntityNr") or "")
            selger_navn = g.get("legalEntityName")
        kk, ks = klasse(kjoper), klasse(selger)
        if kk != "selskap" or ks != "selskap":
            tap[f"A_utelatt kjøper={kk} selger={ks}"] += 1
            continue
        rader.append(dict(ledd="A", nr=nr, dato=dato, jnr=t.get("journalNr"),
                          kjoper=kjoper, kjoper_navn=t.get("officialName"),
                          selger=selger, selger_navn=selger_navn))
print("ajourDate i overføringskroppene:", dict(sorted(ajour.items())))
print(f"akvakultur (PO via lokalitet) sha256 {h_akva}")
(UT / "overforinger-sha256.txt").write_text("\n".join(hasher) + "\n")
samlet = hashlib.sha256("\n".join(hasher).encode()).hexdigest()
print(f"{len(hasher)} overføringskropper, sha256 over hashlista: {samlet}")

# --- ledd B: ukentlige eierkropper etter ajourDate
navn = {}
for f in siste:
    for l in kropp(f)[1]["tillatelser"]:
        navn[str(l.get("openLegalEntityNr"))] = l.get("legalEntityName")
forrige = None
for f in siste:
    h, b = kropp(f)
    L = {l["licenseNr"]: l for l in b["tillatelser"]}
    if forrige:
        for n, l in L.items():
            if n in forrige:
                a, c = str(forrige[n].get("openLegalEntityNr")), str(l.get("openLegalEntityNr"))
                if a != c:
                    tap["B_eierskifter"] += 1
                    if klasse(a) == klasse(c) == "selskap":
                        rader.append(dict(ledd="B", nr=n, dato=f.name[:10], jnr=None,
                                          kjoper=c, kjoper_navn=l.get("legalEntityName"),
                                          selger=a, selger_navn=forrige[n].get("legalEntityName")))
                    else:
                        tap[f"B_utelatt {klasse(c)}/{klasse(a)}"] += 1
        tap["B_nye_tillatelser_uten_selger"] += len(set(L) - set(forrige))
    print(f"eierskap {f.name}  sha256 {h}")
    forrige = L

for k, v in sorted(tap.items()):
    print(f"  {k}: {v}")

df = pl.DataFrame(rader).with_columns(
    pl.col("nr").map_elements(po, return_dtype=pl.Utf8).alias("po"),
    pl.col("nr").map_elements(lambda n: kap(n)[0], return_dtype=pl.Float64).alias("kapasitet"),
    pl.col("nr").map_elements(lambda n: kap(n)[1], return_dtype=pl.Utf8).alias("enhet"),
    pl.col("nr").map_elements(ttype, return_dtype=pl.Utf8).alias("type"))
df.write_csv(UT / "overforinger.csv")
pl.Config.set_tbl_rows(200); pl.Config.set_tbl_cols(12); pl.Config.set_fmt_str_lengths(40)
print("\nPer ledd:", df.group_by("ledd").len().sort("ledd").rows())
print("Konserninterne kandidater (kjøper == selger):", df.filter(pl.col("kjoper") == pl.col("selger")).height)
print("\nPer PO:")
print(df.group_by("po").agg(
    pl.len().alias("overforinger"),
    pl.col("nr").n_unique().alias("tillatelser"),
    pl.col("kjoper").n_unique().alias("kjopere"),
    pl.col("selger").n_unique().alias("selgere"),
    pl.col("jnr").n_unique().alias("journalnr")).sort(
        pl.col("po").cast(pl.Int32, strict=False)))
print("\nKapasitet per PO og enhet (dagens kapasitet):")
print(df.group_by("po", "enhet").agg(pl.col("kapasitet").sum(), pl.col("kapasitet").null_count().alias("uten_kap"), pl.len()).sort(
    pl.col("po").cast(pl.Int32, strict=False), "enhet"))
print("\nKjøpere og selgere per PO:")
print(df.group_by("po", "type").len().sort("po", "type"))
k = df.group_by("po", "kjoper_navn", "enhet").agg(pl.len().alias("n"), pl.col("kapasitet").sum()).sort(
    pl.col("po").cast(pl.Int32, strict=False), "n", descending=[False, True])
s = df.group_by("po", "selger_navn", "enhet").agg(pl.len().alias("n"), pl.col("kapasitet").sum()).sort(
    pl.col("po").cast(pl.Int32, strict=False), "n", descending=[False, True])
print(k); print(s)
k.write_csv(UT / "kjopere.csv"); s.write_csv(UT / "selgere.csv")
