/* Søket. Lastes BARE av /sok/, og bare der.
 *
 * ## Hvorfor dette ikke er i kystloggen.js
 *
 * Fordi det henter Pagefinds egen modul og en WebAssembly-fil på til
 * sammen ~1 MB, og det skal ikke skje på 2 336 sider der ingen søker.
 * `kystloggen.js` er 5 kB og lastes overalt; dette lastes ett sted.
 *
 * ## Hvorfor søket i det hele tatt er JavaScript
 *
 * Nettstedets regel er at TALLENE skal stå i kildekoden. Et
 * søkeresultat er ikke et tall fra et register — det er en vei til
 * siden der tallet står, og den siden er statisk HTML som kan siteres,
 * arkiveres og leses uten skript.
 *
 * Et søk over 2 337 sider som skal svare uten en server, må kjøre i
 * nettleseren. Alternativet er ingen søk, og /sok/ har derfor en
 * veiviser til de tre flate indeksene som ALLTID står der — også når
 * dette skriptet aldri lastes.
 *
 * ## Ingen bygging, ingen pakkebrønn
 *
 * Pagefind-indeksen bygges av en binær ved bygging, og modulen som
 * lastes her er den Pagefind selv la i `/pagefind/`. Ingen npm, ingen
 * bundler — se `nettsted.skriv_sokeindeks()`.
 */
(function () {
  "use strict";

  var felt = document.getElementById("q");
  var ut = document.getElementById("sokeresultat");
  if (!felt || !ut) return;

  var TAK = 30;           /* treff som vises */
  var pagefind = null;    /* lastes ved første søk, ikke ved sidelast */
  var siste = "";
  var valgtType = "";     /* tom = alle sidetyper */
  var filterrad = document.getElementById("sokefilter");

  function tekst(el, s) { el.textContent = s; }

  function melding(s) {
    ut.innerHTML = "";
    var p = document.createElement("p");
    p.className = "sok-melding";
    tekst(p, s);
    ut.appendChild(p);
  }

  /* MODULEN LASTES VED FØRSTE TASTETRYKK, ikke når siden åpnes. Den er
     ~1 MB med wasm, og en som kom hit ved et uhell skal ikke betale
     for den. */
  function last() {
    if (pagefind) return Promise.resolve(pagefind);
    return import("/pagefind/pagefind.js").then(function (modul) {
      pagefind = modul;
      return modul.init().then(function () { return modul; });
    });
  }

  /* FILTERET BYGGES AV INDEKSEN, ikke av en liste her.
   *
   * Pagefind vet hvilke sidetyper som finnes og hvor mange sider hver
   * av dem har, fordi `data-pagefind-filter` står på hver side. En
   * liste i dette skriptet ville vært en andre kopi av den samme
   * opplysningen — og den ville stått og løyet den dagen en sidetype
   * kom til. Raden tegnes først når modulen er lastet, altså ved
   * første tastetrykk; før det er den tom, og søket virker uten den. */
  function tegnFilter(m) {
    if (!filterrad || filterrad.dataset.tegnet) return Promise.resolve();
    return m.filters().then(function (alle) {
      var typer = alle.type || {};
      var navn = Object.keys(typer).sort();
      if (!navn.length) return;
      filterrad.dataset.tegnet = "ja";
      navn.unshift("");
      navn.forEach(function (t) {
        var knapp = document.createElement("button");
        knapp.type = "button";
        knapp.className = "typemerke" + (t === valgtType ? " typemerke--valgt" : "");
        knapp.dataset.type = t;
        tekst(knapp, t || "Alle");
        if (t) {
          var n = document.createElement("span");
          n.className = "typemerke-tall";
          tekst(n, String(typer[t]));
          knapp.appendChild(document.createTextNode(" "));
          knapp.appendChild(n);
        }
        knapp.setAttribute("aria-pressed", t === valgtType ? "true" : "false");
        knapp.addEventListener("click", function () {
          valgtType = t;
          Array.prototype.forEach.call(
            filterrad.querySelectorAll("button"), function (b) {
              var pa = b.dataset.type === valgtType;
              b.classList.toggle("typemerke--valgt", pa);
              b.setAttribute("aria-pressed", pa ? "true" : "false");
            });
          siste = "";          /* samme ord, nytt filter: søk på nytt */
          sok();
        });
        filterrad.appendChild(knapp);
      });
    });
  }

  function vis(treff, q) {
    ut.innerHTML = "";
    var hode = document.createElement("p");
    hode.className = "sok-melding";
    tekst(hode, treff.length
      ? "Viser " + Math.min(treff.length, TAK) + " av " + treff.length
        + " treff på «" + q + "»."
      : "Ingen treff på «" + q + "». Prøv et lokalitetsnummer, et "
        + "kommunenavn eller et selskapsnavn — eller bla i de flate "
        + "listene under.");
    ut.appendChild(hode);
    if (!treff.length) return;

    var liste = document.createElement("ol");
    liste.className = "sokeliste";
    ut.appendChild(liste);

    Promise.all(treff.slice(0, TAK).map(function (t) { return t.data(); }))
      .then(function (data) {
        data.forEach(function (d) {
          var li = document.createElement("li");
          var a = document.createElement("a");
          a.href = d.url;
          /* TITTELEN ER SIDENS EGEN `<title>`, uten «— Kystloggen»:
             hver rad i en trefflista som ender på det samme, sier
             ingenting med de siste tolv tegnene. */
          tekst(a, (d.meta && d.meta.title
                    ? d.meta.title : d.url).replace(/ — Kystloggen$/, ""));
          li.appendChild(a);
          /* UNDERTITTELEN: kommune · område · innehaver for en
             lokalitet, organisasjonsnummer · antall lokaliteter for et
             selskap. Den er sidas egen, satt ved bygging — se
             `nettsted._grunnkontekst()`. */
          if (d.meta && d.meta.undertittel) {
            var u2 = document.createElement("p");
            u2.className = "sok-undertittel";
            tekst(u2, (d.meta.sidetype ? d.meta.sidetype + " · " : "")
                      + d.meta.undertittel);
            li.appendChild(u2);
          }
          var p = document.createElement("p");
          p.className = "sok-utdrag";
          /* UTDRAGET ER SIDAS EGEN BESKRIVELSE, ikke Pagefinds klipp
             rundt treffet. Klippet er ord fra et vilkårlig sted på
             sida — en kolonneoverskrift, halve en fotnote — og to
             treff i samme tabell fikk det samme klippet. Beskrivelsen
             sier hva sida ER.

             `textContent` og ikke `innerHTML`: uten Pagefinds `<mark>`
             er det ingen merking å bevare, og da skal strengen
             behandles som tekst. Mangler beskrivelsen, faller vi
             tilbake på klippet — det er HTML fra Pagefind, bygget av
             vår egen statiske side. */
          if (d.meta && d.meta.beskrivelse) {
            tekst(p, d.meta.beskrivelse);
          } else {
            p.innerHTML = d.excerpt;
          }
          li.appendChild(p);
          var u = document.createElement("p");
          u.className = "sok-url";
          tekst(u, d.url);
          li.appendChild(u);
          liste.appendChild(li);
        });
      });
  }

  function sok() {
    var q = felt.value.trim();
    if (q === siste) return;
    siste = q;
    if (q.length < 2) { ut.innerHTML = ""; return; }
    melding("Søker …");
    last()
      .then(function (m) {
        return tegnFilter(m).then(function () {
          return m.search(q, valgtType
            ? {filters: {type: valgtType}} : undefined);
        });
      })
      .then(function (r) { if (felt.value.trim() === q) vis(r.results, q); })
      .catch(function () {
        melding("Søkeindeksen kunne ikke lastes. Listene under virker "
                + "uansett.");
      });
  }

  var vent = null;
  felt.addEventListener("input", function () {
    clearTimeout(vent);
    vent = setTimeout(sok, 150);
  });
  felt.closest("form").addEventListener("submit", function (e) {
    e.preventDefault();
    clearTimeout(vent);
    sok();
  });

  /* `?q=` I ADRESSEN. Skjemaet er en `GET`, så en som trykker enter
     uten JavaScript havner på `/sok/?q=oterneset`. Da skal søket
     kjøre av seg selv når skriptet finnes — ellers ville lenka gitt et
     tomt felt.

     Dette er den ENE spørrestrengen på nettstedet, og den bærer ikke
     innhold: den bærer et søkeord, og /sok/ har ingen identitet å
     forveksle den med. Se 2026-09-16-url-struktur.md punkt 3. */
  var fra = new URLSearchParams(window.location.search).get("q");
  if (fra) { felt.value = fra; sok(); }
})();
