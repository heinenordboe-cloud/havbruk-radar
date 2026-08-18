---
dato: 2026-08-16
tittel: Alarmen holder seg rød så lenge en kilde er nede
status: gjeldende
commit: 40a32ee
---

# Alarmen holder seg rød så lenge en kilde er nede

**Bestemt:** `run.py` avslutter med feilkode hver uke en kilde som har
fungert før er nede, ikke bare den uka den brekker. En kilde som aldri
har levert varsler ikke.

**Hvorfor:** Den gamle logikken varslet kun på overgangen fungerte→feiler.
Verifisert: uke 2 gav rød jobb, uke 3 gav grønn mens kilden fortsatt var
død. Docstringen i `health.py` beskrev denne feilmodusen som den farligste
i systemet, og koden gjenskapte den forskjøvet én uke. Mister du den ene
e-posten, er alt grønt igjen mens datatapet fortsetter.

**Prisen:** E-post hver mandag til det er fikset. Alternativet — demping
etter noen uker — gjeninnfører stillheten, og stillhet er hele feilen.
Løsningen på støyen er å fikse kilden eller deaktivere den bevisst.

**Ville snudd det:** At alarmtretthet i praksis fører til at e-postene
ignoreres. Da er problemet at varselet ikke er handlingsutløsende nok,
ikke at det kommer for ofte.
