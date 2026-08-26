"""Hva et analyseresultat hvilte på, skrevet ned sammen med resultatet.

    rho = +0,761

Det tallet er ikke en egenskap ved dataene. Det er en egenskap ved
dataene OG ved omtrent tolv valg som ikke står noe sted: hvilke år,
hvilke uker, hvilket mål, hvilken fasitversjon, hvilken PERSONFORMER-
liste, og — nytt siden 26.08.2026 — hvilken PÅSTAND om hver måned som
lå på disk den dagen. Om tre måneder kan ingen svare på om et nytt tall
er et nytt funn eller et endret valg.

Det er samme klasse feil som utvalgsutvidelsen (F9), feltnormalen (F10)
og løpenummeret (F14): en verdi UTENFOR dataene avgjør hva de betyr.
Regel 1b-3 stiller prøven for et snapshot — «kan raden alene svare på
hva denne verdien var da den ble skrevet?» — og den gjelder ordrett for
et analyseresultat.

## Hvorfor lesingen går HERFRA og ikke ved siden av

Loggen kunne vært en liste kalleren fyller ut selv. Den ville vært feil
på nøyaktig den måten F6, F7 og F8 var feil: to tellere for samme sak,
som holder helt til de svarer ulikt. En analyse som leser `lusetall`
gjennom `snapshot.les_mellom()` og SEPARAT skriver «leste lusetall
2018–2026» i loggen, påstår noe om lesingen framfor å beskrive den.

Derfor er `Kjoringslogg.les()` selve lesedøra. Loggen kan ikke si noe
annet enn det som faktisk ble lest, fordi den skrives av lesingen.

## Versjonsvalget er et VALG, og det var usynlig før 26.08.2026

`snapshot.les_mellom()` gir flere innslag for en dato som har flere
versjoner, og kallerne tar det siste. Det var en trygg antakelse så
lenge et høyere løpenummer også bar en nyere påstand. Etter at
Wayback-kopien ble skrevet inn er det ikke det: 81 biomassemåneder har
en `.2` utgitt 20.07.2024 ved siden av en `.parquet` utgitt to år
senere.

Én av de to er «gjeldende», og hvilken det er avgjør tallet. En analyse
som ikke sier hvilken den leste, er ikke reproduserbar — den er bare
tilfeldigvis riktig så lenge ingen skriver inn flere arkivkopier.

Derfor har `les()` et EKSPLISITT `versjonsvalg`, og loggen fører
løpenummer og `published_at` for hver eneste fil.

## Klokka slås opp ett sted

`kjort_at` settes i `__init__` og leses derfra av alt annet. En logg med
to tidspunkter fra to oppslag er F7 i miniatyr. Tidspunktet handler om
OSS — når vi kjørte — og da er veggklokka riktig klokke (1b-1).
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from core import persondata, snapshot

ROT = Path(__file__).resolve().parent.parent

# Versjonsvalgene, som navn og ikke som bar sannhet i en if-setning.
#
# GJELDENDE er den SIST UTGITTE versjonen av en dato — samme valg som
# `snapshot.forrige_versjon()` og `previous()` gjør, altså den påstanden
# resten av systemet behandler som den som står. Det er standarden fordi
# en analyse normalt vil lese det kilden sier NÅ.
#
# FORSTE er den først utgitte. Den finnes for å kunne spørre «hva ville
# denne analysen gitt før kilden reviderte».
GJELDENDE = "gjeldende"
FORSTE = "forste"

# Verdien som skrives der et tidspunkt ikke er kjent. Tom streng ville
# lest som en kolonne som mangler; dette er en påstand om fravær.
UKJENT = "(ukjent)"


@dataclass(frozen=True)
class Lesing:
    """Én snapshot-FIL som gikk inn i resultatet.

    `versjon` og `published_at` står ved siden av hverandre med vilje: de
    to var samme opplysning fram til 26.08.2026, og er det ikke lenger.
    Løpenummeret sier når VI skrev fila, `published_at` når KILDEN utga
    innholdet. Se CLAUDE.md 1b-7.
    """

    kilde: str
    observed_at: str
    versjon: int
    published_at: str      # UKJENT der kilden ikke sa noe
    fetched_at: str        # UKJENT der radene spriker
    source_version: str
    utvalg: str
    n_rader: int


@dataclass(frozen=True)
class Forkastet:
    """En dato som lå i intervallet, men ikke gikk inn i resultatet.

    Skilles fra en dato som aldri fantes: den første er et valg
    analysen gjorde, den andre er et hull i historikken. Bare den
    første hører hjemme i en logg over valg — men den hører definitivt
    hjemme der, fordi «uke 52/2017 ble lest» og «uke 52/2017 ble
    forkastet av ISO-årsavgrensningen» gir ulike tall.
    """

    kilde: str
    observed_at: str
    grunn: str


def _sha256(sti: Path) -> str:
    return hashlib.sha256(sti.read_bytes()).hexdigest()


def _git(*args: str) -> str:
    """Git-svar som RÅ tekst, eller tom streng om git ikke svarer.

    Faller stille tilbake på tom streng framfor å kaste: en analyse som
    kjøres fra en tarball uten .git skal skrive en logg som sier at
    committen er ukjent, ikke la være å skrive noen logg.

    RÅ, altså uten `.strip()`. Første utkast strippet her, og det spiste
    det ledende mellomrommet i `git status --porcelain`: en umodifisert-i-
    indeks-fil kommer som `" M sti"`, og etter stripping ble `linje[3:]`
    til `"nalyse/..."`. Feilen er liten og illustrerende — en logg som
    skal gjøre valg etterprøvbare kan ikke selv forkorte filnavn.
    """
    try:
        ferdig = subprocess.run(["git", "-C", str(ROT), *args],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return ""
    return ferdig.stdout if ferdig.returncode == 0 else ""


def _tell(verdier: list[str]) -> str:
    """`['1','1','2']` -> `'1×2, 2×1'`. Sortert, altså determinstisk.

    Finnes fordi en logg som lister `source_version` for 400 filer er
    uleselig, mens «alle 400 hadde versjon 1» er nettopp det leseren
    trenger — og «399 hadde versjon 1, én hadde versjon 2» er et funn.
    """
    if not verdier:
        return "(ingen)"
    antall: dict[str, int] = {}
    for v in verdier:
        antall[v] = antall.get(v, 0) + 1
    return ", ".join(f"{k}×{n}" for k, n in sorted(antall.items()))


class Kjoringslogg:
    """Samler valgene mens analysen tas, og skriver dem ved siden av den.

    Bruk:

        logg = Kjoringslogg("lusepress_mot_fasit", UT / "lusepress.kjoring.log")
        logg.valg("avgrensning.fra_aar", 2018)
        for dato, ramme in logg.les("lusetall", "2017-12-01", "2027-01-31"):
            ...
        logg.skriv()
    """

    def __init__(self, navn: str, sti: Path) -> None:
        self.navn = navn
        self.sti = Path(sti)
        # ETT klokkeoppslag for hele kjøringen. Se modulens docstring.
        self.kjort_at = dt.datetime.now(dt.timezone.utc).isoformat()
        self._valg: list[tuple[str, str]] = []
        self._filer: list[tuple[str, Path]] = []
        self._lesinger: list[Lesing] = []
        self._forkastet: list[Forkastet] = []
        self._versjonsvalg: dict[str, str] = {}

    # ------------------------------------------------------------ valg

    def valg(self, nokkel: str, verdi: object) -> None:
        """Ett valg som påvirket resultatet.

        Verdien tvinges til tekst her og ikke ved skriving, fordi det er
        her den er kjent. En liste blir kommaseparert i den rekkefølgen
        kalleren ga den — er rekkefølgen tilfeldig, er den et valg
        kalleren må sortere selv.
        """
        if isinstance(verdi, (list, tuple)):
            tekst = ", ".join(str(v) for v in verdi)
        elif isinstance(verdi, bool):
            tekst = "ja" if verdi else "nei"
        else:
            tekst = str(verdi)
        self._valg.append((nokkel, tekst))

    def fil(self, nokkel: str, sti: Path) -> None:
        """En INNGANGSFIL som ikke er et snapshot — fasiten, en terskelfil.

        Innholds-hash og ikke banen alene: fasiten er en CSV som kan
        redigeres uten at noe annet endrer seg, og da er banen den samme
        og tallet et annet.
        """
        self._filer.append((nokkel, Path(sti)))

    # ---------------------------------------------------------- lesing

    def les(self, kilde: str, fra: str, til: str,
            versjonsvalg: str | int = GJELDENDE,
            behold=None, forkastningsgrunn: str = "") -> list[tuple[str, pl.DataFrame]]:
        """Snapshots i [fra, til], eldst først — og loggen som beskriver dem.

        Returnerer det samme som `snapshot.les_mellom()` ville gjort for
        `versjonsvalg=GJELDENDE` og datoer uten flere versjoner, men med
        ÉN forskjell som er hele poenget: der en dato har flere versjoner,
        gir denne nøyaktig én av dem, og loggen sier hvilken.

        `versjonsvalg`:
            GJELDENDE   sist utgitte versjon av hver dato (standard)
            FORSTE      først utgitte
            et heltall  det løpenummeret, der det finnes. Datoer uten det
                        forkastes og føres som forkastet — de forsvinner
                        ikke stille.

        `behold(dato) -> bool` er avgrensninger som ikke lar seg uttrykke
        som et datointervall. Den viktige er ISO-år mot kalenderdato: et
        vindu må være en dag vidt i hver ende rundt nyttår, og datoene som
        faller utenfor ISO-året skal forkastes ETTER at intervallet er
        hentet. Forkastede datoer LESES IKKE — de føres med
        `forkastningsgrunn`, slik at loggen skiller «vi valgte bort denne»
        fra «den fantes ikke».
        """
        self._sett_versjonsvalg(kilde, versjonsvalg)
        ut: list[tuple[str, pl.DataFrame]] = []

        for dato in snapshot.datoer(kilde):
            if not (fra <= dato <= til):
                continue
            if behold is not None and not behold(dato):
                self._forkastet.append(
                    Forkastet(kilde, dato, forkastningsgrunn or "behold() sa nei"))
                continue

            versjonene = snapshot.versjoner(kilde, dato)
            valgt = self._velg(versjonene, versjonsvalg)
            if valgt is None:
                self._forkastet.append(Forkastet(
                    kilde, dato,
                    f"ingen versjon med løpenummer {versjonsvalg} "
                    f"(fantes: {', '.join(str(n) for n, _ in versjonene)})"))
                continue

            nr, ramme = valgt
            self._lesinger.append(Lesing(
                kilde=kilde,
                observed_at=dato,
                versjon=nr,
                published_at=snapshot.published_at_i(ramme) or UKJENT,
                fetched_at=snapshot.fetched_at_i(ramme) or UKJENT,
                source_version=snapshot.source_version_i(ramme) or UKJENT,
                utvalg=(ramme["utvalg"][0] if "utvalg" in ramme.columns
                        and not ramme.is_empty() else "") or UKJENT,
                n_rader=ramme.height,
            ))
            ut.append((dato, ramme))

        return ut

    def les_dato(self, kilde: str, dato: str,
                 versjonsvalg: str | int = GJELDENDE) -> pl.DataFrame | None:
        """Én dato. Samme valg, samme føring — bare ett intervall på én dag."""
        lest = self.les(kilde, dato, dato, versjonsvalg=versjonsvalg)
        return lest[-1][1] if lest else None

    @staticmethod
    def _velg(versjonene: list[tuple[int, pl.DataFrame]],
              versjonsvalg: str | int) -> tuple[int, pl.DataFrame] | None:
        """Hvilken av versjonene av én dato som gjelder for denne analysen.

        `versjoner()` leverer dem ELDST UTGITT FØRST, ikke i
        filnavnrekkefølge. Det er den sorteringen GJELDENDE og FORSTE
        hviler på, og grunnen til at valget ikke gjøres på løpenummeret:
        for 81 biomassemåneder er `.2` to år ELDRE enn `.parquet`.
        """
        if not versjonene:
            return None
        if versjonsvalg == GJELDENDE:
            return versjonene[-1]
        if versjonsvalg == FORSTE:
            return versjonene[0]
        for nr, ramme in versjonene:
            if nr == versjonsvalg:
                return nr, ramme
        return None

    def _sett_versjonsvalg(self, kilde: str, versjonsvalg: str | int) -> None:
        """Én kilde, ett versjonsvalg per kjøring.

        To ulike valg for samme kilde i samme analyse ville gitt et
        resultat der halvparten av tallene hviler på én påstand og
        halvparten på en annen — og en logg som ikke kan si hvilken
        halvdel som er hvilken. Det felles her framfor å bli oppdaget
        i tallene.
        """
        tidligere = self._versjonsvalg.get(kilde)
        if tidligere is not None and tidligere != str(versjonsvalg):
            raise ValueError(
                f"{kilde} leses både med versjonsvalg {tidligere!r} og "
                f"{str(versjonsvalg)!r} i samme kjøring. Da hviler halve "
                f"resultatet på én påstand om kilden og halve på en annen, "
                f"og loggen kan ikke si hvilken halvdel som er hvilken."
            )
        self._versjonsvalg[kilde] = str(versjonsvalg)

    # --------------------------------------------------------- skriving

    @property
    def peker(self) -> str:
        """Navnet resultatfilene skal vise til. Se punkt 3: en analyse
        leser ikke git, så pekeren må gå til noe som ligger ved siden av
        resultatet."""
        return self.sti.name

    def peker_fra(self, katalog: Path) -> str:
        """Samme peker, men som en lenke som VIRKER fra `katalog`.

        Ligger loggen ved siden av resultatet — det normale — er dette
        bare filnavnet. Er den lagt et annet sted (to kjøringer som skal
        sammenlignes), blir det en relativ sti dit.

        Finnes fordi `peker` alene ga en død lenke i akkurat det
        tilfellet pekeren betyr mest: når noen har flyttet loggen for å
        sammenligne to kjøringer, og resultatfila skal si hvilken av dem
        den hører til.
        """
        return os.path.relpath(self.sti.resolve(), Path(katalog).resolve())

    def linjer(self) -> list[str]:
        """Hele loggen som linjer. Determinstisk bortsett fra `kjort_at`.

        Skilt fra `skriv()` for at reproduserbarhetstesten skal kunne
        sammenligne to kjøringer uten å skrive to filer.
        """
        ut: list[str] = [
            f"# kjøringslogg — {self.navn}",
            "#",
            "# Hva dette resultatet hvilte på. Endres én linje her, kan",
            "# tallene endre seg uten at dataene har gjort det.",
            "#",
            "# Alt utenom `kjort_at` er determinstisk: to kjøringer uten",
            "# endring gir identiske logger. Se tests/test_kjoringslogg.py.",
            "",
            self._linje("kjort_at", self.kjort_at),
            self._linje("analyse", self.navn),
            self._linje("python", sys.version.split()[0]),
            self._linje("polars", pl.__version__),
        ]

        commit = _git("rev-parse", "HEAD").strip()
        # `XY<mellomrom>STI` — de tre første tegnene er statuskoden, og
        # resten er stien slik den er, inkludert mellomrom i navnet.
        skitne = sorted(
            linje[3:] for linje in _git("status", "--porcelain").splitlines()
            if linje.strip())
        ut += [
            self._linje("git.commit", commit or UKJENT),
            self._linje("git.rent_arbeidstre", "nei" if skitne else "ja"),
        ]
        if skitne:
            ut.append(self._linje("git.endret", f"{len(skitne)} fil(er)"))
            ut += [f"    {sti}" for sti in skitne]

        # PERSONFORMER føres HER og ikke av kalleren. Lista virker i
        # `snapshot._les()`, altså inne i lesedøra denne loggen eier —
        # og en verdi som virker ved lesing skal føres av den som leser.
        # Se punkt 5 i docs/beslutninger: at den ikke er versjonert er en
        # kjent mangel, og loggen fører i det minste hva den var.
        ut += [
            "",
            self._linje("personformer", ", ".join(sorted(persondata.PERSONFORMER))),
            self._linje("personformer.virker", "ved lesing, i snapshot._les()"),
        ]

        if self._valg:
            ut.append("")
            ut += [self._linje(n, v) for n, v in self._valg]

        for nokkel, sti in self._filer:
            ut += [
                "",
                self._linje(f"{nokkel}.sti", self._relativ(sti)),
                self._linje(f"{nokkel}.sha256",
                            _sha256(sti) if sti.exists() else UKJENT),
                self._linje(f"{nokkel}.bytes",
                            sti.stat().st_size if sti.exists() else UKJENT),
            ]

        ut += self._kildeblokker()
        ut += self._fillista()
        return ut

    def _kildeblokker(self) -> list[str]:
        ut: list[str] = []
        kilder = {les.kilde for les in self._lesinger} | set(self._versjonsvalg)
        for kilde in sorted(kilder):
            mine = [les for les in self._lesinger if les.kilde == kilde]
            forkastet = [f for f in self._forkastet if f.kilde == kilde]
            p = f"lesing.{kilde}"
            ut += ["", self._linje(f"{p}.versjonsvalg",
                                   self._versjonsvalg.get(kilde, UKJENT))]
            if not mine:
                ut.append(self._linje(f"{p}.filer", 0))
            else:
                datoer = [les.observed_at for les in mine]
                hentet = sorted({les.fetched_at for les in mine} - {UKJENT})
                utgitt = sorted({les.published_at for les in mine} - {UKJENT})
                ut += [
                    self._linje(f"{p}.filer", len(mine)),
                    self._linje(f"{p}.datoer",
                                f"{len(set(datoer))}  [{min(datoer)} .. {max(datoer)}]"),
                    self._linje(f"{p}.rader", sum(les.n_rader for les in mine)),
                    self._linje(f"{p}.lopenummer",
                                _tell([str(les.versjon) for les in mine])),
                    self._linje(f"{p}.published_at",
                                f"{min(utgitt)} .. {max(utgitt)}" if utgitt
                                else UKJENT),
                    self._linje(f"{p}.published_at.ukjent",
                                sum(1 for les in mine
                                    if les.published_at == UKJENT)),
                    self._linje(f"{p}.fetched_at",
                                f"{min(hentet)} .. {max(hentet)}" if hentet
                                else UKJENT),
                    self._linje(f"{p}.source_version",
                                _tell([les.source_version for les in mine])),
                    self._linje(f"{p}.utvalg",
                                _tell([les.utvalg for les in mine])),
                ]
            if forkastet:
                ut.append(self._linje(f"{p}.forkastet",
                                      f"{len(forkastet)} dato(er)"))
                for grunn in sorted({f.grunn for f in forkastet}):
                    treff = sorted(f.observed_at for f in forkastet
                                   if f.grunn == grunn)
                    ut.append(f"    {len(treff):>4}  {grunn}: "
                              f"{', '.join(treff)}")
        return ut

    def _fillista(self) -> list[str]:
        """Hver leste fil, med løpenummer OG published_at.

        Det er denne delen punkt 2 handler om. En linje per fil er mye
        for `lusetall` (400 uker), og det er riktig pris: uten den kan
        ingen si hvilken påstand om en gitt måned tallet hviler på.
        """
        if not self._lesinger:
            return []
        ut = ["", "# Hver leste snapshot-fil, i lesningsrekkefølge.",
              "# kilde  dato  .løpenummer  utgitt=<published_at>  "
              "hentet=<fetched_at>  rader"]
        for les in self._lesinger:
            ut.append(
                f"  {les.kilde}  {les.observed_at}  .{les.versjon}  "
                f"utgitt={les.published_at}  hentet={les.fetched_at}  "
                f"rader={les.n_rader}")
        return ut

    @staticmethod
    def _linje(nokkel: str, verdi: object) -> str:
        return f"{nokkel:<40} {verdi}"

    @staticmethod
    def _relativ(sti: Path) -> str:
        try:
            return str(Path(sti).resolve().relative_to(ROT))
        except ValueError:
            return str(sti)

    def skriv(self) -> Path:
        self.sti.parent.mkdir(parents=True, exist_ok=True)
        self.sti.write_text("\n".join(self.linjer()) + "\n", encoding="utf-8")
        return self.sti
