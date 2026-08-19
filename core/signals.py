"""Scorer endringer etter regler i rules/signals.yml.

Reglene ligger i YAML og ikke i kode med vilje: du kommer til å justere
dem ofte, og du skal slippe å røre Python for å gjøre det.
"""

from pathlib import Path

import polars as pl
import yaml

RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "signals.yml"


def load_rules() -> list[dict]:
    if not RULES_PATH.exists():
        return []
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf-8")).get("regler", [])


def _matches(rule: dict, row: dict) -> bool:
    if rule.get("felt") and rule["felt"] != row["field"]:
        return False
    if rule.get("endringstype") and rule["endringstype"] != row["change_type"]:
        return False

    # Uten disse to kan ikke grammatikken skille en ny LOKALITET fra et
    # nytt SELSKAP: begge er feltet `navn` med endringstype `ny`, og
    # første treff vinner. Hver nyregistrert virksomhet fra
    # Enhetsregisteret fikk dermed lokalitetsetiketten. Raden har hatt
    # `source` og `entity_type` fra diff.py hele tiden — grammatikken
    # brukte dem bare ikke.
    if rule.get("kilde") and rule["kilde"] != row.get("source"):
        return False
    if rule.get("entity_type") and rule["entity_type"] != row.get("entity_type"):
        return False

    terskel = rule.get("min_endring_prosent")
    retning = rule.get("retning", "begge")

    if terskel is not None or retning != "begge":
        try:
            old, new = float(row["old_value"]), float(row["new_value"])
        except (TypeError, ValueError):
            return False
        if old == 0:
            return False

        endring = (new - old) / old * 100

        # Uten dette scores et KUTT på ti prosent under regelen som
        # heter "økning", og endringsloggen lyver om hva som skjedde.
        if retning == "opp" and endring <= 0:
            return False
        if retning == "ned" and endring >= 0:
            return False

        if terskel is not None and abs(endring) < terskel:
            return False

    return True


def score(changes: pl.DataFrame) -> pl.DataFrame:
    """ALLE endringer, med `signal` og `vekt` der en regel traff.

    Returnerer hver rad, ikke bare de scorede. En rad ingen regel treffer
    får `signal: null` og `vekt: 0`.

    Dette er endringen fra den opprinnelige versjonen, og grunnen er verdt
    å skrive ned: før kastet funksjonen hver rad ingen regel traff. Traff
    ingen regel noe som helst, kom en tom ramme ut — selv om det var fire
    hundre endringer den uka. Blindsonen var strukturelt usynlig, og du
    kan ikke skrive regelen som mangler før du kan telle hva den skulle
    ha fanget.

    MERK for kallere: `height` er nå TOTALEN, ikke antall treff. Vil du
    ha treffene, filtrer på `signal.is_not_null()`.
    """
    rules = load_rules()
    rader = []

    for row in changes.iter_rows(named=True):
        signal, vekt = None, 0
        for rule in rules:
            if _matches(rule, row):
                signal, vekt = rule["navn"], rule.get("vekt", 1)
                break
        rader.append({**row, "signal": signal, "vekt": vekt})

    if not rader:
        return changes.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("signal"),
            pl.lit(0, dtype=pl.Int64).alias("vekt"),
        )

    # schema_overrides: traff ingen regel, ville `signal` ellers blitt
    # utledet som Null-dtype og brutt filtreringen hos kalleren.
    # maintain_order: sorteringen er stabil i praksis på polars 1.36.1,
    # men garantien er ikke dokumentert, og siste_kjoring.txt committes.
    # En ustabil sortering ville gitt ny commit-melding uten at noe
    # faktisk endret seg. snapshot.to_frame() setter den av samme grunn.
    return pl.DataFrame(
        rader, schema_overrides={"signal": pl.Utf8, "vekt": pl.Int64}
    ).sort("vekt", descending=True, maintain_order=True)


def treff(scoret: pl.DataFrame) -> pl.DataFrame:
    """Bare radene en regel traff. Motstykket til score()."""
    return scoret.filter(pl.col("signal").is_not_null())


def uklassifiserte_felter(scoret: pl.DataFrame, antall: int = 5) -> list[tuple[str, int]]:
    """De vanligste feltene blant endringene ingen regel traff.

    Peker rett på hvilke regler som mangler: står `kapasitet_midlertidig`
    øverst med 60 uklassifiserte endringer, er det der neste regel hører
    hjemme.
    """
    uten = scoret.filter(pl.col("signal").is_null())
    if uten.is_empty():
        return []
    topp = uten.group_by("field").len().sort(["len", "field"], descending=[True, False])
    return [(str(f), int(n)) for f, n in topp.head(antall).iter_rows()]
