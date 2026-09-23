/* Kystloggen — det lille som er JavaScript.
 *
 * ## REGELEN: alt her er en FORBEDRING av noe som virker uten
 *
 * Nettstedets første regel er at tallene skal stå i kildekoden. En side
 * der en verdi tegnes av et skript kan ikke siteres, kan ikke arkiveres
 * av Wayback, og kan ikke leses av noen som har slått det av. Se
 * `base.html.j2` og docs/VISNING.md.
 *
 * Denne fila bryter ikke regelen: den LEGGER IKKE TIL ÉN VERDI. Tre
 * ting, og hver av dem har en fungerende variant uten skript:
 *
 *   kopierknappen   uten: teksten er markerbar og kan kopieres med
 *                   musa eller tastaturet. Knappen er `hidden` i
 *                   markupen og vises først her — en knapp som ikke
 *                   gjør noe er verre enn ingen knapp.
 *   områdesøket     uten: hele tabellen vises, og skjemaet sender til
 *                   en side som svarer.
 *   endringsfilter  uten: hver type er sin egen STI, bygget som en
 *                   ekte side. Med skript slipper man rundturen.
 *
 * ## Ingen avhengigheter, ingen bygging, ingen modulsyntaks
 *
 * Én fil, lastet med `defer`. Ingen npm, ingen bundler, ingen
 * transpilering — samme begrunnelse som pinningen av
 * `requirements.txt`: dette skal virke uten tilsyn i ti år, og et
 * byggesteg er et sted ting kan råtne.
 *
 * ## Feil her skal ikke ta ned siden
 *
 * Hver del står i sin egen `try`. Et unntak i filteret skal ikke gjøre
 * kopierknappen død — og ingen av dem skal gjøre innholdet
 * utilgjengelig, fordi innholdet er der uten dem.
 */
(function () {
  "use strict";

  /* ---------------------------------------------------------- kopier
   *
   * Knappen står `hidden` i markupen og slås på her. Teksten hentes fra
   * elementet den peker på, så den kan ikke bli uenig med det som står
   * på siden.
   */
  function kopier() {
    var knapper = document.querySelectorAll("[data-kopier]");
    if (!knapper.length || !navigator.clipboard) return;

    Array.prototype.forEach.call(knapper, function (knapp) {
      var mal = document.getElementById(knapp.getAttribute("data-kopier"));
      if (!mal) return;
      knapp.hidden = false;
      knapp.addEventListener("click", function () {
        navigator.clipboard.writeText(mal.textContent.trim().replace(/\s+/g, " "))
          .then(function () {
            var fra = knapp.textContent;
            knapp.textContent = "Kopiert";
            /* TILBAKEMELDINGEN MELDES OGSÅ TIL SKJERMLESERE. En knapp
               som bare bytter tekst sier ingenting til den som ikke ser
               den. `aria-live` på knappen selv holder, fordi teksten
               ER tilbakemeldingen. */
            knapp.setAttribute("aria-live", "polite");
            setTimeout(function () { knapp.textContent = fra; }, 2400);
          })
          .catch(function () {
            /* Utklippstavla kan være nektet. Da sier knappen det,
               framfor å se ut som om den virket. */
            knapp.textContent = "Kunne ikke kopiere — merk teksten";
          });
      });
    });
  }

  /* ------------------------------------------------------ områdesøk
   *
   * Filtrerer radene i en tabell på det som skrives. Uten skript sendes
   * skjemaet, og siden det går til viser hele lista.
   *
   * SØKET LESER `data-sok`, som generatoren setter — ikke celletekst.
   * En rad som ble funnet på grunn av et kolonnenavn eller en dato i
   * en annen kolonne, ville vært et treff leseren ikke kan forklare.
   */
  function omraadesok() {
    var felt = document.querySelector("[data-filtrerer]");
    if (!felt) return;
    var tabell = document.getElementById(felt.getAttribute("data-filtrerer"));
    if (!tabell) return;
    var teller = document.querySelector("[data-teller]");
    var rader = tabell.querySelectorAll("tbody tr");

    /* Skjemaet sender ikke lenger: vi svarer på stedet. Knappen blir
       overflødig og skjules, slik at den ikke lover en rundtur som ikke
       skjer. */
    var skjema = felt.closest("form");
    if (skjema) {
      skjema.addEventListener("submit", function (e) { e.preventDefault(); });
      var knapp = skjema.querySelector("button[type=submit]");
      if (knapp) knapp.hidden = true;
    }

    function filtrer() {
      var q = felt.value.trim().toLowerCase();
      var synlige = 0;
      Array.prototype.forEach.call(rader, function (rad) {
        var treff = !q || (rad.getAttribute("data-sok") || "").indexOf(q) >= 0;
        rad.hidden = !treff;
        if (treff) synlige++;
      });
      if (teller) {
        teller.textContent = q
          ? "Viser " + synlige + " av " + rader.length
          : teller.getAttribute("data-teller");
      }
    }
    felt.addEventListener("input", filtrer);
    filtrer();
  }

  /* -------------------------------------------------- endringsfilter
   *
   * Avkrysningsboksene på endringssiden. Uten skript er hver boks en
   * LENKE til `/endringer/<uke>/<type>/`, som er en ekte side bygget
   * ved bygging. Med skript filtreres tabellen på stedet, og flere
   * typer kan velges samtidig — det er forbedringen.
   */
  function endringsfilter() {
    var rot = document.querySelector("[data-filter-for]");
    if (!rot) return;
    var tabell = document.getElementById(rot.getAttribute("data-filter-for"));
    if (!tabell) return;
    var bokser = rot.querySelectorAll("input[type=checkbox][name=type]");
    if (!bokser.length) return;
    var teller = tabell.querySelector("caption [data-teller]");
    var rader = tabell.querySelectorAll("tbody tr[data-type]");
    var tomrad = tabell.querySelector("tbody tr[data-tom]");

    rot.hidden = false;

    /* LENKELISTA SKJULES når skjemaet tar over. Begge er filteret —
       den ene virker uten skript, den andre med — og to filtre på
       skjermen samtidig er ett for mye. Rekkefølgen er viktig: lista
       skjules FØRST når skjemaet er slått på, aldri før. */
    var utenJs = document.querySelectorAll("[data-uten-js]");
    Array.prototype.forEach.call(utenJs, function (el) { el.hidden = true; });

    function filtrer() {
      var valgt = [];
      Array.prototype.forEach.call(bokser, function (b) {
        if (b.checked) valgt.push(b.value);
      });
      var synlige = 0;
      Array.prototype.forEach.call(rader, function (rad) {
        var treff = !valgt.length
          || valgt.indexOf(rad.getAttribute("data-type")) >= 0;
        rad.hidden = !treff;
        if (treff) synlige++;
      });
      if (tomrad) tomrad.hidden = synlige > 0;
      if (teller) {
        teller.textContent = "Viser " + synlige + " av " + rader.length;
      }
    }
    Array.prototype.forEach.call(bokser, function (b) {
      b.addEventListener("change", filtrer);
    });
    filtrer();
  }

  /* --------------------------------------------- selskapsdata-delen
   *
   * `<details open>` i markupen, lukket her. Rekkefølgen er hele
   * poenget: uten skript står delen ÅPEN, og alt innholdet er der.
   * En del som må åpnes av et skript er en del som ikke finnes for
   * den som har skript av — det er samme regel som knappen som er
   * `hidden` til den virker, speilvendt.
   */
  function selskapsdel() {
    var deler = document.querySelectorAll("details[data-lukk-ved-js]");
    Array.prototype.forEach.call(deler, function (d) { d.open = false; });
  }

  [kopier, omraadesok, endringsfilter, selskapsdel].forEach(function (del) {
    try {
      del();
    } catch (e) {
      /* En knekt forbedring skal koste én forbedring, ikke siden.
         Samme regel som `runner.run_all()` og `skriv_alle()`. */
      if (window.console && console.warn) console.warn("Kystloggen:", e);
    }
  });
})();
