"""Sjøtemperatur (BarentsWatch fiskehelse) — målt temperatur per lokalitet
per uke.

Verifisert mot levende tjeneste 24.08.2026, se docs/KILDE-SJOTEMPERATUR.md.
Alt i denne docstringen er MÅLT, ikke antatt eller lest ut av
dokumentasjonen.

Endepunkt:

    {base}/v1/geodata/download/fishhealth
        ?reporttype=Lice&filetype=csv
        &fromyear={år}&fromweek={uke}&toyear={år}&toweek={uke}

## Hvorfor eksportendepunktet og ikke seatemperature/{år}

Det opplagte endepunktet er
`/v1/geodata/fishhealth/locality/{localityNo}/seatemperature/{year}`. Det
virker, og det gir ukentlige verdier. Men aksen er FEIL vei: én lokalitet
per år per kall, altså 1777 x 15 = ~26 000 kall for full historikk.

Eksporten gir alle lokaliteter for én uke i ett kall — samme akse som
`lusetall`, samme akse som `backfill.py`, og 730 kall for det samme.

De to er krysset mot hverandre på 12 lokaliteter i uke 30/2018, og ga
samme verdi til to desimaler i alle tolv (14.07, 16.7, 13.19, 11.0, 9.5,
13.6, 11.0, 13.4, 15.6, 15.43, 11.5, 15.46). Det er ikke to kilder til
det samme tallet; det er to visninger av den samme innrapporterte
verdien.

Prisen er at kolonnenavnene er norske og laget for et regneark, ikke for
et API. Derfor sjekker `_les_csv()` at kolonnene FINNES og kaster med
navns nevnelse hvis de er borte — en stille omdøping ville ellers gitt
tomme uker som ser vellykkede ut. Rå-CSV-en arkiveres før parse, så en
omdøping er en re-parse og ikke tapt historikk.

## Hva kilden emitter, og hva den lar være

`sjotemperatur` og `temperatur_er_rapportert`. Ikke noe mer.

CSV-en bærer 20 kolonner, men de andre 18 eies allerede: `lusetall` eier
lusetallene og driftsflaggene, `akvakultur` eier navn, kommune, fylke,
breddegrad og produksjonsområde (`prodomraade_kode`/-`navn`/-`status`).
To kilder som skriver samme felt med hver sin skrivemåte legger igjen en
permanent falsk forskjell i dataene — samme grunn som at `lusetall` ikke
emitter `navn`.

`temperatur_er_rapportert` er ikke pynt. 0,0 grader er en LOVLIG målt
verdi og forekommer 675 ganger i historikken, de fleste i uke 51-52/2012.
Uten flagget blir «ingen rapport» til 0 grader i enhver analyse — og med
Stien-formelens (T + 4,28)^2 er forskjellen mellom «ukjent» og «0» et
faktisk tall på smittepresset. Samme skille som `lus_er_rapportert` og
`ansatte_er_registrert`.

## Om etterslepet, og om vakten som måler det

Temperaturen rapporteres i SAMME ukeskjema som lusetallet. Etterslepet
er derfor ikke likt lusetalls — det er det samme. `uker_etterslep: 4`.

Målt 24.08.2026, andel av ikke-brakklagte lokaliteter med temperatur:

    uke 29   99,8 %      uke 33   97,0 %
    uke 30   99,5 %      uke 34   30,8 %   <- inneværende uke
    uke 31   99,7 %      uke 35    1,3 %
    uke 32   98,5 %      uke 36    0,0 %

Vakten måler ANDELEN AV IKKE-BRAKKLAGTE SOM HAR EN TEMPERATUR. Det er
verdt å si hvorfor den ikke måler noe som ligner mer:

  - «andel av dem som telte lus som har temperatur» er 100,0 % i hver
    eneste uke fra 2012 til 2026, også i uke 35 der åtte lokaliteter har
    rapportert. Den ville aldri fyrt. Det er formen fra F10 — et mål som
    er riktig akkurat der de to tingene faller sammen, og stille ellers.
  - «andel av alle rader» er ~55 %, fordi to tredeler er brakklagte og
    ikke skal måle noe. Den ville fyrt hver uke.

Terskelen er MÅLT over alle 763 ferdige uker 2012-2026, ikke gjettet:

    laveste uke      76,8 %  (uke 21/2013)
    nest laveste     77,8 %  (uke 51/2012)
    tredje laveste   85,3 %  (uke 52/2012)
    p5               96,1 %
    median           99,4 %

`min_rapportert_andel: 0.80` gir 2 falske alarmer på 763 uker (0,26 %),
begge i oppstartsårene 2012-2013, og fanger den ferskeste uka med 49
prosentpoengs margin (30,8 % mot 80 %). Tallet er ikke utledet av feilen
det skal fange: de ufullstendige ukene er målt for seg.

## Om uteliggere — de LAGRES, de fjernes ikke

Måleområdet er målt over 436 931 verdier 2012-2026:

    p1 2,70    median 8,69    p99 17,00    min -0,2    maks 196,18

98 % ligger mellom 2,7 og 17,0 grader, som er det man skal forvente på
oppdrettsdyp i norsk sjø. Men 56 verdier er over 25 grader (196,18,
173,44, 158,9 ...), alle i 2023-2026, og de er åpenbart tastefeil hos
innrapportør.

Kilden fjerner dem ikke og advarer ikke om dem. Begrunnelsen:

  - Å fjerne dem ville vært kilden som redigerer virkeligheten. Det som
    ble rapportert er det som lagres; `value` er tekst og typingen skjer
    i analysen. Det står i core/contract.py og gjelder her.
  - Å advare om dem ville gitt en advarsel i 6 % av ukene, og i 2025
    omtrent annenhver. En advarsel som fyrer hele tiden er en advarsel
    ingen leser, og da er den verre enn ingen.

Analysen skal filtrere på et intervall den velger selv. Dette avsnittet
er dokumentasjonen den trenger for å velge det.

## Om observed_at

Mandagen i ISO-uka dataene gjelder for, ikke dagen vi hentet dem —
utledet av `Uke`/`År` i CSV-en, altså av DATAENE og ikke av en klokke.
Samme regel og samme funksjon som `lusetall`, så de to kildenes filer
for samme uke får nøyaktig samme dato.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
from typing import Iterable

import httpx

from core.config import get
from core.contract import Observation, Source
from sources import _barentswatch, _http
from sources._barentswatch import PAUSE_S, TIDLIGSTE, mandag, uke_med_etterslep  # noqa: F401

# Kolonnenavnene i eksporten, verifisert 24.08.2026. Norske, med BOM,
# laget for et regneark. De er en kontrakt vi ikke eier — derfor står de
# her som navngitte konstanter og sjekkes eksplisitt, i stedet for å
# leses med .get() som gir None og en stille tom uke.
KOL_UKE = "Uke"
KOL_AAR = "År"
KOL_NR = "Lokalitetsnummer"
KOL_NAVN = "Lokalitetsnavn"
KOL_TEMP = "Sjøtemperatur"
KOL_BRAKK = "Trolig uten fisk"

PAAKREVDE = (KOL_UKE, KOL_AAR, KOL_NR, KOL_TEMP, KOL_BRAKK)

# Feltnavn er en kontrakt mot historikken. Døper du om et felt senere,
# leser diffen det som at det gamle forsvant og et nytt oppsto.
FELT_TEMP = "sjotemperatur"
FELT_RAPPORTERT = "temperatur_er_rapportert"


class Kolonnefeil(RuntimeError):
    """Eksporten kom, men ikke med kolonnene vi leser.

    Egen type fordi den betyr noe annet enn et nettverksavbrudd: den
    sier at formatet er endret, og at rå-arkivet må re-parses etterpå.
    """


def _les_csv(tekst: str) -> list[dict[str, str]]:
    """CSV-tekst til rader. Kaster hvis en kolonne vi leser mangler.

    Eksporten har BOM — verifisert, de tre første bytene er EF BB BF.
    `hent_uke()` dekoder med utf-8-sig og spiser den, men BOM-en fjernes
    OGSÅ her, og det er ikke belte og bukseseler: `parse()` kalles på
    tekst som like gjerne kommer fra en re-parse av rå-arkivet eller fra
    en fil noen har lastet ned for hånd, og da har ingen `hent_uke()`
    vært innom.

    Overlever BOM-en, heter den første kolonnen '\\ufeffUke'. Oppslaget
    på 'Uke' bommer da på nøyaktig én kolonne — og fordi det er kolonnen
    som bærer UKA, ville uka blitt udaterbar mens de nitten andre
    kolonnene så helt friske ut.
    """
    leser = csv.DictReader(io.StringIO(tekst.lstrip("﻿")))
    rader = list(leser)
    if not rader:
        return []

    mangler = [k for k in PAAKREVDE if k not in rader[0]]
    if mangler:
        raise Kolonnefeil(
            f"Eksporten mangler kolonnen(e) {', '.join(mangler)}. "
            f"Fikk: {', '.join(rader[0])}. Formatet er endret — rå-CSV-en "
            f"er arkivert, så dette er en re-parse og ikke tapt historikk."
        )
    return rader


def _tall(tekst: str | None) -> float | None:
    """Tom celle -> None. En verdi som ikke er et tall -> None.

    Ikke exception: en enkelt ulesbar celle skal koste den ene raden, ikke
    uka. Raden får da `temperatur_er_rapportert = False`, som er sant —
    vi har ingen temperatur for den.
    """
    if tekst is None or not tekst.strip():
        return None
    try:
        return float(tekst.strip().replace(",", "."))
    except ValueError:
        return None


def rapportert_andel(rader: list[dict[str, str]]) -> tuple[int, int, float]:
    """(ikke_brakklagte, med_temperatur, andel).

    Nevneren er ikke-brakklagte lokaliteter. Se modulens docstring for
    hvorfor det er den ENESTE nevneren som både kan fyre og kan tie.
    """
    aktive = [r for r in rader if r.get(KOL_BRAKK) != "Ja"]
    med = [r for r in aktive if _tall(r.get(KOL_TEMP)) is not None]
    andel = len(med) / len(aktive) if aktive else 0.0
    return len(aktive), len(med), andel


def _vurder_rapportering(rader: list[dict[str, str]], aar: int, uke: int) -> list[str]:
    """Advarsel hvis uka ser ufullstendig ut. Ikke exception: snapshotet
    skal fortsatt skrives, men jobben skal bli rød så uka kan hentes på
    nytt senere."""
    grense = float(get("kilder.sjotemperatur.min_rapportert_andel", 0.80))
    aktive, med, andel = rapportert_andel(rader)
    if aktive and andel < grense:
        return [
            f"sjotemperatur uke {uke}/{aar}: bare {andel:.1%} av {aktive} "
            f"ikke-brakklagte lokaliteter har en temperatur (grense "
            f"{grense:.0%}). Uka er trolig for fersk — hent den på nytt "
            f"senere."
        ]
    return []


class Sjotemperatur(Source):
    name = "sjotemperatur"
    entity_type = "lokalitet"

    # Temperaturen kommer i det samme ukeskjemaet som lustallet, altså én
    # ny verdi per lokalitet per uke. Uke er den frekvensen kilden
    # FAKTISK endrer seg med, ikke en frekvens valgt for å ligne på
    # naboen: en månedlig henting ville mistet tre av fire uker
    # permanent, siden snapshots er append-only og en uke ikke kan
    # hentes tilbake som en uke hvis den aldri ble skrevet.
    min_dager_mellom = 7

    # Backfill-pause, høyere enn `_barentswatch.PAUSE_S` (0,5 s). Eksporten
    # er 128 kB per ukekall mot lusetalls få kilobyte, og en grense ingen
    # har dokumentert kan like gjerne gå på BYTES som på antall kall:
    # 239 uker på åtte minutter er ~30 kall/min og ~30 MB.
    #
    # Tallet er forsikring, ikke en rettelse — årsaken til 401-blokka
    # 24.08.2026 er ikke fastslått, og skal ikke gjettes. Det som ER målt:
    # kallet tar 0,8 s, resten av uka (diff, skriving, changelog) ~1,4 s.
    # 2,0 s pause gir ~20 kall/min og tar hele historikken fra ~27 til
    # ~48 minutter. Én gang, for en kilde vi skal bruke i to år.
    pause_s = 2.0

    def __init__(self) -> None:
        self.enabled = bool(get("kilder.sjotemperatur.aktiv", False))
        self._tilgang = _barentswatch.Tilgang(self.name)

    # ---- henting -------------------------------------------------------

    def hent_uke(self, aar: int, uke: int,
                 client: httpx.Client | None = None) -> str:
        """Rå CSV-tekst for én uke. Brukes av både fetch() og backfill.

        Returnerer TEKST og ikke ferdig tolkede rader, fordi kjernen
        arkiverer det fetch() returnerer og det som arkiveres skal være
        det tjenesten faktisk sendte. `core/raw.py` lagrer en str som
        `.txt.gz`.
        """
        # Utvalget settes HER og ikke i fetch(), fordi hent_uke() er det
        # ENE stedet begge veier inn i kilden går gjennom: ukejobben via
        # fetch(), historikken via backfill.py. Sto det i fetch(), fikk
        # backfillede rader tomt utvalg — og et tomt utvalg leses «vet
        # ikke», ikke «ingen filtrering». 389 206 rader ble skrevet slik
        # 24.08.2026 før det ble oppdaget.
        #
        # `reporttype` er ikke en innstilling som bare påvirker formatet:
        # eksporten er delt i tre rapporter, og hvilken vi ber om avgjør
        # HVILKE lokaliteter som kommer med. Ber noen senere også om
        # `Disease`, kommer det inn lokaliteter som er nye i utvalget og
        # ikke i verden — nøyaktig hendelsen merkingen finnes for.
        # `filetype` står ikke her: den endrer ikke hvilke entiteter vi
        # får, bare hvordan de er pakket.
        self.utvalg = {"rapporttype": ["Lice"]}

        base = self._tilgang.base_url()
        egen = client is None
        c = client or self._tilgang.klient(accept="text/csv")
        try:
            svar = _http.get(
                c, f"{base}/v1/geodata/download/fishhealth",
                hva=f"uke {uke}/{aar}",
                params={
                    "reporttype": "Lice",
                    "filetype": "csv",
                    "fromyear": aar, "fromweek": uke,
                    "toyear": aar, "toweek": uke,
                },
            )
            # Eksplisitt dekoding, ikke svar.text: httpx gjetter tegnsett
            # fra headeren, og en header uten charset ville gitt latin-1
            # på et innhold som er utf-8 med BOM. Da blir «Sjøtemperatur»
            # til «SjÃ¸temperatur» og kolonnesjekken feller uka.
            return svar.content.decode("utf-8-sig")
        finally:
            if egen:
                c.close()

    def _uke_naa(self, kjoredato: str) -> tuple[int, int]:
        """Uka kilden henter når vi kjører `kjoredato`. Ett sted, ikke to.

        Både fetch() og gjelder_for() må svare på det samme spørsmålet, og
        begge får datoen inn. Ingen klokkeoppslag her — se Source.fetch og
        F7.
        """
        uker = int(get("kilder.sjotemperatur.uker_etterslep", 4))
        return uke_med_etterslep(dt.date.fromisoformat(kjoredato), uker)

    def gjelder_for(self, kjoredato: str) -> str:
        """Mandagen i uka vi henter — ikke dagen vi henter den."""
        return mandag(*self._uke_naa(kjoredato))

    def fetch(self, kjoredato: str) -> str:
        aar, uke = self._uke_naa(kjoredato)
        rå = self.hent_uke(aar, uke)

        # Vurderingen får ALDRI felle fetch(). Kjernen arkiverer det
        # fetch() RETURNERER (`runner.run_all`: fetch, så arkiver, så
        # parse), så en exception her betyr at rå-CSV-en aldri når disk —
        # og da er en omdøpt kolonne oppdaget om et halvt år permanent
        # datatap i stedet for en re-parse. Det er hele begrunnelsen for
        # rå-arkivet, og den holder bare hvis fetch() kommer helskinnet
        # tilbake.
        #
        # Kolonnefeilen forsvinner ikke: `parse()` kaller `_les_csv()` på
        # nytt og kaster der. Da er arkiveringen unnagjort, runner fanger
        # feilen, kilden blir rød — og uka ligger på disk.
        try:
            self.advarsler = _vurder_rapportering(_les_csv(rå), aar, uke)
        except Kolonnefeil as e:
            self.advarsler = [
                f"sjotemperatur uke {uke}/{aar}: klarte ikke vurdere "
                f"rapporteringsgraden. {e}"
            ]
        return rå

    # ---- tolkning ------------------------------------------------------

    def parse(self, raw: str, observed_at: str) -> Iterable[Observation]:
        """observed_at kommer fra kjernen, men uka står i dataene.

        Datoen utledes av `Uke`/`År` på radene og ikke av kjøredatoen, av
        samme grunn som i lusetall: filnavnet skal si det samme som
        innholdet (F6).

        En CSV med flere uker i seg KASTER. Et snapshot bærer én dato, så
        to uker i samme fil ville datert den ene uka feil — stille, og
        permanent, siden filene er append-only.
        """
        rader = _les_csv(raw)
        if not rader:
            return

        uker = {(r[KOL_AAR], r[KOL_UKE]) for r in rader}
        if len(uker) > 1:
            raise ValueError(
                f"Eksporten inneholder {len(uker)} ulike uker "
                f"({sorted(uker)[:5]}...). Et snapshot bærer én dato, så "
                f"dette ville datert alle radene etter én av dem."
            )

        aar_tekst, uke_tekst = uker.pop()
        try:
            gjelder = mandag(int(aar_tekst), int(uke_tekst))
        except (TypeError, ValueError):
            gjelder = observed_at

        for rad in rader:
            nr = (rad.get(KOL_NR) or "").strip()
            if not nr:
                continue
            navn = (rad.get(KOL_NAVN) or "").strip()
            temp = _tall(rad.get(KOL_TEMP))

            # Flagget først, og for HVER rad. Det er det som gjør et hull
            # lesbart som et hull i stedet for som null grader.
            yield Observation(
                entity_id=nr,
                entity_type=self.entity_type,
                entity_name=navn,
                field=FELT_RAPPORTERT,
                value=str(temp is not None),
                source=self.name,
                observed_at=gjelder,
            )

            if temp is None:
                continue

            yield Observation(
                entity_id=nr,
                entity_type=self.entity_type,
                entity_name=navn,
                field=FELT_TEMP,
                value=str(temp),
                source=self.name,
                observed_at=gjelder,
            )
