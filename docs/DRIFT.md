# Drift, sikring og lagring

## Hva som faktisk kan ødelegge prosjektet

Rangert etter sannsynlighet, ikke etter hvor dramatisk det høres ut.

**1. Innsamlingen stopper uten at du merker det.** Klart størst risiko.
GitHub deaktiverer planlagte workflows etter 60 dager uten commit-aktivitet.
Så lenge kjøringen lykkes hver mandag, nullstilles klokka automatisk. Men
feiler den stille i to måneder, slås den av — og *da* har du et hull i
historikken som ikke kan fylles.

Motmiddel: workflowen feiler høyt (`exit 1`), og GitHub sender e-post ved
feilet kjøring. Sjekk at varsling er på:
Settings → Notifications → Actions → "Send notifications for failed workflows only".

**2. Kontoen din forsvinner.** Lav sannsynlighet, total konsekvens.
Motmiddel er speiling — se under.

**3. En kilde bytter format.** Høy sannsynlighet, lav konsekvens.
Feilisoleringen tar den. Du mister én kilde i noen uker, ikke historikken.

## Speiling

Git er distribuert: hver klon er en komplett kopi med full historikk.
Det er backup-strategien, og den er allerede halvferdig.

Sett opp ett speil utenfor GitHub — Codeberg og GitLab er begge gratis:

    1. Lag tomt repo hos Codeberg/GitLab.
    2. Lag et access token med skriverettighet der.
    3. GitHub → Settings → Secrets → Actions → New secret
       Navn:  MIRROR_URL
       Verdi: https://<bruker>:<token>@codeberg.org/<bruker>/havbruk-radar.git

Workflowen speiler da etter hver kjøring. Er hemmeligheten ikke satt,
hoppes steget over uten å feile.

I tillegg: `git clone` til egen maskin en gang i kvartalet. Det tar tretti
sekunder og gir deg en tredje kopi på en helt annen infrastruktur.

## Størrelse over tid

Parquet komprimerer gjentatte tekststrenger hardt. Med Enhetsregisteret på
seks NACE-koder ligger et ukentlig snapshot på anslagsvis 0,2–0,5 MB.
Det blir i størrelsesorden 10–25 MB i året.

GitHub anbefaler å holde repoer under 1 GB. Du har flere tiår før det er
et tema, og legger du til fem kilder til er du fortsatt langt unna.

Ikke bruk Git LFS. Det har kvote, koster penger over den, og gjør hver
klon dyrere. Vanlige filer er riktig her.

## Hemmeligheter

Nøkler skal aldri i `config.yml`. Config-laget bytter ut `${NAVN}` med
miljøvariabel ved innlasting, og workflowen mater dem inn fra GitHub Secrets:

    kilder:
      barentswatch:
        api_key: "${BARENTSWATCH_KEY}"

Lokalt legger du dem i `.env` — som allerede er i `.gitignore`.

## Offentlig eller privat repo

Anbefaling: privat nå, offentlig når koden er presentabel. Commit-historikken
følger med når du flipper bryteren, så du taper ingenting på å vente.

Én ting å være obs på før du gjør det offentlig: hvis du senere henter
roller fra Enhetsregisteret, får du navn og fødselsdato på privatpersoner
inn i repoet. Et offentlig repo blir da et personregister du selv er
behandlingsansvarlig for. Selskapsdata er uproblematisk — persondata er
en annen samtale. Ta det valget bevisst.

## Vekk fra GitHub Actions?

Ikke før du har et problem. En VPS koster penger, må vedlikeholdes, og
gir deg ingenting du ikke har. Det eneste som virkelig tvinger fram et
bytte er kjøretid over seks timer, eller kilder som blokkerer GitHubs
IP-adresser. Ingen av delene er aktuelt nå.
