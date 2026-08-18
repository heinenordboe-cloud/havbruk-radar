---
dato: 2026-08-16
tittel: Kilder er plugins, kjernen kjenner dem ikke
status: gjeldende
commit: 
---

# Kilder er plugins, kjernen kjenner dem ikke

**Bestemt:** `core/` skanner `sources/` og finner kilder dynamisk. Ny
kilde = én ny fil, ingen endring i kjernen.

**Hvorfor:** Kilder og kjerne har helt ulik levetid. Kilder brekker når
en etat bytter format; kjernen brekker bare når man selv velger det.

**Testen på at det holder:** Kan en kilde legges til uten å åpne `core/`?
Blir svaret nei, mangler kontrakten i `contract.py` noe — det er ikke en
grunn til å gjøre unntak.
