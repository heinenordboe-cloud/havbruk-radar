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

    terskel = rule.get("min_endring_prosent")
    if terskel is not None:
        try:
            old, new = float(row["old_value"]), float(row["new_value"])
        except (TypeError, ValueError):
            return False
        if old == 0:
            return False
        if abs((new - old) / old) * 100 < terskel:
            return False

    return True


def score(changes: pl.DataFrame) -> pl.DataFrame:
    rules = load_rules()
    scored = []

    for row in changes.iter_rows(named=True):
        for rule in rules:
            if _matches(rule, row):
                scored.append({
                    **row,
                    "signal": rule["navn"],
                    "vekt": rule.get("vekt", 1),
                })
                break

    if not scored:
        return changes.with_columns(
            pl.lit(None, dtype=pl.Utf8).alias("signal"),
            pl.lit(0, dtype=pl.Int64).alias("vekt"),
        ).head(0)

    return pl.DataFrame(scored).sort("vekt", descending=True)
