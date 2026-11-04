"""MALING-NYE-KILDER, etterskrift 04.11.2026 (økt 4c, punkt 1e): hvilke
flater på nettstedet viser ILA eller PD, og fra hvilken uke.

    HAVBRUK_DATA_DIR=../havbruk-radar-data/data \
        .venv/bin/python analyse/ilapd/i3_flater.py <byggemappe> \
        > analyse/ilapd/i3_flater.txt

Leser et bygg fra `nettsted.py --alle` som det er, med publiseringsvaktens
egne lesere: tekstfiler, Pagefind-fragmentene pakket ut, og hvert ark og
medlem i `.xlsx` og `.zip`. Treffet er `publiseringsvakt.SYKDOMSMONSTER`,
den samme prøven porten bruker etterpå. Det som telles er FILER, gruppert
etter flate (første mappenivå, og filtypen).

Deretter changelog-radene nettstedet leser (`nettsted._les_beveg()`, den
ene døra) for `lusetall` `har_ila`/`har_pd`: hvor mange, hvor mange
lokaliteter, første og siste uke, og fordelingen per endringsuke slik
ukesidene viser dem. Ingen regel og ingen terskel; det er en opptelling.

Døra leses slik den var FØR 04.11.2026, med `IKKE_PUBLISERTE_FELT` tom:
spørsmålet er hva nettstedet viste, ikke hva det viser etter rettingen.
Radene skrives til `analyse/ilapd/i3_hendelser.csv` — lista over
hendelsene som går ut av framtidige bygg.
"""

import io
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import nettsted  # noqa: E402
import publiseringsvakt as vakt  # noqa: E402

UKESIDE = re.compile(r"^endringer/(\d{4}-\d{2})/")


def treff_i(sti: Path) -> Counter:
    """{treff: antall} for én fil, arkiver pakket ut."""
    t = Counter()
    if sti.suffix.lower() == ".xlsx":
        for _navn, rader in vakt.xlsx_ark(sti.read_bytes()) or []:
            t.update(vakt.SYKDOMSMONSTER.findall("\n".join(v for r in rader for v in r)))
        return t
    if sti.suffix.lower() == ".zip":
        z = zipfile.ZipFile(io.BytesIO(sti.read_bytes()))
        for m in z.namelist():
            data = z.read(m)
            if m.endswith(".xlsx"):
                for _navn, rader in vakt.xlsx_ark(data) or []:
                    t.update(vakt.SYKDOMSMONSTER.findall("\n".join(v for r in rader for v in r)))
            else:
                t.update(vakt.SYKDOMSMONSTER.findall(data.decode("utf-8", errors="replace")))
        return t
    tekst = vakt._tekst(sti)
    if tekst:
        t.update(vakt.SYKDOMSMONSTER.findall(tekst))
    return t


def main() -> None:
    mappe = Path(sys.argv[1])
    per_flate = defaultdict(lambda: [0, 0, Counter()])
    ukesider = Counter()
    lokaliteter = set()
    filer = [p for p in sorted(mappe.rglob("*")) if p.is_file()]
    for sti in filer:
        t = treff_i(sti)
        if not t:
            continue
        rel = sti.relative_to(mappe).as_posix()
        flate = (rel.split("/")[0] if "/" in rel else "(rot)") + " " + (sti.suffix or sti.name)
        per_flate[flate][0] += 1
        per_flate[flate][1] += sum(t.values())
        per_flate[flate][2].update(t)
        if m := UKESIDE.match(rel):
            ukesider[m.group(1)] += 1
        if rel.startswith("lokalitet/"):
            lokaliteter.add(rel.split("/")[1])
    print(f"Bygg: {mappe.name}, {len(filer)} filer lest\n")
    print("flate                          filer   treff  former")
    for flate, (n, s, t) in sorted(per_flate.items()):
        print(f"{flate:<30} {n:>5} {s:>7}  {dict(t.most_common())}")
    print(f"\nLokalitetsmapper med treff: {len(lokaliteter)}")
    print(f"Ukesider (endringer/<uke>/...) med treff, per uke: {dict(sorted(ukesider.items()))}")

    import polars as pl
    nettsted.IKKE_PUBLISERTE_FELT = frozenset()
    nettsted._les_beveg.cache_clear()
    beveg = nettsted._les_beveg()
    rader = beveg.filter((pl.col("source") == "lusetall")
                         & pl.col("field").is_in(["har_ila", "har_pd"]))
    print(f"\nChangelog gjennom nettsted._les_beveg(): {rader.height} rader for "
          f"lusetall har_ila/har_pd, {rader['entity_id'].n_unique()} lokaliteter")
    for felt in ("har_ila", "har_pd"):
        r = rader.filter(pl.col("field") == felt)
        print(f"  {felt}: {r.height} rader, observed_at {r['observed_at'].min()} – "
              f"{r['observed_at'].max()}")
    print("  per år (observed_at):")
    aar = rader.with_columns(pl.col("observed_at").str.slice(0, 4).alias("aar")) \
        .group_by("aar").len().sort("aar")
    print("   " + ", ".join(f"{a} {n}" for a, n in aar.iter_rows()))
    ut = Path(__file__).with_name("i3_hendelser.csv")
    rader.select(["entity_id", "entity_name", "field", "change_type", "old_value",
                  "new_value", "observed_at", "forrige_observed_at"]) \
        .sort(["entity_id", "field", "observed_at"]).write_csv(ut)
    print(f"  lista: {ut.name}, sha256 "
          f"{__import__('hashlib').sha256(ut.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
