"""Sammenligner denne kjøringen mot forrige snapshot.

Diffen er produktet. Rådataene er bare råstoffet.

## To akser, to spørsmål

`compare()` går langs TIDA: hva sier kilden i dag som den ikke sa forrige
gang vi spurte. Det er bevegelse i verden.

`revisjon()` går langs HENTINGENE: hva sier kilden i dag om et tidspunkt
den allerede har uttalt seg om. Det er ikke bevegelse i verden — det er
kilden som har ombestemt seg.

Aksen finnes fordi én kilde krever den. Fiskeridirektoratets biomassefil
publiseres på nytt den 20. hver måned og endrer tall helt tilbake til
2017: målt 25.08.2026 mot en kopi fra 07.08.2024 var 490 av 3973 felles
rader endret, i hvert eneste år i serien, mens summen av alle
beholdninger bare flyttet seg 0,006 %. Mekanismen er lokaliteter som
omklassifiseres mellom produksjonsområder i ettertid.

To snapshots som er uenige om 2018 er derfor ikke en feil. `observed_at`
sier hvilket punkt i verden raden handler om; `fetched_at` sier hvilken
PÅSTAND om det punktet dette er. Begge er sanne, og bare den andre aksen
kan vise at den andre påstanden erstattet den første. Se CLAUDE.md 1b-5.
"""

import polars as pl

from core import snapshot
from core import utvalg

# Radene som IKKE er bevegelse. Entiteten dukket opp fordi vi begynte å
# spørre etter den, ikke fordi noe skjedde i verden. Se core/utvalg.py.
UTVALGSUTVIDELSE = "utvalgsutvidelse"

# Radene som heller ikke er bevegelse, av motsatt grunn: verden sto
# stille, og det var KILDEN som flyttet seg. Se `revisjon()`.
REVIDERT = "revidert"

# Endringstypene som beskriver at noe skjedde i verden. Alt utenfor er
# noe som skjedde med OSS eller med KILDEN, og telles ikke som aktivitet
# — se `bevegelse()`.
IKKE_BEVEGELSE = frozenset({UTVALGSUTVIDELSE, REVIDERT})


class Feilrekkefolge(RuntimeError):
    """Påstanden som skal sammenlignes er ELDRE enn den som ligger lagret.

    `revisjon()` svarer på «hva har kilden ombestemt seg om siden sist».
    Får den en eldre påstand inn, ville radene sagt at kilden endret 2026
    til 2024 — riktig innhold, motsatt fortegn, og en changelog som leser
    baklengs.

    Det er ikke en feil å HA en eldre påstand: en kropp gravd fram fra
    Wayback er nettopp det, og den er verdifull. Den skal bare skrives
    med `backfill.py --arkiv`, som setter den inn på riktig plass i
    utgivelsesrekkefølgen.

    Kastes bare når BEGGE sider har et kjent `published_at`. Er den ene
    ukjent, kan rekkefølgen ikke fastslås, og da påstås den ikke.
    """


class Grunnlagssprik(RuntimeError):
    """De to versjonene ble ikke laget på samme vilkår.

    Kastes av `revisjon()` når vår egen tolkning (`source_version`) eller
    vårt eget utvalg (`utvalg`) endret seg mellom de to hentingene. Da kan
    en forskjell ikke tilskrives kilden, og påstanden «Fiskeridirektoratet
    reviderte dette» ville vært en anklage mot en tredjepart for noe vi
    gjorde selv.

    Egen type fordi den ikke er en datafeil: begge snapshots er gyldige,
    spørsmålet er bare ubesvarlig fra dem alene. Kalleren skal si fra og
    la begge stå.
    """

CHANGE_SCHEMA = {
    "entity_id": pl.Utf8,
    "entity_type": pl.Utf8,
    "entity_name": pl.Utf8,
    "field": pl.Utf8,
    "old_value": pl.Utf8,
    "new_value": pl.Utf8,
    # "ny" | "endret" | "borte" | "utvalgsutvidelse" | "revidert"
    #
    # De to siste er EGNE verdier og ikke boolske kolonner ved siden av,
    # med vilje. Enhver leser som forgrener på change_type — og signals.py
    # er en av dem — må da forholde seg til dem eksplisitt i stedet for å
    # svelge dem som bevegelse. En kolonne til hadde vært noe hver leser
    # måtte huske å lese.
    #
    # Ingen av de 24 reglene i rules/signals.yml matcher "revidert", og
    # det er ikke tilfeldig: alle oppgir `endringstype`, så en ny verdi
    # treffer ingen regel før noen skriver en som ber om den. Samme
    # mekanikk som utvalgsutvidelse.
    "change_type": pl.Utf8,
    "source": pl.Utf8,
    "observed_at": pl.Utf8,
    # Datoen snapshotet ble sammenlignet MOT. Uten den kan ingen lese
    # hvor langt en changelog-rad spenner: 26673 endringer over sju dager
    # og over tretti dager ser identisk ut i loggen. Signalregelen
    # `krev_dato_etter_forrige` trenger den også — den er hele skillet
    # mellom "ny i registeret" og "ny i utvalget vårt".
    #
    # For en revisjonsrad er den LIK `observed_at`. Det er ikke en feil:
    # det er nettopp det som gjør raden til en revisjon.
    "forrige_observed_at": pl.Utf8,
    # HENTETIDSPUNKTET vi sammenlignet mot. Tom streng når det gamle
    # snapshotet ikke bærer ett entydig — rader skrevet før feltet fantes,
    # eller en ramme satt sammen av flere hentinger.
    #
    # For `compare()` er den kontekst: to snapshots med samme observed_at
    # ville ellers vært umulige å skille. For `revisjon()` er den HELE
    # opplysningen — der er `observed_at` lik på begge sider, og
    # hentetidspunktet er det eneste som plasserer de to påstandene i tid.
    "forrige_fetched_at": pl.Utf8,
    # UTGIVELSESTIDSPUNKTENE på hver side. Tom streng = kilden sa
    # ingenting; se Observation.published_at.
    #
    # De kom inn 26.08.2026 sammen med `published_at`, og de er det som
    # gjør en revisjonsrad LESBAR UTEN FILNAVNET. En rad som sier
    #
    #     forrige_published_at 2024-07-20  ->  published_at 2026-08-20
    #
    # forteller selv hvilken vei den går, uansett hvilken changelog-fil
    # den ligger i og uansett hvilken rekkefølge de to snapshotene ble
    # SKREVET i. Hentetidspunktene kan ikke det: en arkivkopi hentes i
    # dag og er utgitt for to år siden.
    "published_at": pl.Utf8,
    "forrige_published_at": pl.Utf8,
}


def compare(current: pl.DataFrame, observed_at: str,
            startdatofelt: str = "") -> pl.DataFrame:
    """Endringer mot forrige snapshot, per kilde.

    To slags «nytt» undertrykkes eller merkes her, og de er samme klasse
    hendelse:

    - **Nytt FELTNAVN** filtreres helt bort. Utvider du kilden med 24
      felter, er 23 000 "ny"-rader den uka støy som drukner de ekte
      endringene. Målt 17.08.2026: 18687 rader.
    - **Ny ENTITET fordi utvalget ble utvidet** merkes
      `utvalgsutvidelse`. Radene BEHOLDES — append-only, og en
      undertrykt rad er en hendelse ingen får se — men de teller ikke
      som bevegelse og treffer ingen signalregel. Målt 24.08.2026:
      25804 rader, 96,7 % av uka.

    Forskjellen i behandling er ikke vilkårlig. Et nytt feltnavn er
    ETTERPRØVBART fra de to snapshotene alene: feltet står der eller
    ikke. Om en ny entitet skyldes utvalget kan derimot bare avgjøres
    hvis snapshotet vet hva det ba om, og det er nettopp den
    opplysningen som manglet fram til 24.08. Derfor merker vi framfor å
    slette: påstanden hviler på et felt som kan være tomt.

    `startdatofelt` er kildens eget navn på entitetens fødselsdato (se
    Source.startdatofelt), og det er unntaket fra merkingen. En bedrift
    som ble REGISTRERT etter forrige snapshot er en hendelse i verden
    selv om den kom inn i samme uke som utvalget vokste — og en ekte
    nyregistrering som forsvinner i støyen fra utvidelsen er samme tap
    som utvidelsen selv skaper, bare med motsatt fortegn. Tom streng:
    kilden kan ikke etterprøves, og da merkes alle nye entiteter.
    """
    changes = []

    for (source,), group in current.group_by(["source"]):
        old = snapshot.previous(str(source), before=observed_at)
        if old is None:
            continue  # første kjøring for denne kilden: alt er "nytt", ikke interessant

        # Snapshots skrevet før dedupliseringen kom inn i to_frame() kan ha
        # flere rader per (entity_id, field). De filene er append-only og kan
        # ikke rettes i ettertid — men joinen under fanner ut på dem, og da
        # rapporteres SAMME endring én gang per duplikat den uka verdien
        # endrer seg. Verifisert: to like gamle rader ga to identiske
        # endringer. Leseren må derfor forsvare seg mot historikk den ikke
        # kan reparere.
        old = old.unique(subset=snapshot.NOKKEL, keep="first", maintain_order=True)

        # Felter som ikke fantes i forrige snapshot i det hele tatt er en
        # SKJEMAUTVIDELSE, ikke en hendelse. Utvider du kilden med 24 nye
        # felter, er 23 000 "ny"-rader den uka støy som drukner de ekte
        # endringene. Entiteter som er nye telles fortsatt — det er bare
        # nye FELTNAVN som filtreres.
        gamle_felter = set(old["field"].unique().to_list())

        # Ble utvalget bredere siden sist? Sant bare når BEGGE snapshots
        # oppgir hva de ba om. Et snapshot fra før 24.08 har tom
        # `utvalg`, og da er svaret usant: vi kan ikke påstå en utvidelse
        # vi ikke kan se. Se utvalg.er_utvidet for hvorfor fallbacken går
        # denne veien og ikke den andre.
        utvidet = utvalg.er_utvidet(snapshot.utvalg_i(old),
                                    snapshot.utvalg_i(group))

        # Entitetene som fantes sist. Trengs bare når utvalget er utvidet
        # — ellers er en "ny"-rad en "ny"-rad uansett hvem den gjelder.
        gamle_entiteter = (
            set(old["entity_id"].to_list()) if utvidet else set()
        )

        # Datoen vi sammenligner MOT, tatt fra radene i det gamle
        # snapshotet og ikke fra filnavnet. `write()` håndhever at de to
        # er like, og radene er det som faktisk ble observert.
        forrige_dato = ""
        forrige_datoer = set(old["observed_at"].to_list())
        if len(forrige_datoer) == 1:
            forrige_dato = str(forrige_datoer.pop())

        # Hentetidspunktet vi sammenligner mot. Tom streng når det gamle
        # snapshotet ikke bærer ett entydig — snapshots fra før feltet
        # fantes gjør ikke det, og de skal fortsatt kunne diffes.
        forrige_hentet = snapshot.fetched_at_i(old) or ""
        forrige_utgitt = snapshot.published_at_i(old) or ""
        utgitt = snapshot.published_at_i(group) or ""

        # Entitetene som ble til i verden etter forrige snapshot. De
        # skal STÅ som "ny" selv i en utvidelsesuke — se docstringen.
        # Tom mengde når kilden ikke oppgir noe startdatofelt, eller når
        # vi ikke vet hvilken dato vi sammenligner mot.
        egenfodte: set[str] = set()
        if utvidet and startdatofelt and forrige_dato:
            egenfodte = set(
                group.filter(
                    (pl.col("field") == startdatofelt)
                    & (pl.col("value") > pl.lit(forrige_dato))
                )["entity_id"].to_list()
            )

        key = ["entity_id", "field"]
        joined = group.join(
            old.select(key + ["value"]).rename({"value": "old_value"}),
            on=key,
            how="full",
            coalesce=True,
        )

        for row in joined.iter_rows(named=True):
            new_value, old_value = row.get("value"), row.get("old_value")
            if new_value == old_value:
                continue

            if old_value is None:
                if row["field"] not in gamle_felter:
                    continue   # nytt felt i kilden, ikke ny opplysning
                # Ny entitet + bredere utvalg = vi begynte å spørre etter
                # den. Merket gjelder HELE entiteten, ikke bare feltet:
                # er selskapet nytt for oss, er hver eneste rad om det
                # like mye en følge av utvidelsen.
                ny_for_oss = (utvidet
                              and row["entity_id"] not in gamle_entiteter)
                change_type = (
                    UTVALGSUTVIDELSE
                    if ny_for_oss and row["entity_id"] not in egenfodte
                    else "ny"
                )
            elif new_value is None:
                change_type = "borte"
            else:
                change_type = "endret"

            changes.append({
                "entity_id": row["entity_id"],
                "entity_type": row.get("entity_type") or "",
                "entity_name": row.get("entity_name") or "",
                "field": row["field"],
                "old_value": old_value,
                "new_value": new_value,
                "change_type": change_type,
                "source": str(source),
                "observed_at": observed_at,
                "forrige_observed_at": forrige_dato,
                "forrige_fetched_at": forrige_hentet,
                "published_at": utgitt,
                "forrige_published_at": forrige_utgitt,
            })

    if not changes:
        return pl.DataFrame(schema=CHANGE_SCHEMA)

    return pl.DataFrame(changes).select(list(CHANGE_SCHEMA)).cast(CHANGE_SCHEMA)


def _vilkaar(eldre: pl.DataFrame, nyere: pl.DataFrame, source: str,
             observed_at: str) -> None:
    """Kaster hvis de to versjonene ikke kan sammenlignes som kildens
    revisjon.

    To ting må ha stått stille mellom hentingene: vår egen tolkning
    (`source_version`) og vårt eget utvalg. Endret én av dem seg, kan en
    forskjell like gjerne være oss som kilden, og de to kan ikke skilles
    herfra. Da er det spørsmålet som er ubesvarlig — ikke dataene som er
    ødelagte, og begge snapshots blir stående.
    """
    gammel_versjon = snapshot.source_version_i(eldre)
    ny_versjon = snapshot.source_version_i(nyere)
    if gammel_versjon != ny_versjon:
        raise Grunnlagssprik(
            f"{source} {observed_at}: forrige versjon ble tolket av "
            f"source_version {gammel_versjon!r}, denne av {ny_versjon!r}. "
            f"En forskjell mellom dem kan like gjerne være vår egen "
            f"parser som kildens revisjon, og de to kan ikke skilles "
            f"herfra. Begge snapshots står."
        )

    gammelt_utvalg = snapshot.utvalg_i(eldre)
    nytt_utvalg = snapshot.utvalg_i(nyere)
    if gammelt_utvalg != nytt_utvalg:
        raise Grunnlagssprik(
            f"{source} {observed_at}: forrige versjon ble hentet med "
            f"utvalget {gammelt_utvalg!r}, denne med {nytt_utvalg!r}. "
            f"Entiteter som kommer eller går kan da være vårt utvalg og "
            f"ikke kildens revisjon. Begge snapshots står."
        )


def revisjon_mellom(eldre: pl.DataFrame, nyere: pl.DataFrame,
                    observed_at: str) -> pl.DataFrame:
    """Revisjonsradene mellom to navngitte versjoner av samme dato.

    Ren funksjon: den slår ingenting opp på disk, og den avgjør ingen
    rekkefølge — kalleren har allerede bestemt hvilken av de to som er
    ELDRE. Det er nettopp derfor den finnes ved siden av `revisjon()`:
    arkivmodusen i `backfill.py` setter en kropp inn MELLOM to påstander
    vi allerede har, og da er «forrige versjon på disk» feil spørsmål.

    ## Hva som IKKE regnes som revisjon

    **Et feltnavn som bare finnes på én side.** Legger vi til en kolonne i
    parseren, ville hver eneste måned fått en «revidert»-rad for det nye
    feltet — en påstand om at kilden endret noe VI endret. Samme regel og
    samme begrunnelse som skjemautvidelsen i `compare()`, bare med to
    sider å beskytte: et felt vi la til, og et felt vi fjernet, er begge
    våre.

    Merk at filteret går på FELTNAVN og ikke på entiteter. En entitet som
    dukker opp eller forsvinner mellom to versjoner av samme måned ER en
    revisjon — kilden har flyttet noe inn i eller ut av det tidsrommet —
    og `old_value`/`new_value` viser hvilken vei det gikk.
    """
    changes = []
    kilder = set(nyere["source"].to_list()) | set(eldre["source"].to_list())
    source = str(sorted(kilder)[0]) if kilder else ""

    _vilkaar(eldre, nyere, source, observed_at)

    # Samme forsvar som i compare(): snapshots fra før dedupliseringen
    # kan ha flere rader per (entity_id, field), og joinen under ville
    # fanne ut på dem.
    eldre = eldre.unique(subset=snapshot.NOKKEL, keep="first",
                         maintain_order=True)

    felles_felter = (set(eldre["field"].unique().to_list())
                     & set(nyere["field"].unique().to_list()))

    key = ["entity_id", "field"]
    joined = nyere.join(
        eldre.select(key + ["value"]).rename({"value": "old_value"}),
        on=key,
        how="full",
        coalesce=True,
    )

    for row in joined.iter_rows(named=True):
        if row["field"] not in felles_felter:
            continue
        new_value, old_value = row.get("value"), row.get("old_value")
        if new_value == old_value:
            continue

        changes.append({
            "entity_id": row["entity_id"],
            "entity_type": row.get("entity_type") or "",
            "entity_name": row.get("entity_name") or "",
            "field": row["field"],
            "old_value": old_value,
            "new_value": new_value,
            "change_type": REVIDERT,
            "source": source,
            "observed_at": observed_at,
            # Samme dato på begge sider. Det ER revisjonen.
            "forrige_observed_at": observed_at,
            "forrige_fetched_at": snapshot.fetched_at_i(eldre) or "",
            "published_at": snapshot.published_at_i(nyere) or "",
            "forrige_published_at": snapshot.published_at_i(eldre) or "",
        })

    if not changes:
        return pl.DataFrame(schema=CHANGE_SCHEMA)

    return pl.DataFrame(changes).select(list(CHANGE_SCHEMA)).cast(CHANGE_SCHEMA)


def revisjon(current: pl.DataFrame, observed_at: str) -> pl.DataFrame:
    """Hva kilden har OMBESTEMT SEG om for et tidspunkt den alt har uttalt
    seg om.

    Speilvendt `compare()`: der sammenlignes to ULIKE `observed_at` fra
    samme henting, her sammenlignes to ULIKE hentinger av SAMME
    `observed_at`. Radene får `change_type = "revidert"`, `observed_at` og
    `forrige_observed_at` er like, og `forrige_published_at` ->
    `published_at` bærer hvilken vei revisjonen gikk.

    «Forrige» er den SIST UTGITTE versjonen på disk, ikke den med høyest
    løpenummer. De to var det samme til 26.08.2026, da en kropp utgitt i
    2024 ble skrevet inn ved siden av en utgitt i 2026. Se
    `snapshot.versjoner()`.

    Tom ramme når datoen ikke finnes fra før. Det er ikke en revisjon —
    det er en førstegangsskriving, og den hører til `compare()`.

    Kaster `Feilrekkefolge` hvis `current` er utgitt FØR den lagrede
    versjonen. Da er dette ikke «hva har kilden ombestemt seg om siden
    sist», men en eldre påstand som skal settes inn på riktig plass —
    `backfill.py --arkiv`. Kaster `Grunnlagssprik` hvis vår egen
    tolkning eller vårt eget utvalg endret seg imellom; se `_vilkaar`.
    """
    deler = []

    for (source,), group in current.group_by(["source"]):
        forrige = snapshot.forrige_versjon(str(source), observed_at)
        if forrige is None or forrige.is_empty():
            continue

        # Retningen FØR sammenligningen. En eldre påstand inn hit ville
        # gitt riktig innhold med motsatt fortegn — en changelog som
        # leser baklengs — og det skal ikke kunne skje ved et uhell.
        #
        # Bare når BEGGE sider har et kjent utgivelsestidspunkt. Er den
        # ene ukjent, kan rekkefølgen ikke fastslås, og da påstås den
        # ikke: `fetched_at` er bare en øvre grense, og en grense er ikke
        # et grunnlag for å nekte.
        ute_nå = snapshot.published_at_i(group)
        ute_før = snapshot.published_at_i(forrige)
        if ute_nå and ute_før and ute_nå < ute_før:
            raise Feilrekkefolge(
                f"{source} {observed_at}: kroppen er utgitt {ute_nå}, den "
                f"lagrede versjonen {ute_før}. Dette er ikke en revisjon "
                f"av den — det er en ELDRE påstand, og radene ville sagt "
                f"at kilden endret det nye til det gamle. Skriv den inn "
                f"med `backfill.py --arkiv`, som setter den på riktig "
                f"plass i utgivelsesrekkefølgen."
            )

        deler.append(revisjon_mellom(forrige, group, observed_at))

    return slaa_sammen(deler)


def bevegelse(endringer: pl.DataFrame) -> pl.DataFrame:
    """Radene som faktisk er bevegelse i verden.

    Alt unntatt `IKKE_BEVEGELSE`, altså unntatt utvalgsutvidelse og
    revisjon. De to er speilbilder av hverandre og filtreres av samme
    grunn: den ene sier at VI begynte å se etter noe, den andre at KILDEN
    ombestemte seg om noe. I ingen av tilfellene skjedde det noe i sjøen.

    Egen funksjon og ikke et filter hos hver kaller: «hvor mye skjedde
    denne uka» er ett spørsmål med ett svar, og tallet står i
    commit-meldingen som leses på telefonen. To kallere som filtrerer
    hver for seg er to steder å glemme det.

    Radene som filtreres bort er IKKE slettet. De ligger i changeloggen,
    de kan telles, og de kan leses av den som vil vite når utvalget ble
    utvidet eller når kilden skrev om fortiden. De skal bare ikke summeres
    som aktivitet.
    """
    if endringer.is_empty() or "change_type" not in endringer.columns:
        return endringer
    return endringer.filter(~pl.col("change_type").is_in(sorted(IKKE_BEVEGELSE)))


def slaa_sammen(deler: list[pl.DataFrame]) -> pl.DataFrame:
    """Endringer fra flere kilder til én ramme.

    Trengs fordi kilder med ulikt etterslep ikke lenger deler dato: én
    kjøring differ nå hver kilde mot sin egen gyldighetsdato, og delene
    må settes sammen igjen før scoring og commit-melding. Tom liste gir
    tom ramme med riktig skjema, så kalleren slipper å skille på det.
    """
    deler = [d for d in deler if not d.is_empty()]
    if not deler:
        return pl.DataFrame(schema=CHANGE_SCHEMA)
    return pl.concat(deler, how="diagonal_relaxed")
