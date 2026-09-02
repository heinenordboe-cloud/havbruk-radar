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

import kildeledd                            # noqa: E402
from analyse import revisjoner              # noqa: E402
from core import changelog, diff, snapshot   # noqa: E402
from core.paths import DATA_DIR, RAW_DIR      # noqa: E402

UT = DATA_DIR / "oversikt.html"

# Kildeleddet, skrevet OG lest av kildeledd.py. Visningen regner ikke
# formelen ut på nytt: to steder som beregner Stien-leddet ville vært to
# tellere for samme sak, og den formen har dette repoet betalt for flere
# ganger (CLAUDE.md 1b). Lesingen ligger heller ikke her — se
# kildeledd.les_serier() for hvorfor. Finnes filene ikke, hoppes
# seksjonen over: vis.py skal kunne kjøres på et repo der kildeledd.py
# aldri er kjørt.

# FULL og DELVIS er IKKE samme størrelse, og skal ikke kunne forveksles
# ved et blikk. Ulik farge og ulik strek, ikke bare ulik etikett.
FARGE_FULL = "#05628a"
FARGE_DELVIS = "#b26a00"

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


def _per_felt(kilde: str, rader: pl.DataFrame) -> dict[str, int]:
    """{feltnavn: antall} for én kildes rader i en endringsramme."""
    if not rader.height:
        return {}
    return {
        str(felt): int(antall)
        for felt, antall in (rader.filter(pl.col("source") == kilde)
                             .group_by("field").len().iter_rows())
    }


def _felter_for_kilde(kilde: str, ramme: pl.DataFrame,
                      endringer: pl.DataFrame,
                      revisjoner: pl.DataFrame) -> list[dict]:
    entiteter = ramme["entity_id"].n_unique()

    endr_per_felt = _per_felt(kilde, endringer)
    # Egen kolonne, ikke lagt til endringstallet. En revidert måned er
    # ikke en måned der noe skjedde — det er en måned kilden har uttalt
    # seg om to ganger. Summeres de, forsvinner nettopp det skillet
    # revisjonsaksen finnes for.
    rev_per_felt = _per_felt(kilde, revisjoner)

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
            "revisjoner": rev_per_felt.get(str(felt), 0),
            "numerisk": _er_numerisk(verdier),
        })

    # Fallende på endringer: toppen av lista er der det er noe å mene
    # noe om. Sekundært på dekning, så lista er stabil mens
    # endringstallet ennå er null for alt.
    rader.sort(key=lambda r: (-r["endringer"], -r["revisjoner"],
                              -r["dekning"], r["felt"]))
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

    # Tell hver for seg, ikke som «resten». `bevegelse()` filtrerer nå bort
    # TO typer, og differansen alene ville tilskrevet revisjonene til
    # utvalgsutvidelsen — et tall som så riktig ut og pekte på feil årsak.
    def _av_type(t):
        return (alle.filter(pl.col("change_type") == t)
                if "change_type" in alle.columns else alle.head(0))

    utvalgsutvidelse = _av_type(diff.UTVALGSUTVIDELSE).height
    revisjoner = _av_type(diff.REVIDERT)
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
            "felter": _felter_for_kilde(navn, ramme, endringer, revisjoner),
        })

    return {
        "kilder": kilder,
        "endringer_totalt": endringer.height,
        # Står for seg og skjules ikke: uka utvalget vokser er den uka
        # enhver senere sammenligning må ta hensyn til.
        "utvalgsutvidelse_totalt": utvalgsutvidelse,
        # Samme prinsipp, motsatt årsak: her sto verden stille og KILDEN
        # flyttet seg. To utsagn om samme tidspunkt er ikke bevegelse.
        "revisjon_totalt": revisjoner.height,
        # Hvor mange PERIODER kilden har uttalt seg om mer enn én gang.
        # Radtallet alene sier ikke om det er én måned som ble skrevet om
        # femti ganger eller femti måneder som ble rørt én gang hver.
        "reviderte_perioder": (revisjoner.select(["source", "observed_at"])
                               .unique().height),
    }


# ------------------------------------------------------- kildeleddet

def _linje(punkter: list[tuple[float, float]], farge: str,
           strek: str = "") -> str:
    if not punkter:
        return ""
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in punkter)
    stiplet = ' stroke-dasharray="2 2"' if strek else ""
    return (f'<polyline points="{d}" fill="none" stroke="{farge}" '
            f'stroke-width="1"{stiplet}/>')


def _panel(rader: list[tuple[str, float]], bredde: int, hoyde: int,
           farge: str, alle_datoer: list[str], strek: str = "") -> str:
    """Én kurve i en boks. x er posisjon i den GLOBALE datolista.

    Den globale aksen er poenget: to paneler under hverandre skal kunne
    leses mot hverandre uten at 2012 i det ene ligger over 2018 i det
    andre. FULL starter derfor inne i panelet sitt og ikke ved venstre
    kant — hullet foran 2017-10 er en egenskap ved dataene, ikke ved
    tegningen, og skal SES.
    """
    if not rader:
        return ""
    indeks = {d: i for i, d in enumerate(alle_datoer)}
    n = max(len(alle_datoer) - 1, 1)
    topp = max(v for _, v in rader) or 1.0
    punkter = [((indeks[d] / n) * bredde, hoyde - (v / topp) * hoyde)
               for d, v in rader if d in indeks]
    return _linje(punkter, farge, strek)


def _sesongprofil(ramme: pl.DataFrame, farge: str, strek: str = "") -> str:
    """Median per ISO-uke over alle år og alle PO.

    Dette er plausibilitetssjekken, og den er den enkleste som finnes:
    lakselus har et kraftig sesongmønster, og en serie uten det er regnet
    feil. Median og ikke middel — ett PO-år med en ekstremverdi skal ikke
    kunne tegne en topp som ikke er der.
    """
    per_uke = (ramme.group_by("iso_uke")
               .agg(pl.col("verdi").median().alias("m"))
               .sort("iso_uke"))
    if per_uke.is_empty():
        return ""
    B, H = 520, 110
    topp = per_uke["m"].max() or 1.0
    punkter = [(((u - 1) / 52) * B, H - (m / topp) * H)
               for u, m in per_uke.iter_rows()]
    return _linje(punkter, farge, strek)


def kildeledd_html() -> str:
    """Hele seksjonen, eller tom streng om serien ikke er beregnet."""
    serier = kildeledd.les_serier()
    if not serier:
        return ""

    alle_datoer = sorted({d for r in serier.values()
                          for d in r["uke_mandag"].to_list()})
    B, H = 520, 110

    # --- sesongprofil ---------------------------------------------------
    sesong = []
    for serie, farge, strek in (("full", FARGE_FULL, ""),
                                ("delvis", FARGE_DELVIS, "stiplet")):
        if serie not in serier:
            continue
        r = serier[serie]
        kurve = _sesongprofil(r, farge, strek)
        topp = (r.group_by("iso_uke").agg(pl.col("verdi").median().alias("m"))
                 .sort("m", descending=True))
        topp_uke = topp["iso_uke"][0] if not topp.is_empty() else "?"
        bunn_uke = topp.sort("m")["iso_uke"][0] if not topp.is_empty() else "?"
        enhet = r["enhet"][0] if not r.is_empty() else ""
        sesong.append(
            f'<div class="fig"><div class="figh">{serie.upper()} — median per ISO-uke'
            f' <span class="dim">(topp uke {topp_uke}, bunn uke {bunn_uke};'
            f' {enhet})</span></div>'
            f'<svg viewBox="0 -6 {B} {H + 12}" width="100%" height="{H + 12}">'
            f'{kurve}</svg>'
            f'<div class="figx"><span>uke 1</span><span>uke 26</span>'
            f'<span>uke 52</span></div></div>')

    # --- per PO ---------------------------------------------------------
    po_er = sorted({p for r in serier.values() for p in r["po"].to_list()})
    paneler = []
    for po in po_er:
        deler = []
        merker = []
        for serie, farge, strek in (("full", FARGE_FULL, ""),
                                    ("delvis", FARGE_DELVIS, "stiplet")):
            if serie not in serier:
                continue
            d = serier[serie].filter(pl.col("po") == po).sort("uke_mandag")
            if d.is_empty():
                continue
            rader = list(zip(d["uke_mandag"].to_list(), d["verdi"].to_list()))
            deler.append(_panel(rader, B, H, farge, alle_datoer, strek))
            # Toppverdien står som TALL. Hver kurve er skalert til sitt
            # eget maksimum, så uten tallet er to paneler ikke
            # sammenlignbare — og et panel som ser høyt ut kan være lavt.
            merker.append(f'<span style="color:{farge}">{serie}: '
                          f'maks {max(v for _, v in rader):.3g}</span>')
        navn = ""
        for r in serier.values():
            treff = r.filter(pl.col("po") == po)["po_navn"]
            if not treff.is_empty() and treff[0]:
                navn = treff[0]
                break
        paneler.append(
            f'<div class="fig"><div class="figh">PO{po} {navn} '
            f'<span class="dim">{" · ".join(merker)}</span></div>'
            f'<svg viewBox="0 -6 {B} {H + 12}" width="100%" height="{H + 12}">'
            f'{"".join(deler)}</svg></div>')

    forbehold = ""
    for r in serier.values():
        if not r.is_empty():
            forbehold = r["forbehold"][0]
            break

    # DEKNINGEN bak middelet, regnet av serien selv. Et middel over tre
    # lokaliteter er ikke et områdeestimat, og den begrensningen skal stå
    # ved siden av kurven — ikke i en logg noen må lete etter.
    tynt = []
    for navn in ("full", "delvis"):
        r = serier.get(navn)
        if r is None or r.is_empty() or "n_rapporterende" not in r.columns:
            continue
        for po in sorted(r["po"].unique().to_list()):
            d = r.filter(pl.col("po") == po)
            andel = d.filter(pl.col("n_rapporterende") <= 5).height / d.height
            if andel > 0.10:
                tynt.append((navn, po, andel, int(d["n_rapporterende"].median())))
        break   # samme bilde i begge seriene; vis den ene
    dekning = ""
    if tynt:
        punkter = " · ".join(
            f"<b>PO{po}</b>: {andel:.0%} av ukene har ≤ 5 rapporterende "
            f"(median {med})" for _, po, andel, med in tynt)
        dekning = (
            f'<br><b class="lav">Tynn dekning:</b> {punkter}. Middelet '
            f'hviler der på svært få anlegg, og ett anlegg som tømmes '
            f'svinger kurven uten at lusepresset i sjøen har endret seg. '
            f'Les <code>n_rapporterende</code> sammen med verdien.')
    formler = " · ".join(
        f'{s.upper()} = {serier[s]["formel"][0]}' for s in ("full", "delvis")
        if s in serier and not serier[s].is_empty())
    agg = (serier[next(iter(serier))]["aggregering"][0]
           if serier else "")

    fra = min(alle_datoer) if alle_datoer else "?"
    til = max(alle_datoer) if alle_datoer else "?"

    return f"""
<h2 class="k2">Kildeleddet — Stien mfl. 2005, per produksjonsområde per uke</h2>
<div class="merk">
 <b style="color:{FARGE_FULL}">FULL</b> (heltrukket) er kildeleddet:
 klekte nauplier per time. Finnes bare fra 2017-10, fordi N_fisk gjør det.
 <b style="color:{FARGE_DELVIS}">DELVIS</b> (stiplet) er
 <b>ikke kildeleddet</b> — den er lus × (T + 4,28)² uten N_fisk og uten
 0,17, i en annen enhet, og tallene er ikke sammenlignbare med FULL.
 Hver kurve er skalert til sitt eget maksimum; les tallet, ikke høyden.
 <br>{formler}
 <br>N_fisk mot ukentlige lus/temp: <b>{agg}</b> — uka ganges med
 beholdningen ved slutten av sin egen måned, ikke interpolert.
 Sprang i FULL som ikke finnes i DELVIS er et månedsskifte i N_fisk,
 ikke en hendelse i sjøen.
 <br><b>Forbehold:</b> {forbehold}{dekning}
 <br><span class="dim">{fra} .. {til}. Beregnet av kildeledd.py; denne
 siden leser tallene og regner dem ikke ut på nytt.</span>
</div>
<div class="figrad">{"".join(sesong)}</div>
<div class="figrad">{"".join(paneler)}</div>
"""


def revisjoner_html() -> str:
    """Revisjonssammendraget: hvem ombestemmer seg, hvor mye, hvor sent.

    Tom streng når ingen kilde har revidert noe. Tallene REGNES IKKE HER
    — `analyse/revisjoner.py` eier dem, og denne funksjonen setter dem
    bare opp. Samme grunn som for kildeleddet: to steder som regner ut
    samme størrelse er to tellere for samme sak.
    """
    rev = revisjoner.hent_revisjoner()
    if rev.is_empty():
        return ""

    tid = revisjoner.Tidslinje()
    rader = revisjoner.sammendrag(rev, tid)

    tr = []
    for r in rader:
        endr = ("<span class=\"dim\">ikke tall</span>"
                if r["median_endring"] is None
                else f"{r['median_endring'] * 100:.2f} %")
        storst = ("" if r["storste_endring"] is None
                  else f"{r['storste_endring'] * 100:.1f} %")
        if r["dager_median"] is None:
            sent = "<span class=\"dim\">—</span>"
        elif r["dager_min"] == r["dager_maks"]:
            merke = " ≤" if r["er_ovre_grense"] else ""
            sent = f"{r['dager_median']}{merke}"
        else:
            merke = " ≤" if r["er_ovre_grense"] else ""
            sent = (f"{r['dager_min']}–{r['dager_maks']}"
                    f" (med. {r['dager_median']}){merke}")
        tr.append(
            f"<tr><td>{r['kilde']}</td><td>{r['aar']}</td>"
            f"<td class=\"n rev\">{r['rader']}</td>"
            f"<td class=\"n\">{r['enheter']}</td>"
            f"<td class=\"n\">{r['felter']}</td>"
            f"<td class=\"n\">{endr}</td><td class=\"n\">{storst}</td>"
            f"<td class=\"n\">{sent}</td></tr>")

    # Verifiseringen står PÅ SIDA og ikke bare i en logg. Påstanden om at
    # ingen andre har de gamle versjonene er verdiløs hvis den ikke kan
    # etterprøves av den som leser tallene.
    sjekk = revisjoner.verifiser(rev, 5, tid)
    ok = sum(1 for v in sjekk if v["utfall"] == "OK")
    spor = []
    for v in sjekk:
        spor.append(
            f"<tr><td>{v['source']}</td><td>{v['observed_at']}</td>"
            f"<td>{v['entity_id']}</td><td>{v['field']}</td>"
            f"<td>{v.get('eldst_publisert', '')[:10]}<br>"
            f"<span class=\"dim\">v{v.get('eldst_versjon', '?')}</span></td>"
            f"<td>{v.get('gammel_pa_disk')!r}</td>"
            f"<td>{v.get('nyest_publisert', '')[:10]}<br>"
            f"<span class=\"dim\">v{v.get('nyest_versjon', '?')}</span></td>"
            f"<td>{v.get('ny_pa_disk')!r}</td>"
            f"<td class=\"rev\">{v['utfall']}</td></tr>")

    kilder_nevnt = ", ".join(sorted(rev["source"].unique().to_list()))
    e = revisjoner.eksempel_po9()
    eksempel = ""
    if e:
        eksempel = f"""
<div class="fig" style="margin-bottom:1rem">
 <div class="figh"><b>Ett produksjonsområde, én verdi, ett år imellom</b></div>
 <b>{e['entity_name']} (PO{e['entity_id']}), vurderingsåret 2024.</b>
 <br>Ekspertgruppens rapport for 2024, utgitt
 <b>{e['utgitt_forst'][:10]}</b>, ville ikke plassere PO9 i en kategori.
 Den skrev <code>{e['kategori_ordrett_2024']}</code> og lot
 <code>kategori</code> stå tom — et grensetilfelle.
 <br>Rapporten for 2025, utgitt <b>{e['utgitt_revidert'][:10]}</b>,
 kapittel 6.1 «Oppdaterte hovedkonklusjoner for 2024», avgjorde det:
 <code>kategori = <span class="rev">{e['new_value']}</span></code>.
 <br><b>{e['dager']} dager senere.</b> Samme år, samme område, ny
 vurdering — og bare den som tok vare på den første påstanden kan se at
 den ble endret. Fiskeridirektoratets biomassefil overskriver seg selv
 den 20. hver måned.
</div>"""

    return f"""
<h2 class="k2">Revisjoner — når kilden ombestemmer seg</h2>
<div class="merk">
 En <span class="rev">revisjon</span> er ikke en feil og ikke en hendelse
 i sjøen. Det er kilden som uttaler seg om det SAMME tidspunktet en gang
 til. Radene telles derfor ikke som bevegelse.
 <br><b>{rev.height}</b> revisjonsrader i changeloggen, fordelt på
 <b>{rev['source'].n_unique()}</b> kilder: {kilder_nevnt}.
 <br><b>Havforskningsinstituttet står ikke i tabellen.</b> HI erklærer i
 egen rapport at hele arkivet fra 2012 kjøres på nytt ved
 modellendring, så kilden REVIDERER — men vi henter ingen serie fra den
 som skriver snapshots, og en revisjon vi ikke har to påstander om, kan
 ikke telles. Fraværet er vårt, ikke kildens.
</div>
{eksempel}
<table>
<tr><th>kilde</th><th>år</th><th class="n">rader</th><th class="n">områder</th>
<th class="n">felter</th><th class="n">median endring</th>
<th class="n">største</th><th class="n">dager etter</th></tr>
{"".join(tr)}
</table>
<div class="merk">
 «dager etter» er tiden fra den opprinnelige utgivelsen til revisjonen,
 lest av <code>published_at</code> på hver side.
 <b>≤</b> betyr ØVRE GRENSE: den nyere påstanden bærer ingen
 utgivelsesdato, og <code>fetched_at</code> brukes som grense. Det
 gjelder alle biomasse-radene — de nyere snapshotene er skrevet før
 <code>published_at</code> fantes, og fylles ikke inn retroaktivt.
 <br>Biomasse har bare ÉN revisjonshendelse så langt (Wayback-kopien
 utgitt 2024-07-20 mot dagens fil), så min og maks er samme tall. Det er
 én måling, ikke en fordeling.
</div>

<h2 class="k2">Verifisering — kan hver rad spores til de to snapshotene?</h2>
<div class="merk">
 Påstanden om at ingen andre har tatt vare på de gamle versjonene holder
 bare hvis hver revisjonsrad kan gjenfinnes i dataene. Fem rader er
 slått opp i snapshotene, ikke i koden som skrev dem —
 <b>{ok} av {len(sjekk)} stemmer</b>.
 <br>Versjonene sorteres på <code>published_at</code>, aldri på filnavn:
 for biomasse bærer <code>.2.parquet</code> den ELDSTE påstanden.
</div>
<table>
<tr><th>kilde</th><th>observed_at</th><th>område</th><th>felt</th>
<th>eldst utgitt</th><th>verdi da</th>
<th>nyest utgitt</th><th>verdi nå</th><th>utfall</th></tr>
{"".join(spor)}
</table>
"""


def html(data: dict) -> str:
    # `</` brytes opp: en verdi som inneholder "</script>" ville ellers
    # lukket taggen og ødelagt sida.
    nyttelast = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    kildeledd = kildeledd_html()
    revisjon = revisjoner_html()

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
 /* Egen farge, ikke rød: en revisjon er ikke en feil. Den er kilden som
    har uttalt seg om det samme tidspunktet en gang til. */
 .rev {{ color: #05628a; font-weight: 600; }}
 input {{ font: inherit; padding: 3px 6px; width: 18rem; }}
 .merk {{ color: #666; margin: .3rem 0 1rem; }}
 .k2 {{ font-size: 1rem; margin: 2rem 0 .3rem;
        border-top: 2px solid #111; padding-top: .6rem; }}
 .figrad {{ display: grid; gap: .8rem 1.2rem;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            margin-bottom: 1.2rem; }}
 .fig {{ border: 1px solid #ddd; padding: .4rem .5rem; }}
 .figh {{ font-size: 11px; margin-bottom: .2rem; }}
 .figx {{ display: flex; justify-content: space-between;
          font-size: 10px; color: #888; }}
 .dim {{ color: #888; font-weight: normal; }}
 .fig svg {{ display: block; }}
</style>

<h1>Feltoversikt</h1>
<div class="sub">Visning 2 av 5. Ett felt per rad, sortert fallende på antall endringer.</div>
{kildeledd}
{revisjon}
<h2 class="k2">Felter</h2>

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
         ['distinkte','n'],['endringer','n'],['revidert','n'],['type',''],
         ['eksempler','']]) {{
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
      // Egen kolonne, og tom celle framfor 0: en revisjon er ikke en
      // liten endring, den er en annen slags påstand. Blandes de i én
      // kolonne, leses «kilden skrev om fortiden» som «det skjedde noe».
      celle(tr, f.revisjoner || '', f.revisjoner ? 'n rev' : 'n');
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
    + (DATA.revisjon_totalt
        ? ` (+${{DATA.revisjon_totalt}} rader revisjon over `
          + `${{DATA.reviderte_perioder}} perioder — kilden har uttalt seg `
          + `om samme tidspunkt flere ganger; ikke bevegelse i verden)`
        : ``)
    + `. `
    + `Gul rad = én distinkt verdi, feltet kan ikke endre seg. `
    + `Rød prosent = under 50 % dekning. `
    + `Blå «revidert» = kilden skrev om fortiden.`;
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
    if data["revisjon_totalt"]:
        print(f"  revisjon (ikke bevegelse): {data['revisjon_totalt']} rader "
              f"over {data['reviderte_perioder']} perioder")
    print(f"  filstørrelse: {mb:.2f} MB")
    if mb > STOR_FIL_MB:
        print(f"  ADVARSEL: over {STOR_FIL_MB} MB. Se 'Navngitt feilmodus' "
              f"i docs/VISNING.md — per-entitet-detalj bør ut i egne filer.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
