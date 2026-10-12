---
name: overlevering
description: Komprimer økta til en overlevering på maks 30 linjer i /tmp, slik at neste økt kan fortsette uten samtalen. Bruk når Heine ber om overlevering, når økta nærmer seg slutten, eller før en lang pause i arbeidet.
---

# Overlevering

Skriv `/tmp/overlevering-<ÅÅÅÅ-MM-DD>-<emne>.md`, aldri i git. Maks 30
linjer, i tre deler:

1. **Gjort.** Ett punkt per oppgave: hva som endret seg og commit-hash.
   Si om den er pushet (`git log origin/main..main` i begge repoene;
   CLAUDE.md regel 7).
2. **Målt.** Tall med merke (MÅLT / MÅLBAR / UBELAGT) og hvor de står:
   dokument og linje, eller kropp og sha256. Det som ikke er verifisert,
   sies uttrykkelig (regel 4).
3. **Står igjen.** Det som ikke er gjort, hva Heine må avgjøre, og den
   første kommandoen neste økt bør kjøre. Ugjorte ting som hører til en
   annen oppgave, nevnes men løses ikke.

Gjenta ikke det som står i commit-meldingene eller i `docs/`; pek dit.
Ingen navn på personer eller personformforetak (regel 3). Oppgi stien
til fila til slutt.
