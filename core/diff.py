"""Sammenligner denne kjøringen mot forrige snapshot.

Diffen er produktet. Rådataene er bare råstoffet.
"""

import polars as pl

from core import snapshot

CHANGE_SCHEMA = {
    "entity_id": pl.Utf8,
    "entity_type": pl.Utf8,
    "entity_name": pl.Utf8,
    "field": pl.Utf8,
    "old_value": pl.Utf8,
    "new_value": pl.Utf8,
    "change_type": pl.Utf8,   # "ny" | "endret" | "borte"
    "source": pl.Utf8,
    "observed_at": pl.Utf8,
}


def compare(current: pl.DataFrame, observed_at: str) -> pl.DataFrame:
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
                change_type = "ny"
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
            })

    if not changes:
        return pl.DataFrame(schema=CHANGE_SCHEMA)

    return pl.DataFrame(changes).select(list(CHANGE_SCHEMA)).cast(CHANGE_SCHEMA)


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
