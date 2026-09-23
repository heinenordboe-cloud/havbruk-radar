"""Skriver snapshots. Overskriver aldri noe.

Filnavnet er datoen. Det er hele versjonssystemet — git tar resten.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import polars as pl

from core import kodeproveniens
from core import persondata
from core import utvalg as utvalg_modul
from core.contract import Observation
from core.paths import RAW_DIR  # noqa: F401  (monkeypatches i testene treffer her)

SCHEMA = [
    "entity_id",
    "entity_type",
    "entity_name",
    "field",
    "value",
    "source",
    "observed_at",
    "fetched_at",
    "source_version",
    "raw_hash",
    # Hva kilden ba om. Proveniens som de tre over — se core/utvalg.py.
    # Verdien er lik for hver rad i ett snapshot, så parquet
    # ordbok-koder den bort. Målt på enhetsregisteret 24.08: 51623 rader
    # og en 100-tegns utvalgsstreng koster 1156 bytes, 0,53 % av fila.
    "utvalg",
    # Da KILDEN utga svaret. Tom streng = vet ikke. Se
    # Observation.published_at for hvorfor det ikke er `fetched_at`.
    "published_at",
    # Hvilke par kroppen UTTALER SEG OM. Bare differansen mot det
    # emitterte lagres, så verdien er "*", "{}" eller en kort parliste —
    # målt 1,04x filstørrelse mot 24x for en full parliste. Se
    # core/domene.py.
    "domene",
    # HVILKEN KODE SOM SKREV RADEN. Stemples av `write()`, ikke av
    # kilden: en verdi som gjelder hele kjøringen skal ikke være noe
    # tolv kildeforfattere må huske.
    #
    # F15 er grunnen, og den skjedde to ganger — se
    # core/kodeproveniens.py. Uten disse to kan ingen se at snapshotet
    # 21.09 ble skrevet av kode fra før 16.09, og at det derfor bærer
    # personformer kildens gjeldende filter ville stoppet.
    #
    # Tom streng = «kodeproveniens ukjent». Alle filer skrevet før
    # 23.09.2026 leser slik, og de blir stående — append-only.
    "kode_commit",
    "kode_rent",
]

# Kolonnene som gjelder KJØRINGEN og ikke observasjonen.
#
# De står med vilje IKKE på `Observation`: et felt på dataklassen er et
# felt en kilde kan fylle, og en kilde som oppga sin egen commit ville
# kunnet oppgi feil. `write()` stempler dem, i den ene veien alt går
# gjennom.
KJORINGSFELT = ("kode_commit", "kode_rent")


# Én kilde skal levere én verdi per entitet og felt per kjøring. Dette er
# invarianten i observasjonsformatet, ikke en egenskap ved noen enkelt kilde,
# og derfor håndheves den her — i trakta alt går gjennom — og ikke i hver
# kilde for seg.
#
# `source` er med i nøkkelen med vilje: to KILDER som observerer samme felt
# på samme entitet er kryssvalidering og skal beholdes. Det er samme kilde
# to ganger som er feilen.
NOKKEL = ["entity_id", "field", "source"]


def to_frame(observations: list[Observation]) -> pl.DataFrame:
    """Observasjoner til tabell, med duplikater fjernet.

    Hvorfor dedupliseringen ligger her: en kilde som gjør flere søk kan få
    samme entitet i retur fra to av dem. Enhetsregisteret søker på ni
    NACE-koder, og 15 selskaper matchet to av dem 17.08.2026 — det ga 503
    identiske ekstrarader. Mønsteret er ikke særegent for Brreg; enhver
    kilde som filtrerer på en kodeliste kan treffe det.

    Konsekvensen av å la dem stå er ikke bare støy i parquet: diff.compare()
    joiner på (entity_id, field), så en duplisert rad blir til en duplisert
    ENDRING den uka verdien faktisk endrer seg. Endringsloggen er produktet,
    og den kan ikke rapportere samme hendelse to ganger.

    `maintain_order=True` fordi rekkefølgen ellers varierer mellom kjøringer.
    Det ville gitt en ny parquet-fil i git selv når ingenting er endret.
    """
    if not observations:
        return pl.DataFrame(schema={col: pl.Utf8 for col in SCHEMA})
    fra_obs = [k for k in SCHEMA if k not in KJORINGSFELT]
    frame = pl.DataFrame([o.as_dict() for o in observations]).select(fra_obs)
    # KJØRINGSFELTENE LEGGES TIL TOMME her og fylles av `write()`.
    # `to_frame()` er også en lesevei — `diff` og testene bruker den på
    # observasjoner som aldri skrives — og den skal ikke spørre git.
    frame = frame.with_columns(
        [pl.lit("", dtype=pl.Utf8).alias(k) for k in KJORINGSFELT]
    ).select(SCHEMA)
    return frame.unique(subset=NOKKEL, keep="first", maintain_order=True)


def _vakt_mot_personformer(source: str, group: pl.DataFrame) -> None:
    """Nekter å skrive et snapshot som inneholder en fysisk person.

    Filteret i kilden er der data faktisk holdes ute. Denne vakten er der
    fordi et filter noen glemmer å oppdatere ikke er en garanti: en ny
    kilde som henter selskapsdata, en re-parse gjennom en vei som ikke
    filtrerer, eller en backfill som går utenom kildens `fetch()` — alle
    tre ender her, i den ene trakta alt skrives gjennom. Samme plassering
    og samme begrunnelse som datokontrollen under.

    TO felter, ikke ett, fra 16.09.2026: `organisasjonsform` mot
    `PERSONFORMER` og `institusjonell_sektorkode` mot `PERSONSEKTORER`.
    Grensa går ved sektoren (se core/persondata.py), og en vakt som bare
    leste formlista ville sluppet gjennom nøyaktig det tilfellet
    sektorleddet finnes for: en form ingen har rukket å føre opp.

    Hva vakten IKKE dekker, sagt rett ut: den ser bare de to feltnavnene.
    En kilde som kaller dem noe annet, eller som ikke oppgir noen av dem,
    går forbi — `eierskap` oppgir formen for 2839 av 2953 tillatelser og
    sektoren for ingen. Den fanger at et kjent filter sviktet, ikke at
    listene er riktige.
    """
    felter = set(group["field"].to_list())
    verdi = pl.col("value").str.strip_chars()

    treff = []
    if persondata.FORM_FELT in felter:
        treff.append(group.filter(
            (pl.col("field") == persondata.FORM_FELT)
            & verdi.str.to_uppercase().is_in(sorted(persondata.PERSONFORMER))))
    if persondata.SEKTOR_FELT in felter:
        treff.append(group.filter(
            (pl.col("field") == persondata.SEKTOR_FELT)
            & verdi.is_in(sorted(persondata.PERSONSEKTORER))))

    funn = [t for t in treff if not t.is_empty()]
    if not funn:
        return

    enheter = set()
    verdier = set()
    for t in funn:
        enheter |= set(t["entity_id"].to_list())
        verdier |= set(t["value"].to_list())

    raise ValueError(
        f"{source}: {len(enheter)} enhet(er) med {sorted(verdier)} i radene. "
        f"Det er en fysisk person, ikke et selskap "
        f"(se core/persondata.py), og snapshotet skrives ikke. Filteret i "
        f"kilden har sviktet eller er omgått — rett det der, ikke her."
    )


def _ledig_sti(target_dir: Path, observed_at: str) -> Path:
    """Neste ledige filnavn for denne datoen. Samme mønster som
    raw_arkiv.arkiver(): kollisjon løser seg med løpenummer, ikke
    overskriving."""
    sti = target_dir / f"{observed_at}.parquet"
    if not sti.exists():
        return sti

    n = 2
    while True:
        sti = target_dir / f"{observed_at}.{n}.parquet"
        if not sti.exists():
            return sti
        n += 1


def _dato_og_versjon(stem: str) -> tuple[str, int]:
    """'2026-08-17.3' -> ('2026-08-17', 3). Uten løpenummer: versjon 1.

    Datoen inneholder ingen punktum, så første del er alltid datoen —
    uansett hvor mange løpenumre som følger.
    """
    dato, _, versjon = stem.partition(".")
    return dato, int(versjon) if versjon else 1


def write(observations: list[Observation], observed_at: str) -> list[Path]:
    """Én parquet-fil per kilde per kjøring. Skriver aldri om — kolliderer
    filnavnet med et som finnes, får den neste et løpenummer.

    `observed_at` må stemme med radenes egen `observed_at`, og det
    kontrolleres her. Grunnen er en ekte feil: run.py sendte kjøredatoen
    hit mens lusetall stemplet radene med uka de gjaldt for, så fila het
    2026-08-24 og inneholdt uke 31. Et filnavn som lyver om innholdet er
    verre enn ingen fil, fordi alt nedstrøms — diff, changelog,
    prediksjoner — leser datoen fra navnet.

    Kontrollen ligger her og ikke hos kalleren fordi dette er trakta alt
    går gjennom: både run.py og backfill.py skriver herfra, og en
    invariant som skal holde for begge hører hjemme i den ene veien de
    deler. Samme begrunnelse gjelder personformvakten, se
    `_vakt_mot_personformer`.

    Merk rekkefølgen: rå-arkivet skrives FØR parse(), altså før noe kommer
    hit. Vakten stopper et snapshot, ikke en arkivfil. Skal persondata
    holdes ute av arkivet også, må det skje i kildens `fetch()` — som er
    grunnen til at enhetsregisteret filtrerer begge steder.
    """
    frame = to_frame(observations)

    # KODEPROVENIENSEN STEMPLES HER, i den ene veien alt går gjennom.
    #
    # Ikke i hver kilde, og ikke hos kalleren: `run.py` og
    # `backfill.py` skriver begge herfra, og en verdi som må stemples
    # hver gang skal ikke være noe en ny skrivevei må huske. Samme
    # begrunnelse som personformvakten og datokontrollen under.
    #
    # `write()` NEKTER ikke. Å nekte er `run.py`s jobb, før den henter
    # noe — se `kodeproveniens.krev_sporbar()`. Her stemples det som er
    # sant, også når det er «urent»: en fil som sier at treet var
    # skittent er uendelig mye mer verdt enn en fil som tier.
    if not frame.is_empty():
        sha, tilstand = kodeproveniens.commit(), kodeproveniens.rent()
        frame = frame.with_columns(
            pl.lit(sha, dtype=pl.Utf8).alias("kode_commit"),
            pl.lit(tilstand, dtype=pl.Utf8).alias("kode_rent"))

    written = []

    for (source,), group in frame.group_by(["source"]):
        _vakt_mot_personformer(str(source), group)

        datoer = sorted(set(group["observed_at"].to_list()))
        if datoer != [observed_at]:
            raise ValueError(
                f"{source}: filnavnet skulle vært {observed_at}, men radene "
                f"er observert {datoer}. Ett snapshot er ett tidspunkt — "
                f"skriv dem hver for seg, eller finn ut hvorfor de spriker."
            )

        target_dir = RAW_DIR / str(source)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = _ledig_sti(target_dir, observed_at)
        group.write_parquet(path)
        written.append(path)

    return written


def finnes_allerede(observed_at: str) -> list[str]:
    """Kilder som allerede har skrevet snapshot for denne datoen.

    Kjører du to ganger samme dag, sammenligner diffen mot forrige UKE
    på nytt og fører de samme endringene inn i changeloggen en gang til.
    run.py bruker denne til å nekte, i stedet for å doble tallene dine.
    """
    if not RAW_DIR.exists():
        return []
    return sorted(
        katalog.name
        for katalog in RAW_DIR.iterdir()
        if katalog.is_dir() and (katalog / f"{observed_at}.parquet").exists()
    )


def siste_dato(source: str) -> str | None:
    """Datoen for siste snapshot fra denne kilden, eller None.

    Flere filer kan dele dato (løpenummer ved kollisjon) — det er
    datoen som teller her, ikke hvilken fil som var sist alfabetisk.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None
    filer = sorted(target_dir.glob("*.parquet"), key=lambda p: _dato_og_versjon(p.stem))
    return _dato_og_versjon(filer[-1].stem)[0] if filer else None


def dager_siden_observasjon(source: str, observed_at: str) -> int | None:
    """Alderen på den nyeste OBSERVASJONEN fra kilden. None = ingen finnes.

    Het `dager_siden` og ble brukt som frekvensvakt. Det var feil, og
    navnet var grunnen: den svarer på «hvor gammel er nyeste
    observasjon», ikke på «når samlet vi sist inn». For kilder uten
    etterslep er de to like, og forskjellen var usynlig. For lusetall
    med uker_etterslep=4 er de aldri like — nyeste fil er ALLTID datert
    fire uker tilbake, også når kilden kjører perfekt.

    Frekvensvakten spør health.dager_siden_ok() i stedet. Denne
    måler datafriskhet, som er et ekte spørsmål, bare ikke det
    spørsmålet.

    Negativt tall (snapshot datert fram i tid) returneres som det er.
    """
    sist = siste_dato(source)
    if sist is None:
        return None
    try:
        return (date.fromisoformat(observed_at) - date.fromisoformat(sist)).days
    except ValueError:
        return None   # filnavn som ikke er en dato: behandles som aldri hentet


def _les(sti: Path) -> pl.DataFrame:
    """DEN ENE DØRA INN TIL ET SNAPSHOT PÅ DISK.

    Alt som leser innholdet i `data/raw/<kilde>/<dato>.parquet` går
    herfra, og derfor ligger persondatafilteret her og ikke i hver leser.
    `previous()` og `les_mellom()` er de eneste kallerne, og de er i sin
    tur de eneste veiene diff, prediksjoner og visning har inn til
    rådataene.

    Grunnen til at det må være ETT sted: snapshotene fra 16.–17.08.2026
    inneholder 34 enkeltpersonforetak hver, og de filene er append-only
    og blir stående. Filteret er derfor ikke en engangsopprydding som kan
    kjøres ferdig, men en betingelse hver lesing må oppfylle — og en
    betingelse som må oppfylles hver gang, skal ikke være noe en ny
    leseveis forfatter må huske.

    `test_ingen_leser_snapshots_utenom_les()` håndhever at det forblir
    slik: den nekter at `read_parquet` dukker opp i denne modulen mer enn
    én gang, eller i en annen modul som kjenner RAW_DIR.
    """
    return _les_med_tall(sti)[0]


def _les_med_tall(
        sti: Path) -> tuple[pl.DataFrame, dict[str, int], list[str], list[str]]:
    """Døra, og HVA DEN TOK: (ramme, {form: antall}, [id-er], [råkolonner]).

    Fjerde ledd er kolonnene fila FAKTISK hadde, før de manglende ble
    lagt til under. Det er den eneste måten å skille «fila ble skrevet
    uten kodeproveniens» fra «fila har den, og den er tom» — og de to
    betyr helt forskjellige ting. Se `kodeproveniens_per_fil()`.

    Den ene `read_parquet`-en i repoet står her, og det er grunnen til at
    telleren må bo i samme funksjon: et andre oppslag for å finne ut hva
    det første fjernet, ville vært en andre lesevei — og da er ikke
    filteret én dør lenger.

    Filtrering er stille av natur. `_les()` returnerer en ramme det ikke
    står noe i om at 64 entiteter forsvant på veien, og uten tallet kan
    `publiseringsvakt.py --rapport` ikke skille «filteret tok 64» fra
    «det var ingen der». Se `persondata.tell_personer()`.

    Kallerne som ikke bryr seg, kaller `_les()` og ser ingen forskjell.
    """
    raa = pl.read_parquet(sti)
    fjernet = persondata.tell_personer(raa)
    # ID-ENE, IKKE BARE TALLET. `filtrert_bort()` viser aggregatet og
    # skal fortsette med det; `personentiteter()` trenger hvem, fordi
    # changeloggens dør ikke kan stille spørsmålet selv — en
    # changelog-rad har `old_value` og `new_value` der et snapshot har
    # `value`. Oppslaget skjer her av samme grunn som telleren gjør det:
    # et andre oppslag ville vært en andre lesevei.
    personer = persondata.person_ider(raa)
    frame = persondata.fjern_personformer(raa)

    # Snapshots skrevet før 24.08.2026 har ingen `utvalg`-kolonne. De
    # skal kunne leses, og de skal lese som «vet ikke» — ikke som «ingen
    # filtrering». Tom streng er nettopp det skillet, se utvalg.les().
    #
    # Kolonnen legges til her og ikke hos hver leser av samme grunn som
    # persondatafilteret ligger her: dette er den ene døra, og en
    # betingelse som må oppfylles hver gang skal ikke være noe en ny
    # lesevei må huske.
    if "utvalg" not in frame.columns:
        frame = frame.with_columns(pl.lit("", dtype=pl.Utf8).alias("utvalg"))

    # Og snapshots skrevet før 26.08.2026 har ingen `published_at`. Samme
    # behandling og samme begrunnelse: de skal lese som «vet ikke».
    #
    # De skal IKKE fylles med `fetched_at`. Det ville vært å skrive om
    # historikken med et gjett — 103 biomasse-snapshots ville plutselig
    # PÅSTÅTT at Fiskeridirektoratet utga tallene 25.08.2026, som er
    # dagen VI hentet dem. Regel 2 gjelder her som ellers: en skrevet fil
    # røres ikke, og en manglende opplysning ser ut som en manglende
    # opplysning.
    if "published_at" not in frame.columns:
        frame = frame.with_columns(
            pl.lit("", dtype=pl.Utf8).alias("published_at"))

    # Og snapshots skrevet før 15.09.2026 har ingen `domene`. Samme
    # behandling, samme begrunnelse — og her er fallbacken særlig viktig:
    # tom streng leses som «vet ikke», og `domene.uttaler_seg_om()` svarer
    # da SANT, altså dagens oppførsel. 1873 revisjonsrader er skrevet uten
    # feltet, og en fallback som sa «nei» ville stilltiende undertrykt dem
    # alle — inkludert biomasses 1809 ekte.
    if "domene" not in frame.columns:
        frame = frame.with_columns(pl.lit("", dtype=pl.Utf8).alias("domene"))

    # Og snapshots skrevet før 23.09.2026 har ingen kodeproveniens. De
    # leses som UKJENT, ikke som «rent» og ikke som en påstand om noen
    # commit. Filene blir stående — append-only, og en fil som fikk
    # stemplet sitt i ettertid ville påstått at den ble skrevet av kode
    # som ikke fantes da.
    #
    # MÅLT 23.09.2026: 1 830 filer, alle uten. Det er ikke en feil som
    # kan rettes; det er en grense i historikken, og porten navngir den.
    for kol in ("kode_commit", "kode_rent"):
        if kol not in frame.columns:
            frame = frame.with_columns(pl.lit("", dtype=pl.Utf8).alias(kol))
    return frame, fjernet, personer, list(raa.columns)


def _en_verdi(frame: pl.DataFrame, kolonne: str) -> str | None:
    """Verdien alle radene deler i en kolonne, eller None hvis de spriker.

    Ett snapshot er ett kall, så proveniensfeltene — `fetched_at`,
    `source_version`, `utvalg` — bærer samme verdi på hver rad. Spriker de
    likevel, er rammen satt sammen av flere snapshots eller redigert for
    hånd, og da er svaret None. Å plukke den første av flere ville vært et
    gjett, og et gjett her ender som en påstand i changeloggen.
    """
    if frame.is_empty() or kolonne not in frame.columns:
        return None
    verdier = set(frame[kolonne].to_list())
    return str(verdier.pop()) if len(verdier) == 1 else None


def fetched_at_i(frame: pl.DataFrame) -> str | None:
    """Når snapshotet ble hentet. None = radene spriker eller mangler feltet.

    Trengs av `diff.revisjon()`: en revisjon er to utsagn om samme
    `observed_at`, og det eneste som skiller dem er hvilken henting de kom
    fra. Uten den kan en revisjon ikke plasseres i tid.
    """
    return _en_verdi(frame, "fetched_at")


def published_at_i(frame: pl.DataFrame) -> str | None:
    """Da KILDEN utga snapshotet. None = radene spriker, feltet mangler,
    eller kilden sa ingenting.

    Merk at tom streng og None kollapser til None her, og det er riktig:
    begge betyr «vi vet ikke når dette ble utgitt». Skillet mellom «feltet
    fantes ikke» og «kilden svarte ikke» er ikke et skille noen kan handle
    på.
    """
    return _en_verdi(frame, "published_at") or None


def publisert(frame: pl.DataFrame) -> str:
    """Sorteringsnøkkelen for VERSJONER av samme dato.

    `published_at` der den finnes, ellers `fetched_at`. Ikke fordi de er
    det samme — det er hele grunnen til at `published_at` ble innført —
    men fordi `fetched_at` er en ØVRE GRENSE for den: du kan ikke hente
    noe som ikke er utgitt.

    Rekkefølgen blir derfor riktig så lenge en kropp som er utgitt LENGE
    før den ble hentet, faktisk oppgir `published_at`. Det er nettopp
    tilfellet for en arkivkopi, og derfor nekter arkivmodusen i
    `backfill.py` å skrive en kropp uten den. For en fersk henting er
    grensen stram — timer eller dager — og fallbacken uskadelig.

    Tom streng når ingen av dem er kjent. Da sorterer versjonen først, og
    løpenummeret avgjør resten.
    """
    return published_at_i(frame) or fetched_at_i(frame) or ""


def source_version_i(frame: pl.DataFrame) -> str | None:
    """Hvilken parserversjon som skrev snapshotet. None = spriker.

    Brukes som VILKÅR, ikke som opplysning: to versjoner av samme dato
    kan bare sammenlignes som kildens revisjon hvis vår egen tolkning sto
    stille imellom. Se `diff.revisjon()`.
    """
    return _en_verdi(frame, "source_version")


def utvalg_i(frame: pl.DataFrame) -> dict | None:
    """Utvalget et snapshot ble hentet med. None = vet ikke.

    Ett snapshot er ett kall, så alle rader bærer samme verdi. Spriker
    de likevel — to kilder slått sammen i én ramme, eller en håndredigert
    fil — er svaret None. Å plukke den første av flere ville vært et
    gjett, og et gjett her undertrykker rader.
    """
    rå = _en_verdi(frame, "utvalg")
    return None if rå is None else utvalg_modul.les(rå)


def domene_i(frame: pl.DataFrame) -> str:
    """Den RÅ domenestrengen et snapshot bærer. Tom streng = vet ikke.

    Returnerer strengen og ikke den tolkede formen, fordi
    `domene.uttaler_seg_om()` trenger både den og rammens egne par for å
    svare — og rammen er det kalleren allerede har. Å tolke her ville
    vært en halv avgjørelse tatt et sted til.

    Spriker radene, er svaret tom streng: en ramme satt sammen av flere
    snapshots har ikke ETT domene, og å plukke det første ville påstått
    at den ene kroppens taushet gjaldt den andres rader.
    """
    return _en_verdi(frame, "domene") or ""


def previous(source: str, before: str) -> pl.DataFrame | None:
    """Siste snapshot fra denne kilden før gitt dato — nyeste PÅSTAND om
    den datoen, ikke høyeste løpenummer.

    To ledd, og de svarer på hver sin ting:

        1. hvilken DATO sto sist         — filnavnene avgjør
        2. hvilken PÅSTAND om den gjelder — `forrige_versjon()` avgjør

    Andre ledd var løpenummeret fram til 26.08.2026, og det holdt så lenge
    en høyere `.N` også bar en nyere påstand. Arkivinnsettingen brøt den
    sammenhengen: for 2017-10-31 er `.2` Wayback-kopien utgitt 20.07.2024,
    skrevet ved siden av en `.parquet` utgitt to år senere. Leste vi
    løpenummeret, ville `diff.compare()` sammenlignet november 2017 mot en
    to år gammel påstand om oktober, og hele differansen mellom de to
    utgivelsene lekket inn i changeloggen som industriens bevegelse.

    Derfor slår ikke denne opp versjonen selv. `forrige_versjon()` er det
    ene stedet som avgjør hvilken påstand om en dato som gjelder, og to
    tellere for samme sak er formen F6 og F7 hadde.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return None

    tidligere = {_dato_og_versjon(p.stem)[0] for p in target_dir.glob("*.parquet")}
    aktuelle = [d for d in tidligere if d < before]
    if not aktuelle:
        return None

    return forrige_versjon(source, max(aktuelle))


def versjon_av(sti: Path) -> int:
    """Løpenummeret i et snapshotfilnavn. 1 når det ikke har noe.

    Finnes for kallere som nettopp har skrevet et snapshot og skal gi noe
    annet — en changelog-fil — det SAMME nummeret. Å telle det opp på nytt
    hos kalleren ville vært to tellere for samme sak, som er formen F6 og
    F7 hadde.
    """
    return _dato_og_versjon(sti.stem)[1]


def datoer(source: str) -> list[str]:
    """Alle observasjonsdatoer kilden har skrevet, eldst først, uten
    duplikater.

    Leser FILNAVN, ikke innhold. En revisjonskjøring skal kunne spørre
    «hvilke perioder har vi allerede uttalt oss om» uten å åpne hundre
    parquet-filer for å finne det ut.

    Flere versjoner av samme dato (løpenummer) teller som én dato — det er
    perioden som er nøkkelen her, ikke hvor mange ganger vi har skrevet
    den.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return []
    return sorted({_dato_og_versjon(p.stem)[0]
                   for p in target_dir.glob("*.parquet")})


def forrige_versjon(source: str, observed_at: str) -> pl.DataFrame | None:
    """Nyeste snapshot som allerede finnes for NØYAKTIG denne datoen.

    Søsteren til `previous()`, og forskjellen er hele poenget:

        previous(kilde, before=D)      forrige DATO — hva sto her sist
        forrige_versjon(kilde, D)      forrige VERSJON av samme dato —
                                       hva sa kilden om D forrige gang
                                       vi spurte

    De to besvarer ulike spørsmål, og bare det andre kan uttrykke at en
    kilde har ombestemt seg. `previous()` ville sammenlignet mars med
    februar; det er industriens bevegelse, ikke Fiskeridirektoratets
    revisjon.

    «Forrige» er relativ til versjonen som er i ferd med å bli skrevet:
    svaret er den påstanden en ny skriving ville avløst. Det er den SIST
    UTGITTE av versjonene på disk — ikke den med høyest løpenummer.

    De to falt sammen fram til 26.08.2026 og gjør det ikke lenger: for
    2017-10-31 er `.2` Wayback-kopien utgitt 20.07.2024, skrevet ved
    siden av en `.parquet` utgitt to år senere. `versjoner()` eier
    rekkefølgen, og løpenummeret er der bare tiebreaker — tallmessig, så
    `.10` kommer etter `.2` og ikke før, som det ville alfabetisk.

    None betyr «datoen finnes ikke ennå». Det er ikke en revisjon, det er
    en førstegangsskriving, og den hører til `compare()`.
    """
    versjonene = versjoner(source, observed_at)
    return versjonene[-1][1] if versjonene else None


def versjoner(source: str, observed_at: str) -> list[tuple[int, pl.DataFrame]]:
    """Alle versjoner av én dato som (løpenummer, ramme), ELDST UTGITT FØRST.

    Rekkefølgen er PUBLISERINGSREKKEFØLGE, ikke filrekkefølge. De to var
    det samme helt til 26.08.2026, da Wayback-kopien av biomassefila ble
    skrevet inn: den er utgitt 20.07.2024 og skrevet som `.2` ved siden av
    en `.parquet` utgitt 20.08.2026. Løpenummeret sier når VI skrev,
    `published_at` når KILDEN utga, og det er det siste som avgjør hvilken
    påstand som avløste hvilken.

    Løpenummeret bryter likheter — to kropper med samme utgivelsestidspunkt
    er skrevet i den rekkefølgen de kom.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return []

    samme_dato = [p for p in target_dir.glob("*.parquet")
                  if _dato_og_versjon(p.stem)[0] == observed_at]
    lest = [(_dato_og_versjon(p.stem)[1], _les(p)) for p in samme_dato]
    return sorted(lest, key=lambda par: (publisert(par[1]), par[0]))


def filtrert_bort(source: str, observed_at: str) -> dict[str, int]:
    """{organisasjonsform: antall} som lesedøra tok ut av denne datoen.

    Summert over alle versjoner av datoen, og derfor et TAK og ikke et
    eksakt antall distinkte personer: står samme DA i både `.parquet` og
    `.2`, telles den to ganger. Det er riktig vei å ta feil på for en
    rapport som skal si «filteret virket», og det er sagt her framfor
    gjettet av leseren.

    AGGREGAT. Ingen entitets-ID-er, ingen navn — se `tell_personer()`.

    Finnes for `publiseringsvakt.py --rapport`, som skal kunne si hvor
    mange personer som ble holdt ute hver eneste gang den kjører. Et
    grønt bygg skal ikke kunne bety «ingen persondata» uten at noen har
    sett tallet.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return {}

    ut: dict[str, int] = {}
    for sti in sorted(target_dir.glob("*.parquet")):
        if _dato_og_versjon(sti.stem)[0] != observed_at:
            continue
        for form, antall in _les_med_tall(sti)[1].items():
            ut[form] = ut.get(form, 0) + antall
    return dict(sorted(ut.items()))


def personentiteter(source: str | None = None) -> frozenset[tuple[str, str]]:
    """(kilde, entity_id) for hver entitet lesedøra tar ut.

    `filtrert_bort()` svarer HVOR MANGE, og er aggregatet en rapport skal
    vise. Denne svarer HVEM, og finnes fordi changeloggen ikke kan stille
    spørsmålet selv: en changelog-rad har `old_value` og `new_value` der
    et øyeblikksbilde har `value`, og `persondata._personene()` leser
    `value`. Se `changelog.fjern_personformer()`.

    ## Kostnaden, og hvorfor den ikke er 1 830 filer

    En kilde probes på NYESTE fil. Bærer den verken `organisasjonsform`
    eller `institusjonell_sektorkode`, kan ingen av kildens filer peke ut
    en person, og resten leses ikke. MÅLT 23.09.2026: tre kilder svarer
    ja, og 1 530 av de 1 830 filene — lusetall og sjøtemperatur — leses
    aldri.

    Svaret er et TAK på samme måte som `filtrert_bort()`: summert over
    alle versjoner og alle datoer. En entitet som var en DA i 2024 og et
    AS i 2026 står på lista, og det er riktig vei å ta feil på.
    """
    if not RAW_DIR.exists():
        return frozenset()

    ut: set[tuple[str, str]] = set()
    kataloger = ([RAW_DIR / source] if source
                 else sorted(k for k in RAW_DIR.iterdir() if k.is_dir()))
    for katalog in kataloger:
        if not katalog.is_dir():
            continue
        filer = sorted(katalog.glob("*.parquet"))
        if not filer:
            continue
        nyeste, _, personer, _kol = _les_med_tall(filer[-1])
        felt = set(nyeste["field"].unique().to_list()) if "field" in nyeste.columns else set()
        if not felt & {persondata.FORM_FELT, persondata.SEKTOR_FELT}:
            continue
        for eid in personer:
            ut.add((katalog.name, str(eid)))
        for sti in filer[:-1]:
            for eid in _les_med_tall(sti)[2]:
                ut.add((katalog.name, str(eid)))
    return frozenset(ut)


def kodeproveniens_per_fil() -> list[dict]:
    """Én post per snapshotfil: hvilken kode som skrev den.

    [{kilde, fil, har_felt, commit, rent}]

    ## Hvorfor den bor HER

    `test_ingen_leser_snapshots_utenom_les` nekter enhver annen modul å
    kombinere kjennskap til `RAW_DIR` med en parquet-lesing, og den har
    rett: en andre lesevei er en vei rundt persondatafilteret. Porten
    spør derfor herfra — som den gjør for `filtrert_bort()` og
    `personentiteter()`.

    ## `har_felt` er ikke det samme som at feltet er utfylt

    En fil skrevet før 23.09.2026 har ikke kolonnene i det hele tatt, og
    `_les()` legger dem til som tomme ved lesing. Uten fjerde ledd fra
    `_les_med_tall()` ville de to tilfellene lest likt:

        har_felt=False, commit=""    skrevet før regelen fantes
        har_felt=True,  commit=""    skrevet etter, og kan likevel ikke
                                     gjøres rede for

    Det første er en grense i historikken. Det andre er et funn.
    """
    if not RAW_DIR.exists():
        return []

    ut: list[dict] = []
    for katalog in sorted(k for k in RAW_DIR.iterdir() if k.is_dir()):
        for sti in sorted(katalog.glob("*.parquet")):
            ramme, _tall, _pers, raa_kolonner = _les_med_tall(sti)
            har = "kode_commit" in raa_kolonner
            shaer = sorted({str(v or "") for v in ramme["kode_commit"].to_list()}
                           - {""}) if not ramme.is_empty() else []
            rene = sorted({str(v or "") for v in ramme["kode_rent"].to_list()}
                          - {""}) if not ramme.is_empty() else []
            ut.append({"kilde": katalog.name, "fil": sti.name,
                       "har_felt": har, "commit": shaer, "rent": rene})
    return ut


def les_mellom(source: str, fra: str, til: str) -> list[tuple[str, pl.DataFrame]]:
    """Alle snapshots fra denne kilden i intervallet [fra, til], eldst først.

    `previous()` svarer på "hva sto her sist". Prediksjonsloggen trenger
    noe annet: hele forløpet gjennom et vindu, fordi et anslag treffer
    den uka terskelen passeres — ikke bare hvis verdien tilfeldigvis
    fortsatt er over den når vinduet lukker. Leser man kun endepunktene,
    scores en kapasitetsøkning som ble reversert i uke ni som bom, og
    anslaget var riktig.

    Begge endepunkter er inklusive. `fra` må være med: det er der
    utgangsverdien hentes.

    Flere filer på samme dato (løpenummer ved kollisjon) gir flere
    innslag med samme dato, sortert ELDST UTGITT FØRST — samme nøkkel som
    `versjoner()`, og dermed samme påstand sist som `previous()` velger.

    At det er utgivelsen og ikke løpenummeret som sorterer, betyr noe her:
    kallerne — feltnormalen og prediksjonsloggen — tar det SISTE innslaget
    for en dato som den gjeldende. Etter arkivinnsettingen 26.08.2026 er
    høyeste løpenummer for 81 biomassemåneder en Wayback-kopi utgitt
    20.07.2024, og «gjeldende» ville da vært to år gammel.
    """
    target_dir = RAW_DIR / source
    if not target_dir.exists():
        return []

    lest = [(_dato_og_versjon(p.stem), _les(p))
            for p in target_dir.glob("*.parquet")
            if fra <= _dato_og_versjon(p.stem)[0] <= til]
    lest.sort(key=lambda par: (par[0][0], publisert(par[1]), par[0][1]))
    return [(nokkel[0], ramme) for nokkel, ramme in lest]
