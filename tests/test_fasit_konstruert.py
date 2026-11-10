"""Fasiten mot konstruerte kropper: svakhetene i kjeden, prøvd én for én.

Økt L punkt 5. Fordelingen 2026 er ikke publisert, og 2025-kroppene kan
bare vise at kjeden finner en bom. Her bygges et regneark for 2026 av
pakke 2s egen forventning: lokalitetslista er A2s nøkkel (snapshotet
31.08) med Havbruksstasjonen, kommunene og fylkeskommunene er summen av
den, og beløpene er andelen av 1 600 og 400 millioner kroner. Det
regnearket SKAL gi traff på alt (`test_grunnlaget_gir_traff_paa_alt`).
Hver prøve under endrer én ting og holder fasiten mot det endringen skal
gi:

    ny form           2025-formen, «Andel i %» i prosent, ukjent
                      kolonnenavn, ny tittel, tall som tekst, uten
                      lokalitetsark, bare pressemeldingen, en
                      pressemelding i ukjent form
    ulikt kommunesett en kommune mangler, et nytt kommunenummer
    andre lokaliteter uten Havbruksstasjonen, uten HØGÅS, med en av de
                      ni, MTB fra feltet kapasitet, en lokalitet
                      registeret ikke har, en vi har som de ikke har, en
                      MTB som ikke står i registeret

Kroppen legges i et midlertidig arkiv ved siden av lenker til de ekte
kroppene fasiten også leser (eierskapet 02.09 og regnearket 2025).
Trenger datarepoet; hoppes over uten det.
"""
import gzip
import hashlib
import io
import json
from pathlib import Path

import pytest

import fasit_havbruksfond as fa
import havbruksfond as h
from core import paths, snapshot

DATAREPO = Path(__file__).resolve().parent.parent.parent / "havbruk-radar-data" / "data"
pytestmark = pytest.mark.skipif(
    not (DATAREPO / "raw" / "akvakultur" / f"{h.FOR}.parquet").exists(),
    reason="datarepoet ligger ikke ved siden av")

KOMMUNER_KR = 1_600_000_000.0
FYLKER_KR = 400_000_000.0
URL = "https://www.fiskeridir.no/akvakultur/havbruksfondet/_/attachment/download/x/2026.xlsx"


@pytest.fixture(scope="module")
def grunnlag():
    """Pakke 2 og nøkkelen, lest én gang."""
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
        mp.setattr(paths, "ARKIV_DIR", DATAREPO / "arkiv")
        p2 = h.pakke2()
        nokkel = h.nokkel(h.FOR)
        yield {"p2": p2, "nokkel": nokkel, "lok": nokkel.lok}


def lokaliteter(g) -> list[dict]:
    """Lokalitetslista slik Fiskeridirektoratet ville skrevet den, hvis
    pakke 2 har rett: én rad per lokalitet og kommune."""
    p2, rader = g["p2"], []
    for komnr, plasser in g["nokkel"].plasser.items():
        for p in plasser:
            rader.append({"nr": p.nr, "navn": p.navn, "komnr": komnr,
                          "kommune": p2["kommuner"][komnr]["navn"],
                          "kap": p.mtb, "andel": p.del_})
    for x in p2["lokaliteter"]:
        if x["paastand"] == "P2-3":
            rader.append({"nr": x["nr"], "navn": x["navn"], "komnr": "5501",
                          "kommune": "TROMSØ", "kap": x["mtb"], "andel": 1.0})
    return rader


def ark(g, rader: list[dict], aar: int = 2026, form: str = "2024") -> dict[str, list[list]]:
    """Arkene i regnearket, i 2024-formen (et partallsår) eller 2025-formen."""
    p2 = g["p2"]
    kom: dict[str, float] = {}
    for r in rader:
        kom[r["komnr"]] = kom.get(r["komnr"], 0.0) + r["kap"] * r["andel"]
    total = sum(kom.values())
    fyl: dict[str, float] = {}
    for k, t in kom.items():
        fyl[k[:2]] = fyl.get(k[:2], 0.0) + t
    knavn = {k: (p2["kommuner"].get(k) or {}).get("navn") or next(
        r["kommune"] for r in rader if r["komnr"] == k) for k in kom}
    utbet = [[f"Utbetalinger fra Havbruksfondet {aar}"]]
    if form == "2025":
        utbet.append(["KOMNR", "KOMMUNE", "ANDEL NYKLARERT", "ORDINÆR UTBETALING", "TOTALT"])
        utbet += [[k, knavn[k], 0.0, t / total * KOMMUNER_KR, t / total * KOMMUNER_KR]
                  for k, t in sorted(kom.items())]
        kommuner = [["", "", "", "", "", "Avsatt til klarert ny lokalitets-MTB"], [""], [""],
                    ["LOK_KOMNR", "LOK_KOM", "FYLKESNR", "FYLKE", "KAP REG", "i %"]]
        fylker = [["", f"Havbruksfond til utbet. {aar}", "", "", FYLKER_KR],
                  ["FYLKESNR", "FYLKE", "KAP", "ANDEL", "BELØP"]]
        lok = [["Lokaliteter registrert i Akvakulturregisteret"],
               ["LOK_NR", "LOK_NAVN", "LOK_KOMNR", "LOK_KOM", "LOK_KAP", "Andel i %",
                "Kapasitet justert"]]
        lok += [[r["nr"], r["navn"], r["komnr"], r["kommune"], r["kap"], r["andel"],
                 r["kap"] * r["andel"]] for r in rader]
        lokark = f"Lok. per. 01.09.{aar % 100}"
    else:
        utbet.append(["KOMNR", "KOMMUNE", "ORDINÆR UTBETALING", "TOTALT"])
        utbet += [[k, knavn[k], t / total * KOMMUNER_KR, t / total * KOMMUNER_KR]
                  for k, t in sorted(kom.items())]
        kommuner = [[f"Havbruksfondet {aar} til utbetaling", "", KOMMUNER_KR],
                    ["LOK_KOMNR", "LOK_KOM", "Fylkesnr", "Fylke", "Kapasitet", "Andel",
                     "Ordinær utbet"]]
        fylker = [[f"Havbruksfondet {aar} til utbetaling", "", "", "", FYLKER_KR], [""], [""],
                  ["Fylkesnr", "Fylke", "Kapasitet", "Andel", "Ordinær utbet"]]
        lok = [["Lokaliteter registrert i Akvakulturregisteret"],
               ["KOMMUNE_NAVN", "KOMMUNE_KODE", "LOKNR", "LOK_NAVN", "LOK_KAP", "Andel i %",
                "Kapasitet justert"]]
        lok += [[r["kommune"], r["komnr"], r["nr"], r["navn"], r["kap"], r["andel"],
                 r["kap"] * r["andel"]] for r in rader]
        lokark = f"Lok. per 01.09.{aar % 100}"
    kommuner += [[k, knavn[k], k[:2], p2["fylker"].get(k[:2], {}).get("navn", ""), t,
                  t / total] + ([t / total * KOMMUNER_KR] if form == "2024" else [])
                 for k, t in sorted(kom.items())]
    fylker += [[f, p2["fylker"].get(f, {}).get("navn", f), t, t / total, t / total * FYLKER_KR]
               for f, t in sorted(fyl.items())]
    return {"Utbetalingsoversikt": utbet, "Kommuner": kommuner,
            "Fylkeskommuner": fylker, lokark: lok}


def xlsx(arkene: dict[str, list[list]]) -> bytes:
    import xlsxwriter
    ut = io.BytesIO()
    bok = xlsxwriter.Workbook(ut, {"in_memory": True})
    for navn, rader in arkene.items():
        a = bok.add_worksheet(navn)
        for i, rad in enumerate(rader):
            for j, v in enumerate(rad):
                if isinstance(v, (int, float)):
                    a.write_number(i, j, v)
                elif v != "":
                    a.write_string(i, j, str(v))
    bok.close()
    return ut.getvalue()


@pytest.fixture
def arkiv(tmp_path, monkeypatch):
    """Et midlertidig arkiv: lenker til de ekte kroppene fasiten leser ved
    siden av, og en funksjon som legger inn en konstruert kropp."""
    rot = tmp_path / "arkiv"
    (rot / "havbruksfondet").mkdir(parents=True)
    (rot / "eierskap").symlink_to(DATAREPO / "arkiv" / "eierskap")
    (rot / "havbruksfondet" / "2026-10-12.8.bin.gz").symlink_to(
        DATAREPO / "arkiv" / "havbruksfondet" / "2026-10-12.8.bin.gz")
    monkeypatch.setattr(snapshot, "RAW_DIR", DATAREPO / "raw")
    monkeypatch.setattr(paths, "ARKIV_DIR", rot)
    monkeypatch.setattr(h, "skaringsmappe", lambda: tmp_path / "havbruksfond")

    def legg_inn(data: bytes, mappe: str = "havbruksfondet", navn: str = "2026-11-12.bin.gz",
                 hva: str = "vedlegg") -> str:
        (rot / mappe).mkdir(exist_ok=True)
        (rot / mappe / navn).write_bytes(gzip.compress(data))
        sha = hashlib.sha256(data).hexdigest()
        logg = rot / "havbruksfondet" / "2026-11-12.logg.json"
        poster = json.loads(logg.read_text()) if logg.exists() else []
        poster.append({"hva": hva, "url": URL, "observed_at": navn[:10], "sha256": sha,
                       "ny": True, "fetched_at": "2026-11-12T14:45:00+00:00",
                       "published_at": ""})
        logg.write_text(json.dumps(poster))
        return sha
    return legg_inn


def fasit():
    return fa.fasit(2026, nett=False)


def utfall(f) -> dict[str, str]:
    return {"P1": f["pakke1"]["utfall"], **{x["paastand"]: x["utfall"] for x in f["pakke2"]}}


TRAFF = {"P1": "traff", **{f"P2-{i}": "traff" for i in range(1, 10)}}


def kommune(f, nr):
    return next(k for k in f["avvik"]["kommuner"] if k["nr"] == nr)


# ---------------------------------------------------------------- grunnlaget


def test_grunnlaget_gir_traff_paa_alt(grunnlag, arkiv, tmp_path):
    """Er Fiskeridirektoratets regneark det pakke 2 forventet, treffer begge
    pakkene på alt, og det er ingen avvik. Uten denne kunne kjeden bare
    funnet bom."""
    sha = arkiv(xlsx(ark(grunnlag, lokaliteter(grunnlag))))
    f = fasit()
    assert f["tabell"]["sha256"] == sha and f["tabell"]["url"] == URL
    assert utfall(f) == TRAFF
    assert [x["slaar_til"] for x in f["pakke1"]["ledd"]] == [False] * 4
    assert f["avvik"]["lokaliteter"] == [] and sum(f["avvik"]["antall"].values()) == 0
    assert f["sider"]["kommuner"]["5501"]["andel"] == pytest.approx(0.015475, abs=5e-7)
    assert fa.main(["--uten-nett"]) == 0
    assert (tmp_path / "havbruksfond" / "fasit-2026.md").exists()


# ------------------------------------------------------------------ ny form


def test_2025_formen_leses_ogsaa(grunnlag, arkiv):
    """Navnene fra oddetallsåret: ANDEL NYKLARERT (her 0), KAP REG, BELØP
    og en annen kolonnerekkefølge i lokalitetsarket."""
    arkiv(xlsx(ark(grunnlag, lokaliteter(grunnlag), form="2025")))
    f = fasit()
    assert utfall(f) == TRAFF
    assert f["pakke1"]["ledd"][0]["tall"] == {"kolonnen_finnes": True, "kommuner_over_0": []}


def test_andel_i_prosent_deles_og_sies(grunnlag, arkiv):
    a = ark(grunnlag, lokaliteter(grunnlag))
    lok = a["Lok. per 01.09.26"]
    for r in lok[2:]:
        r[5] = r[5] * 100
    arkiv(xlsx(a))
    f = fasit()
    assert utfall(f) == TRAFF
    assert any("prosent" in m for m in f["tabell"]["merknader"])


def test_et_ukjent_kolonnenavn_er_les_for_haand(grunnlag, arkiv, tmp_path):
    a = ark(grunnlag, lokaliteter(grunnlag))
    a["Utbetalingsoversikt"][1][0] = "Kommunenr."
    arkiv(xlsx(a))
    assert fa.main(["--uten-nett"]) == 3
    assert not (tmp_path / "havbruksfond").exists()


def test_en_ny_tittel_er_les_for_haand(grunnlag, arkiv, tmp_path, capsys):
    """Kjent på tittelen er bare kjent så lenge tittelen står. Et nytt
    vedlegg uten den skal ikke gi «ikke arkivert ennå»."""
    a = ark(grunnlag, lokaliteter(grunnlag))
    a["Utbetalingsoversikt"][0] = ["Havbruksfondet 2026 – utbetaling til kommuner"]
    arkiv(xlsx(a))
    assert fa.main(["--uten-nett"]) == 3
    assert URL in capsys.readouterr().err
    assert not (tmp_path / "havbruksfond").exists()


def test_tall_som_tekst_er_les_for_haand(grunnlag, arkiv):
    a = ark(grunnlag, lokaliteter(grunnlag))
    for r in a["Utbetalingsoversikt"][2:]:
        r[3] = f"{r[3]:,.2f}".replace(",", " ").replace(".", ",")
    arkiv(xlsx(a))
    assert fa.main(["--uten-nett"]) == 3


def test_uten_lokalitetsark_venter_de_som_trenger_det(grunnlag, arkiv):
    """P2-1 og P2-2 avgjøres av «Kommuner»; P2-3 til P2-6 venter, og
    grupperingen sier at den er foreløpig."""
    a = ark(grunnlag, lokaliteter(grunnlag))
    del a["Lok. per 01.09.26"]
    arkiv(xlsx(a))
    f = fasit()
    u = utfall(f)
    assert [u[f"P2-{i}"] for i in range(1, 10)] == ["traff", "traff", "venter", "venter",
                                                     "venter", "venter", "traff", "traff",
                                                     "traff"]
    assert u["P1"] == "traff" and f["avvik"]["foreloepig"]
    assert any("lokalitetslista ikke lest" in m for m in f["tabell"]["merknader"])


def _pressemelding(g, rader, dato="12.11.2026") -> bytes:
    """Formen fra 10.11.2025 (A3), med kommunenavn og hele kroner."""
    a = ark(g, rader)
    kom = " ".join(f"{r[1]} {round(r[3]):,}".replace(",", " ")
                   for r in a["Utbetalingsoversikt"][2:])
    fyl = " ".join(f"{r[1]} {round(r[4]):,}".replace(",", " ")
                   for r in a["Fylkeskommuner"][4:])
    return (f"<html><body><p>Pressemelding | Dato: {dato} | Nærings- og "
            f"fiskeridepartementet</p><p>Havbruksfondet fordeler. Utbetalinger fra "
            f"Havbruksfondet 2026 KOMMUNE TOTALT {kom} Fylkeskommune Utbetaling {fyl} "
            f"Totalt: {round(KOMMUNER_KR + FYLKER_KR):,} kroner</p></body></html>"
            .replace(",", " ")).encode()


def test_bare_pressemeldingen(grunnlag, arkiv):
    """Kommer meldingen før regnearket, avgjøres det som kan avgjøres av
    den: ledd 2–4 i pakke 1 og P2-7 til P2-9. Ledd 1 og P2-1 til P2-6
    venter, og pakke 1 med dem."""
    arkiv(_pressemelding(grunnlag, lokaliteter(grunnlag)),
          mappe="regjeringen-pressemeldinger", hva="regjeringen")
    f = fasit()
    assert f["tabell"]["form"] == "pressemelding" and f["tabell"]["dato"] == "2026-11-12"
    u = utfall(f)
    assert u["P1"] == "venter"
    assert [x["slaar_til"] for x in f["pakke1"]["ledd"]] == [None, False, False, False]
    assert [u[f"P2-{i}"] for i in range(1, 10)] == ["venter"] * 6 + ["traff"] * 3
    assert f["avvik"]["foreloepig"]


def test_en_pressemelding_i_ukjent_form_er_les_for_haand(grunnlag, arkiv):
    arkiv(b"<html><body><p>Dato: 12.11.2026</p><p>Havbruksfondet: 2 milliarder til "
          b"143 kommuner. Se vedlegget for fordelingen per kommune.</p></body></html>",
          mappe="ntb-pressemeldinger", hva="ntb")
    assert fa.main(["--uten-nett"]) == 3


# ------------------------------------------------------- ulikt kommunesett


def test_en_kommune_mangler(grunnlag, arkiv):
    """Surnadal (én lokalitet, 780 t) står ikke i fordelingen."""
    rader = [r for r in lokaliteter(grunnlag) if r["komnr"] != "1566"]
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    assert f["pakke1"]["ledd"][1]["tall"] == {"bare_i_fordelingen": [],
                                             "bare_i_anslaget": ["1566"]}
    u = utfall(f)
    assert u["P1"] == "bom" and u["P2-8"] == "bom" and u["P2-1"] == "bom"
    assert kommune(f, "1566")["gruppe"] == "V"


def test_et_nytt_kommunenummer(grunnlag, arkiv):
    """Fiskeridirektoratet fører Haram under et nummer registeret ikke har.
    Registeret sier 1580, listen sier noe annet: det er grunnlaget."""
    rader = lokaliteter(grunnlag)
    for r in rader:
        if r["komnr"] == "1580":
            r["komnr"] = "1599"
    a = ark(grunnlag, rader)
    arkiv(xlsx(a))
    f = fasit()
    assert f["pakke1"]["ledd"][1]["tall"] == {"bare_i_fordelingen": ["1599"],
                                             "bare_i_anslaget": ["1580"]}
    assert utfall(f)["P1"] == "bom"
    assert kommune(f, "1580")["gruppe"] == "R"
    assert kommune(f, "1599")["gruppe"] == "R"


# ------------------------------------------------------- andre lokaliteter


def test_uten_havbruksstasjonen(grunnlag, arkiv):
    """Det pakke 1 antok og pakke 2 ikke gjorde: pakke 1 treffer, P2-3,
    P2-7 og P2-8 bommer, og Tromsø og Troms er grensetilfeller."""
    rader = [r for r in lokaliteter(grunnlag) if r["nr"] not in ("10768", "15236")]
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    u = utfall(f)
    assert u["P1"] == "traff"
    assert {k for k, v in u.items() if v == "bom"} == {"P2-3", "P2-7", "P2-8"}
    assert kommune(f, "5501")["gruppe"] == "G"
    assert next(x for x in f["avvik"]["fylker"] if x["nr"] == "55")["gruppe"] == "G"


def test_uten_hogaas(grunnlag, arkiv):
    rader = [r for r in lokaliteter(grunnlag) if r["nr"] != "38097"]
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    assert utfall(f)["P2-4"] == "bom" and kommune(f, "1130")["gruppe"] == "G"


def test_en_av_de_ni_er_med(grunnlag, arkiv):
    rader = lokaliteter(grunnlag) + [{"nr": "22296", "navn": "GRØNSET", "komnr": "1557",
                                     "kommune": "GJEMNES", "kap": 3120.0, "andel": 1.0}]
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    assert utfall(f)["P2-5"] == "bom" and kommune(f, "1557")["gruppe"] == "G"


def _med_midlertidig(g) -> str:
    """En lokalitet i nøkkelen, ikke et grensetilfelle, der klarert og
    midlertidig kapasitet er ulike, i en kommune i gruppe U."""
    grense = {x["nr"] for x in g["p2"]["lokaliteter"]}
    for komnr in g["p2"]["grupper"]["U"]:
        for p in g["nokkel"].plasser.get(komnr, []):
            r = g["lok"][p.nr]
            if (p.nr not in grense and p.del_ == 1 and r.get("kapasitet")
                    and r.get("kapasitet_midlertidig")
                    and float(r["kapasitet"]) < float(r["kapasitet_midlertidig"])):
                return p.nr
    pytest.skip("ingen lokalitet med midlertidig kapasitet over klarert i gruppe U")


def test_mtb_fra_feltet_kapasitet_er_var_feil(grunnlag, arkiv):
    """Bruker Fiskeridirektoratet `kapasitet` der vi brukte det høyeste av
    de to, er det vekten vår som bommer, og det kan vises."""
    nr = _med_midlertidig(grunnlag)
    rader = lokaliteter(grunnlag)
    for r in rader:
        if r["nr"] == nr:
            r["kap"] = float(grunnlag["lok"][nr]["kapasitet"])
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    lok = next(x for x in f["avvik"]["lokaliteter"] if x["nr"] == nr)
    assert lok["gruppe"] == "V" and "feltet kapasitet" in lok["hvorfor"]
    assert utfall(f)["P2-1"] == "bom"


def test_en_lokalitet_registeret_ikke_har(grunnlag, arkiv):
    rader = lokaliteter(grunnlag) + [{"nr": "99901", "navn": "OPPDIKTET", "komnr": "5014",
                                     "kommune": "FRØYA", "kap": 1000.0, "andel": 1.0}]
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    lok = next(x for x in f["avvik"]["lokaliteter"] if x["nr"] == "99901")
    assert lok["gruppe"] == "R" and "ikke i registeret" in lok["hvorfor"]
    assert utfall(f)["P2-2"] == "bom" and kommune(f, "5014")["gruppe"] == "R"


def test_en_lokalitet_vi_har_og_de_ikke_har(grunnlag, arkiv):
    """Den største lokaliteten i Senja (gruppe U) er ikke på listen. Den
    består filteret og står i registeret begge dagene: filteret vårt tar
    med noe de holder ute."""
    senja = max(grunnlag["nokkel"].plasser["5530"], key=lambda p: p.tonn).nr
    rader = [r for r in lokaliteter(grunnlag) if r["nr"] != senja]
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    assert utfall(f)["P2-1"] == "bom" and kommune(f, "5530")["gruppe"] == "V"


def test_en_mtb_som_ikke_star_i_registeret(grunnlag, arkiv):
    senja = max(grunnlag["nokkel"].plasser["5530"], key=lambda p: p.tonn).nr
    rader = lokaliteter(grunnlag)
    for r in rader:
        if r["nr"] == senja:
            r["kap"] += 333.0
    arkiv(xlsx(ark(grunnlag, rader)))
    f = fasit()
    lok = next(x for x in f["avvik"]["lokaliteter"] if x["nr"] == senja)
    assert lok["gruppe"] == "R" and "ikke står i noe felt" in lok["hvorfor"]
    assert kommune(f, "5530")["gruppe"] == "R"


# ------------------------------------- funnet med kroppene over (10.11.2026)


def test_rader_som_ikke_kan_leses_er_les_for_haand(grunnlag, arkiv):
    """Overskriften er kjent, men ingen rad har et kommunenummer i
    sifre. Det er ikke en fordeling uten kommuner; det er en form vi
    ikke kan lese."""
    a = ark(grunnlag, lokaliteter(grunnlag))
    for r in a["Utbetalingsoversikt"][2:]:
        r[0] = f"K{r[0]}"
    arkiv(xlsx(a))
    assert fa.main(["--uten-nett"]) == 3


def test_et_kommunenavn_uten_treff_i_pressemeldingen_er_les_for_haand(grunnlag, arkiv):
    """Et navn meldingen skriver annerledes enn pakke 2, skal ikke leses
    som en kommune som er kommet til og en som er borte (ledd 2)."""
    data = _pressemelding(grunnlag, lokaliteter(grunnlag)).replace(
        "HERØY I NORDLAND".encode(), "HERØY (NORDLAND)".encode())
    arkiv(data, mappe="regjeringen-pressemeldinger", hva="regjeringen")
    assert fa.main(["--uten-nett"]) == 3


def test_en_ukjent_utbetalingskolonne_sies(grunnlag, arkiv):
    """Ledd 1 leses ordrett: kolonnen heter ANDEL NYKLARERT. Kaller
    Fiskeridirektoratet den noe annet, slår ikke ledd 1 til, men fila
    skal si at TOTALT er mer enn ORDINÆR UTBETALING, og hvilken kolonne
    som er ukjent."""
    a = ark(grunnlag, lokaliteter(grunnlag))
    a["Utbetalingsoversikt"][1].insert(2, "NY MTB")
    for r in a["Utbetalingsoversikt"][2:]:
        r.insert(2, 1000.0)
        r[4] += 1000.0
    arkiv(xlsx(a))
    f = fasit()
    assert f["pakke1"]["ledd"][0]["slaar_til"] is False
    m = " ".join(f["tabell"]["merknader"])
    assert "NY MTB" in m and "143" in m
