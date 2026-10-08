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
 *   verktøytipset   uten: nettleseren viser kartets og grafens
 *                   `<title>` selv, og hver verdi står i tabellen under.
 *
 * FILTERET PÅ ENDRINGSSIDEN ER BORTE fra 24.09.2026. Det var en rad
 * avkrysningsbokser skriptet slo på, og som da SKJULTE brikkene under.
 * Brikkene er lenker til sider som er bygget, og de virker overalt; to
 * filtre for det samme er ett for mye, og det som forsvant uten skript
 * var det som så ut som et skjema.
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

  /* --------------------------------------------- anker i lukket liste
   *
   * Lange lister står i en lukket `<details>`. Peker adressen på noe
   * inne i en, åpnes den — også når nettleseren ikke gjør det selv.
   */
  function aapneAnker() {
    function aapne() {
      var id = decodeURIComponent(location.hash.slice(1));
      var maal = id && document.getElementById(id);
      for (var e = maal; e; e = e.parentElement) {
        if (e.tagName === "DETAILS") e.open = true;
      }
      if (maal) maal.scrollIntoView();
    }
    window.addEventListener("hashchange", aapne);
    if (location.hash) aapne();
  }

  /* --------------------------------------------------- verktøytips
   *
   * Kart og grafer bærer navnet på hvert punkt og verdien i hver søyle
   * i et SVG-`<title>`. Uten skript viser nettleseren det selv — sent,
   * lite, og der pekeren tilfeldigvis står, også oppå bildeteksten
   * under kartet. Her tegnes det i stedet som et tips INNE i figuren:
   *
   *   - det følger pekeren og snur når det når kanten av TEGNEFLATA, så
   *     det aldri dekker bildeteksten eller tegnforklaringen;
   *   - det vises også når et punkt får tastaturfokus, ved punktet;
   *   - en graf kan få fokus, og piltastene flytter mellom søylene. En
   *     skjult statuslinje leser verdien for en skjermleser; tipset selv
   *     er `aria-hidden`, så en lenke ikke får navnet sitt lest to ganger.
   *
   * `<title>` flyttes til et dataattributt, så nettleserens eget tips
   * ikke kommer i tillegg. En lenke som fikk navnet sitt fra `<title>`,
   * får det i `aria-label` først — navnet skal ikke forsvinne med tipset.
   *
   * Tipset legger ikke til én verdi. Alt det viser, står i tabellen
   * under figuren.
   */
  function verktoytips() {
    var figurer = document.querySelectorAll("svg[data-kart], svg.lusegraf");

    Array.prototype.forEach.call(figurer, function (svg) {
      var ramme = svg.closest("figure") || svg.parentElement;
      if (!ramme) return;

      /* Hvert mål: et element med en `<title>` som barn (ikke figurens
         egen tittel), eller et område på kystkartet med `aria-label`. */
      var maal = [];
      Array.prototype.forEach.call(svg.querySelectorAll("title"), function (t) {
        var e = t.parentElement;
        if (!e || e === svg) return;
        var tekst = t.textContent.replace(/\s+/g, " ").trim();
        if (!tekst) return;
        if (e.tagName.toLowerCase() === "a" && !e.getAttribute("aria-label")) {
          e.setAttribute("aria-label", tekst);
        }
        e.setAttribute("data-tips", tekst);
        e.removeChild(t);
        maal.push(e);
      });
      Array.prototype.forEach.call(
        svg.querySelectorAll(".kart-omraader a[aria-label]"), function (e) {
          e.setAttribute("data-tips", e.getAttribute("aria-label"));
          maal.push(e);
        });
      if (!maal.length) return;

      ramme.classList.add("med-tips");
      var tips = document.createElement("div");
      tips.className = "verktoytips";
      tips.setAttribute("aria-hidden", "true");
      tips.hidden = true;
      ramme.appendChild(tips);

      function vis(e, x, y) {
        var tekst = e.getAttribute("data-tips");
        if (tips.textContent !== tekst) tips.textContent = tekst;
        tips.hidden = false;
        /* I rammens koordinater — med rulling, for kystkartet ligger i en
           ramme som ruller på smal skjerm — og holdt innenfor tegneflata,
           ikke innenfor rammen, som også rommer bildeteksten. */
        var r = ramme.getBoundingClientRect();
        var s = svg.getBoundingClientRect();
        var ox = ramme.scrollLeft - r.left - ramme.clientLeft;
        var oy = ramme.scrollTop - r.top - ramme.clientTop;
        var b = tips.offsetWidth, h = tips.offsetHeight, luft = 12;
        var venstre = x + luft, topp = y - h - luft;
        if (venstre + b > s.right) venstre = x - b - luft;
        if (venstre < s.left) venstre = s.left;
        if (topp < s.top) topp = y + luft;
        if (topp + h > s.bottom) topp = s.bottom - h;
        tips.style.left = Math.round(venstre + ox) + "px";
        tips.style.top = Math.round(topp + oy) + "px";
      }

      function skjul() { tips.hidden = true; }

      function midten(e) {
        var b = e.getBoundingClientRect();
        return [b.left + b.width / 2, b.top + b.height / 2];
      }

      maal.forEach(function (e) {
        e.addEventListener("pointermove", function (ev) { vis(e, ev.clientX, ev.clientY); });
        /* Et trykk på en søyle skal vise verdien til neste trykk, ikke
           blinke den bort når fingeren løftes. */
        e.addEventListener("pointerdown", function (ev) { vis(e, ev.clientX, ev.clientY); });
        e.addEventListener("pointerleave", function (ev) {
          if (ev.pointerType !== "touch") skjul();
        });
        e.addEventListener("focus", function () {
          var m = midten(e);
          vis(e, m[0], m[1]);
        });
        e.addEventListener("blur", skjul);
      });
      document.addEventListener("pointerdown", function (ev) {
        if (maal.indexOf(ev.target.closest ? ev.target.closest("[data-tips]") : null) < 0) skjul();
      });

      /* GRAFENE kan få fokus som helhet, og piltastene går gjennom
         søylene. Søylene selv er ikke tabulatorstopp: 765 av dem ville
         vært en felle. */
      if (!svg.classList.contains("lusegraf")) return;
      var soyler = maal.filter(function (e) { return e.tagName.toLowerCase() === "rect"; });
      if (!soyler.length) return;
      var i = soyler.length - 1;
      var melding = document.createElement("p");
      melding.className = "visuelt-skjult";
      melding.setAttribute("role", "status");
      ramme.appendChild(melding);
      svg.setAttribute("tabindex", "0");

      function marker() {
        soyler.forEach(function (s, j) { s.classList.toggle("aktiv", j === i); });
        var m = midten(soyler[i]);
        vis(soyler[i], m[0], m[1]);
        melding.textContent = soyler[i].getAttribute("data-tips");
      }
      svg.addEventListener("focus", marker);
      svg.addEventListener("blur", function () {
        soyler[i].classList.remove("aktiv");
        skjul();
      });
      svg.addEventListener("keydown", function (ev) {
        var ny = i;
        if (ev.key === "ArrowLeft") ny = Math.max(0, i - 1);
        else if (ev.key === "ArrowRight") ny = Math.min(soyler.length - 1, i + 1);
        else if (ev.key === "Home") ny = 0;
        else if (ev.key === "End") ny = soyler.length - 1;
        else return;
        ev.preventDefault();
        soyler[i].classList.remove("aktiv");
        i = ny;
        marker();
      });
    });
  }

  [kopier, omraadesok, selskapsdel, aapneAnker, verktoytips].forEach(function (del) {
    try {
      del();
    } catch (e) {
      /* En knekt forbedring skal koste én forbedring, ikke siden.
         Samme regel som `runner.run_all()` og `skriv_alle()`. */
      if (window.console && console.warn) console.warn("Kystloggen:", e);
    }
  });
})();
