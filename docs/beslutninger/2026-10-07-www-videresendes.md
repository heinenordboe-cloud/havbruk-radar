---
dato: 2026-10-07
tittel: www.kystloggen.no videresendes med 301 til kystloggen.no, med samme sti
status: besluttet 07.10.2026
commit: (denne)
---

# www videresendes til apex

Avgjør punkt 11 i den andre lista i `docs/APNE-SPORSMAL.md` («www
videresender ikke — to verter svarer 200 med samme side»), som er
fjernet derfra i samme commit.

## Hva som ble bestemt

- `www.kystloggen.no` svarer med **301** til `kystloggen.no` og **samme
  sti**. Satt av Heine 07.10.2026 som en Redirect Rule hos Cloudflare.
- `kystloggen.no` er den ene verten. Det er den `<link rel="canonical">`
  og `og:url` har oppgitt hele tiden; nå svarer tjeneren det samme.
- Røyktesten i `publiser.yml` krever det etter hver publisering
  (`royktest.py`, `sjekk_www()`): forsiden og den første lokaliteten fra
  `www`, uten å følge videresendingen — status 301 og `Location` lik
  adressen på apex. 302, 308, 200 eller en videresending som mister
  stien er rødt.

## Spørsmålet slik det sto

MÅLT 24.09.2026: begge vertene svarte `HTTP/2 200` med samme side —
149 543 byte, identiske bortsett fra Cloudflares e-postobfuskering, som
får en ny nøkkel per forespørsel. Siden navnga én vert mens tjeneren
svarte på to. Spørsmålet var om kanonisk-taggen var nok, eller om `www`
skulle videresendes i kanten.

## Målt 07.10.2026

    curl https://www.kystloggen.no/                     301  https://kystloggen.no/
    curl https://www.kystloggen.no/lokalitet/10029/?a=1  301  https://kystloggen.no/lokalitet/10029/?a=1
    curl http://www.kystloggen.no/om/                   301  https://www.kystloggen.no/om/

Spørrestrengen følger med. Over `http://` er det **to hopp**: først til
`https://www` («Always Use HTTPS»), så til apex (regelen). Røyktesten
måler bare `https://`.

`royktest.py` mot de levende vertene: begge stiene gir 301 til riktig
adresse; apex brukt som www-vert gir «status 200, ikke 301».

## Ikke målt

- Hva søkemotorer og delingsforhåndsvisninger gjorde med de to vertene
  før 07.10.2026, eller gjør nå.
- Regelen står i Cloudflare-kontoen, ikke i noe repo. Røyktesten er det
  eneste som sier fra om den forsvinner — og bare når noen publiserer.

## Hvorfor

[Heine skriver.]

## Hva som ville snudd det

[Heine skriver.]
