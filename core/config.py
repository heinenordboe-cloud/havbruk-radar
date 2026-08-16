"""Leser config.yml. Én kilde til sannhet for alt som kan justeres.

Regel: hvis du noen gang vurderer å hardkode et tall, en URL eller en
liste i en kildefil — den hører hjemme her i stedet.
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yml"
ENV_MONSTER = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _expander(node: Any) -> Any:
    """Bytter ut ${NAVN} med miljøvariabel.

    Nøkler hører aldri hjemme i config.yml. De legges i GitHub Secrets
    og refereres som ${BARENTSWATCH_KEY}. Da kan repoet være offentlig
    uten at noe lekker.
    """
    if isinstance(node, dict):
        return {k: _expander(v) for k, v in node.items()}
    if isinstance(node, list):
        return [_expander(v) for v in node]
    if isinstance(node, str):
        return ENV_MONSTER.sub(lambda m: os.environ.get(m.group(1), ""), node)
    return node


@lru_cache(maxsize=1)
def load() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    rå = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return _expander(rå)


def get(sti: str, standard: Any = None) -> Any:
    """Hent nøstet verdi med punktnotasjon: get("kilder.akvakultur.aktiv")"""
    node: Any = load()
    for del_ in sti.split("."):
        if not isinstance(node, dict) or del_ not in node:
            return standard
        node = node[del_]
    return node
