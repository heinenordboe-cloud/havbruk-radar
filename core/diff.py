"""Sammenligner denne kjøringen mot forrige snapshot.

Diffen er produktet. Rådataene er bare råstoffet.
"""

import polars as pl

from core import snapshot
from core import utvalg

# Radene som IKKE er bevegelse. Entiteten dukket opp fordi vi begynte å
# spørre etter den, ikke fordi noe skjedde i verden. Se core/utvalg.py.
UTVALGSUTVIDELSE = "utvalgsutvidelse"

CHANGE_SCHEMA = {
    "entity_id": pl.Utf8,
    "entity_type": pl.Utf8,
    "entity_name": pl.Utf8,
    "field": pl.Utf8,
    "old_value": pl.Utf8,
    "new_value": pl.Utf8,
    # "ny" | "endret" | "borte" | "utvalgsutvidelse"
    #
    # Den siste er en EGEN verdi og ikke en boolsk kolonne ved siden av
    # "ny", med vilje. Enhver leser som forgrener på change_type — og
    # signals.py er en av dem — må da forholde seg til den eksplisitt i
    # stedet for å svelge den som bevegelse. En kolonne til hadde vært
    # noe hver leser måtte huske å lese.
    "change_type": pl.Utf8,
    "source": pl.Utf8,
    "observed_at": pl.Utf8,
    # Datoen snapshotet ble sammenlignet MOT. Uten den kan ingen lese
    # hvor langt en changelog-rad spenner: 26673 endringer over sju dager
    # og over tretti dager ser identisk ut i loggen. Signalregelen
    # `krev_dato_etter_forrige` trenger den også — den er hele skillet
    # mellom "ny i registeret" og "ny i utvalget vårt".
    "forrige_observed_at": pl.Utf8,
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
            })

    if not changes:
        return pl.DataFrame(schema=CHANGE_SCHEMA)

    return pl.DataFrame(changes).select(list(CHANGE_SCHEMA)).cast(CHANGE_SCHEMA)


def bevegelse(endringer: pl.DataFrame) -> pl.DataFrame:
    """Radene som faktisk er bevegelse — alt unntatt utvalgsutvidelse.

    Egen funksjon og ikke et filter hos hver kaller: «hvor mye skjedde
    denne uka» er ett spørsmål med ett svar, og tallet står i
    commit-meldingen som leses på telefonen. To kallere som filtrerer
    hver for seg er to steder å glemme det.

    Radene som filtreres bort er IKKE slettet. De ligger i changeloggen,
    de kan telles, og de kan leses av den som vil vite når utvalget ble
    utvidet. De skal bare ikke summeres som aktivitet.
    """
    if endringer.is_empty() or "change_type" not in endringer.columns:
        return endringer
    return endringer.filter(pl.col("change_type") != UTVALGSUTVIDELSE)


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
