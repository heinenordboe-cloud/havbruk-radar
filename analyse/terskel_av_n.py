"""R²-terskelen som funksjon av n — regnet, ikke vurdert.

Terskelen i `docs/beslutninger/2026-08-31-hypotesen-omdefineres.md` er
ikke et skjønn som må tas på nytt hver gang celletallet flytter seg. Den
er en FUNKSJON av n alene, og metoden er skrevet ned én gang:

    finn den R² der nedre 95 %-kant av Fisher-z-intervallet lander på
    den fulle Stien-proxyens rho² = 0,494, og rund OPP til nærmeste 0,01

Denne fila er den funksjonen. Den finnes for at tabellen i notatet skal
kunne etterprøves av en som ikke stoler på den, og for at neste gang n
endrer seg skal svaret være et kall og ikke en vurdering.

## Hvorfor tabellen er skrevet FØR n er kjent

Samme grunn som stoppregelen selv. En terskel valgt etter at tallet er
sett, er ikke en terskel — og en terskel som må REGNES UT etter at
tallet er sett, er en invitasjon til å regne den ut på en annen måte.
Hele intervallet 20..60 ligger derfor i notatet, og kjøringen slår opp
den raden som svarer til sitt eget n.

## z = 1,96, ikke 1,959964

Notatets tre eksisterende tall (n=39 -> 0,6948, n=58 -> 0,662,
n=60 -> 0,6592) reproduseres på 1,96 og IKKE på den eksakte
z_{0,975} = 1,959963985, som gir 0,6617 og 0,6591. Avviket er 0,0003 og
uten praktisk betydning — men konstanten er et VALG som avgjør et tall,
og da skal den stå skrevet framfor å bli gjettet av den neste. Vi bruker
notatets egen.

## Én rad som ikke er ren avrunding: n = 60

`ceil(0,6592 * 100) / 100` er 0,66, ikke 0,67. Notatet setter likevel
0,67 i hele båndet 55-60, og grunnen står der: disken holder 58
ROC-celler, ikke 60, og ved n = 58 gir 0,66 en nedre kant på 0,4918 —
så vidt UNDER referansen 0,494. Grensen skal ikke avhenge av en
beslutning som ikke er tatt.

`avrundet()` gjør den rene avrundingen og lyver ikke om den. Unntaket
ligger i `GRENSE`, som er tabellen slik den er ført i notatet, med
avviket merket. De to skal kunne sammenlignes.
"""

import math

# Full Stien-proxy, rho² mot kategorirang, målt 26.08.2026. Referansen
# terskelen må klareres MOT — se notatet om hvorfor det er dette
# punktet og ikke lusetall alene (0,260) eller PO-nummer alene (0,261).
REFERANSE = 0.494

# Notatets egen konstant. Se modulens docstring.
Z = 1.96


def nedre_kant(r2: float, n: int) -> float:
    """Nedre 95 %-kant for R², via Fisher-z på r = sqrt(R²)."""
    r = math.sqrt(r2)
    return math.tanh(math.atanh(r) - Z / math.sqrt(n - 3)) ** 2


def ovre_kant(r2: float, n: int) -> float:
    r = math.sqrt(r2)
    return math.tanh(math.atanh(r) + Z / math.sqrt(n - 3)) ** 2


def eksakt(n: int) -> float:
    """Den R² hvis nedre 95 %-kant treffer REFERANSE nøyaktig."""
    z_ref = math.atanh(math.sqrt(REFERANSE))
    return math.tanh(z_ref + Z / math.sqrt(n - 3)) ** 2


def avrundet(n: int) -> float:
    """`eksakt(n)` rundet OPP til nærmeste 0,01.

    Opp og ikke nærmeste: avrunding NEDOVER ville flyttet nedre kant
    under referansen, og da klarerer terskelen ikke det den ble valgt
    for å klarere.
    """
    return math.ceil(round(eksakt(n), 10) * 100) / 100


# Tabellen slik den er ført i notatet. Nøkkelen er NEDRE n i båndet.
#
# Merk 55: båndet 55-60 står på 0,67 selv om den rene avrundingen gir
# 0,66 ved n = 60. Se modulens docstring — det er notatets egen,
# skrevne begrunnelse, ikke en glipp her.
GRENSE: dict[int, float] = {
    20: 0.77, 25: 0.74, 30: 0.72, 35: 0.71,
    40: 0.70, 45: 0.69, 50: 0.68, 55: 0.67,
}

# Under dette er utvalget for lite til at regelen betyr noe. Da skal det
# SKRIVES at terskelen ikke gjelder, ikke ekstrapoleres nedover.
MINSTE_N = 20


def grense_for(n: int) -> float:
    """Terskelen for et gitt n, slått opp i notatets tabell.

    Kaster for n < MINSTE_N framfor å ekstrapolere. En terskel utenfor
    det området tabellen dekker er ikke pre-registrert, og en
    pre-registrert grense som regnes ut etterpå er ingen grense.
    """
    if n < MINSTE_N:
        raise ValueError(
            f"n = {n} er under {MINSTE_N}. Tabellen i "
            f"2026-08-31-hypotesen-omdefineres.md dekker 20-60, og under "
            f"20 skal terskelen IKKE ekstrapoleres — da er utvalget for "
            f"lite til at regelen betyr noe, og det skal skrives rett ut."
        )
    band = max(b for b in GRENSE if b <= n)
    return GRENSE[band]


def _hovedprogram() -> None:
    print("== reproduksjon av notatets tre tall ==")
    ok = True
    # Sammenligningen skjer på DEN PRESISJONEN notatet oppgir. n=58 står
    # med tre desimaler (0,662) og de to andre med fire; en fast toleranse
    # ville felt 0,6617 for å ikke være 0,66200. Det er ikke et avvik i
    # tallet, bare i hvor mange sifre som er skrevet ned.
    for n, ventet, desimaler in ((39, 0.6948, 4), (58, 0.662, 3), (60, 0.6592, 4)):
        fikk = eksakt(n)
        traff = round(fikk, desimaler) == ventet
        ok = ok and traff
        print(f"   n={n:3d}  eksakt {fikk:.4f}  ~ {round(fikk, desimaler)}  "
              f"notatet {ventet}  {'OK' if traff else 'AVVIK'}")
    print(f"   -> {'tabellen står' if ok else 'TABELLEN STÅR IKKE'}")

    print("\n== tabellen ==")
    print("     n   eksakt   grense   95 % CI for R² ved grensen")
    for n in (20, 25, 30, 35, 40, 45, 50, 55, 58, 60):
        g = grense_for(n)
        print(f"   {n:3d}   {eksakt(n):.4f}    {g:.2f}     "
              f"[{nedre_kant(g, n):.3f}, {ovre_kant(g, n):.3f}]"
              + ("   (ren avrunding: 0,66)" if avrundet(n) != g else ""))


if __name__ == "__main__":
    _hovedprogram()
