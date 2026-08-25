"""Intern visning. Leser data, skriver én HTML-fil, ingenting annet.

    python vis.py

Skriver `oversikt.html` til HAVBRUK_DATA_DIR og printer stien og
filstørrelsen. Fila er gitignorert i datarepoet med vilje: en generert
fil som skrives om hver uke er nøyaktig mønsteret som får git til å
vokse kvadratisk, og visningen er en ren funksjon av snapshots og
changelog — begge append-only — så den kan alltid regenereres.

Kjøres på kommando, aldri fra den ukentlige jobben. Innsamlingen skal
ikke kunne felles av et leseverktøy.

Foreløpig bygges kun visning 2 (felter). Se docs/VISNING.md.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from core import changelog, diff, snapshot   # noqa: E402
from core.paths import DATA_DIR, RAW_DIR      # noqa: E402

UT = DATA_DIR / "oversikt.html"

# Navngitt feilmodus fra VISNING.md: hele datasettet inline slutter å
# virke når det blir stort nok. Grensa ligger et sted rundt 20-50 MB.
# Vi skriver størrelsen hver gang, så det merkes før det blir et problem.
STOR_FIL_MB = 20


def _kilder() -> list[str]:
    if not RAW_DIR.exists():
        return []
    return sorted(k.name for k in RAW_DIR.iterdir() if k.is_dir())


def _siste_snapshot(kilde: str) -> tuple[str, pl.DataFrame] | None:
    """Nyeste snapshot for kilden, med .N-versjonering respektert.

    Går via snapshot.les_mellom() i stedet for å glob'e selv: den kjenner
    allerede regelen om at `.10` sorterer etter `.2`, og den regelen skal
    finnes ett sted.
    """
    dato = snapshot.siste_dato(kilde)
    if dato is None:
        return None
    filer = snapshot.les_mellom(kilde, dato, dato)
    if not filer:
        return None
    return dato, filer[-1][1]          # høyeste løpenummer sist


def _etterslep_dager() -> dict[str, int]:
    """Kildenavn -> hvor mange dager kildens ferskeste snapshot er datert
    bak i tid FORDI kilden har etterslep.

    Uten dette leses lusetall-panelet feil. Snapshotet er datert fire uker
    tilbake, og en leser som sammenligner det med akvakultur-panelet ser
    en kilde som ser ut til å ha stått stille en måned. Den har ikke det —
    den henter uke N-4 med vilje, fordi ferskere uker er ufullstendige.

    Måles som avstanden mellom kjøredatoen og datoen en kjøring i dag
    ville gitt snapshotet, altså kildens egen gjelder_for(). Da er tallet
    kildens regel og ikke et anslag basert på hva som tilfeldigvis ligger
    på disk: en kilde som ikke har kjørt på tre uker skal se gammel ut,
    og det skal ikke skjules bak «etterslep».
    """
    from core import registry

    i_dag = dt.datetime.now(dt.timezone.utc).date()
    ut = {}
    for k in registry.discover():
        gjelder = dt.date.fromisoformat(k.gjelder_for(i_dag.isoformat()))
        ut[k.name] = (i_dag - gjelder).days
    return ut


def _er_numerisk(verdier: pl.Series) -> bool:
    """Alle verdier lar seg lese som tall.

    Alt lagres som tekst (se ARKITEKTUR.md), så dette er den eneste måten
    å vite om et felt kan bli en `endring`-prediksjon. Streng med vilje:
    ett felt der 99 av 100 er tall er ikke et talfelt, det er et rotete
    felt, og det skal synes.
    """
    if verdier.is_empty():
        return False
    return verdier.cast(pl.Float64, strict=False).null_count() == 0


def _felter_for_kilde(kilde: str, ramme: pl.DataFrame,
                      endringer: pl.DataFrame) -> list[dict]:
    entiteter = ramme["entity_id"].n_unique()

    endr_per_felt: dict[str, int] = {}
    if endringer.height:
        for felt, antall in (
            endringer.filter(pl.col("source") == kilde)
            .group_by("field").len().iter_rows()
        ):
            endr_per_felt[str(felt)] = int(antall)

    rader = []
    for (felt,), gruppe in ramme.group_by(["field"]):
        verdier = gruppe["value"]
        vanligste = (
            gruppe.group_by("value").len().sort("len", descending=True).head(3)
        )
        rader.append({
            "felt": str(felt),
            "dekning": gruppe["entity_id"].n_unique(),
            "dekning_andel": round(gruppe["entity_id"].n_unique() / entiteter, 4)
            if entiteter else 0.0,
            "distinkte": verdier.n_unique(),
            "eksempler": [str(v) for v in vanligste["value"].to_list()],
            "endringer": endr_per_felt.get(str(felt), 0),
            "numerisk": _er_numerisk(verdier),
        })

    # Fallende på endringer: toppen av lista er der det er noe å mene
    # noe om. Sekundært på dekning, så lista er stabil mens
    # endringstallet ennå er null for alt.
    rader.sort(key=lambda r: (-r["endringer"], -r["dekning"], r["felt"]))
    return rader


def bygg_data() -> dict:
    # Merkingen skjer ved LESING, ikke i fila. Changeloggen er
    # append-only, og radene fra 24.08.2026 kan ikke skrives om — men de
    # kan leses riktig. 25804 av de 26673 radene den uka var 908
    # selskaper som kom inn da næringskodelista ble utvidet, og en
    # analyse som teller dem som aktivitet leser en utvidelse som en
    # bransje i bevegelse. Se changelog.merk_utvalgsutvidelse().
    alle = changelog.merk_utvalgsutvidelse(changelog.les_alt())
    endringer = diff.bevegelse(alle)
    utvalgsutvidelse = alle.height - endringer.height
    etterslep = _etterslep_dager()
    kilder = []

    for navn in _kilder():
        siste = _siste_snapshot(navn)
        if siste is None:
            continue
        dato, ramme = siste
        kilder.append({
            "kilde": navn,
            "dato": dato,
            # Dager kilden er datert bak i tid FORDI den har etterslep.
            # 0 for kilder uten. Se _etterslep_dager().
            "etterslep": etterslep.get(navn, 0),
            "entiteter": ramme["entity_id"].n_unique(),
            "observasjoner": ramme.height,
            "felter": _felter_for_kilde(navn, ramme, endringer),
        })

    return {
        "kilder": kilder,
        "endringer_totalt": endringer.height,
        # Står for seg og skjules ikke: uka utvalget vokser er den uka
        # enhver senere sammenligning må ta hensyn til.
        "utvalgsutvidelse_totalt": utvalgsutvidelse,
    }


def html(data: dict) -> str:
    # `</` brytes opp: en verdi som inneholder "</script>" ville ellers
    # lukket taggen og ødelagt sida.
    nyttelast = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")

    return f"""<!doctype html>
<meta charset="utf-8">
<title>Feltoversikt — havbruk-radar</title>
<style>
 body {{ font: 13px/1.4 ui-monospace, Menlo, Consolas, monospace;
        margin: 1.5rem; background: #fff; color: #111; }}
 h1 {{ font-size: 1.1rem; margin: 0 0 .2rem; }}
 .sub {{ color: #666; margin-bottom: 1rem; }}
 .kilde {{ margin: 1.5rem 0 .4rem; font-weight: bold; }}
 table {{ border-collapse: collapse; width: 100%; margin-bottom: 1rem; }}
 th, td {{ border-bottom: 1px solid #ddd; padding: 3px 8px;
           text-align: left; vertical-align: top; }}
 th {{ background: #f3f3f3; cursor: pointer; user-select: none;
       position: sticky; top: 0; }}
 td.n, th.n {{ text-align: right; font-variant-numeric: tabular-nums; }}
 .ex {{ color: #555; }}
 .lav {{ color: #b00; }}
 .flat {{ background: #fff6d6; }}
 input {{ font: inherit; padding: 3px 6px; width: 18rem; }}
 .merk {{ color: #666; margin: .3rem 0 1rem; }}
</style>

<h1>Feltoversikt</h1>
<div class="sub">Visning 2 av 5. Ett felt per rad, sortert fallende på antall endringer.</div>

<input id="sok" placeholder="filtrer på feltnavn…" autofocus>
<div class="merk" id="merk"></div>
<div id="ut"></div>

<script id="data" type="application/json">{nyttelast}</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);

function celle(rad, tekst, klasse) {{
  const td = document.createElement('td');
  td.textContent = tekst;
  if (klasse) td.className = klasse;
  rad.appendChild(td);
  return td;
}}

function tegn(filter) {{
  const ut = document.getElementById('ut');
  ut.textContent = '';
  let vist = 0, totalt = 0;

  for (const k of DATA.kilder) {{
    const felter = k.felter.filter(f => f.felt.includes(filter));
    totalt += k.felter.length;
    vist += felter.length;
    if (!felter.length) continue;

    const h = document.createElement('div');
    h.className = 'kilde';
    // Etterslepet står eksplisitt. Uten det ser en kilde som daterer seg
    // fire uker tilbake med vilje ut som en kilde som har stått stille.
    const etterslep = k.etterslep > 0
      ? ` — gjelder ${{k.dato}}, ${{k.etterslep}} dager bak i dag (kilden `
        + `henter med etterslep med vilje; ferskere data er ufullstendige)`
      : ` — snapshot ${{k.dato}}`;
    h.textContent = `${{k.kilde}}${{etterslep}}, ${{k.entiteter}} entiteter, `
                  + `${{k.observasjoner}} observasjoner, ${{k.felter.length}} felter`;
    ut.appendChild(h);

    const t = document.createElement('table');
    const thead = document.createElement('tr');
    for (const [tekst, klasse] of [['felt',''],['dekning','n'],['%','n'],
         ['distinkte','n'],['endringer','n'],['type',''],['eksempler','']]) {{
      const th = document.createElement('th');
      th.textContent = tekst;
      if (klasse) th.className = klasse;
      thead.appendChild(th);
    }}
    t.appendChild(thead);

    for (const f of felter) {{
      const tr = document.createElement('tr');
      // Ett distinkt verdi = feltet kan ikke endre seg. Det er ikke en
      // feil, men det er verdiløst å spå om, og det skal synes.
      if (f.distinkte === 1) tr.className = 'flat';
      celle(tr, f.felt);
      celle(tr, f.dekning, 'n');
      const pst = (f.dekning_andel * 100).toFixed(0) + '%';
      celle(tr, pst, f.dekning_andel < 0.5 ? 'n lav' : 'n');
      celle(tr, f.distinkte, 'n');
      celle(tr, f.endringer, 'n');
      celle(tr, f.numerisk ? 'tall' : 'tekst');
      celle(tr, f.eksempler.join('  |  '), 'ex');
      t.appendChild(tr);
    }}
    ut.appendChild(t);
  }}

  document.getElementById('merk').textContent =
    `${{vist}} av ${{totalt}} felter vist. `
    + `Endringer i changeloggen totalt: ${{DATA.endringer_totalt}}`
    + (DATA.utvalgsutvidelse_totalt
        ? ` (+${{DATA.utvalgsutvidelse_totalt}} rader utvalgsutvidelse, ikke bevegelse)`
        : ``)
    + `. `
    + `Gul rad = én distinkt verdi, feltet kan ikke endre seg. `
    + `Rød prosent = under 50 % dekning.`;
}}

document.getElementById('sok').addEventListener('input', e => tegn(e.target.value));
tegn('');
</script>
"""


def main() -> int:
    data = bygg_data()
    if not data["kilder"]:
        print(f"Ingen snapshots funnet under {RAW_DIR}.")
        return 1

    UT.parent.mkdir(parents=True, exist_ok=True)
    UT.write_text(html(data), encoding="utf-8")

    mb = UT.stat().st_size / 1_048_576
    print(UT)
    for k in data["kilder"]:
        merke = f" (-{k['etterslep']}d etterslep)" if k["etterslep"] else ""
        print(f"  {k['kilde']:<20} {k['dato']}{merke:<18}  "
              f"{len(k['felter']):>3} felter  {k['entiteter']:>6} entiteter  "
              f"{k['observasjoner']:>7} observasjoner")
    print(f"  endringer i changeloggen: {data['endringer_totalt']}")
    if data["utvalgsutvidelse_totalt"]:
        print(f"  utvalgsutvidelse (ikke bevegelse): "
              f"{data['utvalgsutvidelse_totalt']}")
    print(f"  filstørrelse: {mb:.2f} MB")
    if mb > STOR_FIL_MB:
        print(f"  ADVARSEL: over {STOR_FIL_MB} MB. Se 'Navngitt feilmodus' "
              f"i docs/VISNING.md — per-entitet-detalj bør ut i egne filer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
