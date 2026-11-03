"""Kropper i karantene, og kvitteringen som tar dem ut.

    python karantene.py                                   # hva ligger der
    python karantene.py --kvitter <kropp> --avvist  --grunn "…"
    python karantene.py --kvitter <kropp> --godtatt --grunn "…"

En fangstjobb som får en mistenkt kropp, legger den i
`data/arkiv/<mappe>/karantene/` og ender rød (core/karantene.py). Tilsynet
i datarepoet er rødt så lenge en kropp der mangler kvittering.

«avvist»: kroppen var feil (en feilside, en tom liste, en halv kropp). Den
blir liggende i karantene for alltid, og serien er uten den.

«godtatt»: regelen tok feil, og kroppen er ekte — en vilkårsside som ble
kortere, en uke med færre lokaliteter. Den skrives inn i serien med
samme navn og filtype som jobben ville gitt den, og neste kjøring
sammenligner mot den. Skal regelen selv endres, er det en kodeendring.

`<kropp>` er stien til `.gz`-fila i karantenemappa. Grunnen skrives i
kvitteringen ordrett og er det en leser om et år har å gå på.
"""
import argparse
import sys
from pathlib import Path

from core import karantene
from core import raw as raw_arkiv


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--kvitter", metavar="KROPP", type=Path)
    utfall = p.add_mutually_exclusive_group()
    utfall.add_argument("--avvist", action="store_true")
    utfall.add_argument("--godtatt", action="store_true")
    p.add_argument("--grunn", default="")
    a = p.parse_args(argv)

    if a.kvitter:
        if not (a.avvist or a.godtatt):
            p.error("--kvitter krever --avvist eller --godtatt")
        kv = karantene.kvitter(a.kvitter.resolve(),
                               "godtatt" if a.godtatt else "avvist", a.grunn)
        print(f"Kvittert {a.kvitter.name}: {kv['utfall']}"
              + (f", skrevet til data/arkiv/{kv['skrevet_til']}"
                 if kv.get("skrevet_til") else ""))
        return 0

    alle = karantene.poster()
    if not alle:
        print("Ingen kropper i karantene.")
        return 0
    for kropp, post, kv in sorted(alle, key=lambda x: x[2] is not None):
        rel = kropp.relative_to(raw_arkiv.ARKIV_DIR).as_posix()
        status = f"kvittert {kv['utfall']} {kv['kvittert'][:10]}" if kv else "UKVITTERT"
        print(f"{status:<28} data/arkiv/{rel}  {post['byte']} B  "
              f"{'; '.join(post['grunn'])}")
    return 1 if any(kv is None for *_, kv in alle) else 0


if __name__ == "__main__":
    sys.exit(main())
